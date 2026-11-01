import base64
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from to_do_list_fast_api.config import settings
from to_do_list_fast_api.database import get_db
from to_do_list_fast_api.dependencies import get_current_user
from to_do_list_fast_api.models import BiometricChallenge, BiometricCredential, User
from to_do_list_fast_api.schemas import (
    BiometricChallengeRequest,
    BiometricChallengeResponse,
    BiometricCredentialCreate,
    BiometricCredentialResponse,
    BiometricCredentialStatusResponse,
    BiometricVerifyRequest,
    DataResponse,
    Token,
)
from to_do_list_fast_api.security import create_access_token

SUPPORTED_KEY_ALGORITHM = "ECDSA_P256_SHA256"

router = APIRouter(prefix="/biometric", tags=["Biometric Authentication"])


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_and_normalize_public_key(
    public_key_pem: str,
    key_algorithm: str,
) -> str:
    if key_algorithm != SUPPORTED_KEY_ALGORITHM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported key_algorithm. Expected {SUPPORTED_KEY_ALGORITHM}",
        )

    cleaned_pem = public_key_pem.strip()
    try:
        public_key = load_pem_public_key(cleaned_pem.encode("utf-8"))
    except (ValueError, TypeError, UnsupportedAlgorithm) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid public key PEM format",
        ) from exc

    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(
        public_key.curve, ec.SECP256R1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public key must be an ECDSA P-256 (secp256r1) key",
        )

    normalized_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return normalized_pem


def decode_base64url_challenge(challenge_b64url: str) -> bytes:
    cleaned = challenge_b64url.strip()
    padding = "=" * ((4 - len(cleaned) % 4) % 4)
    return base64.urlsafe_b64decode((cleaned + padding).encode("ascii"))


def decode_signature_base64(signature_b64: str) -> bytes:
    cleaned = signature_b64.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid biometric signature",
        )
    normalized = cleaned.replace("-", "+").replace("_", "/")
    padding = "=" * ((4 - len(normalized) % 4) % 4)
    try:
        return base64.b64decode(normalized + padding, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid biometric signature",
        ) from exc


@router.post(
    "/credentials",
    response_model=DataResponse[BiometricCredentialStatusResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a biometric public key credential for the current user",
)
async def register_biometric_credential(
    credential_in: BiometricCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataResponse[BiometricCredentialStatusResponse]:
    normalized_pem = validate_and_normalize_public_key(
        public_key_pem=credential_in.public_key,
        key_algorithm=credential_in.key_algorithm,
    )

    now = datetime.now(timezone.utc)

    existing_device_credentials = (
        db.query(BiometricCredential)
        .filter(
            BiometricCredential.user_id == current_user.id,
            BiometricCredential.device_id == credential_in.device_id,
            BiometricCredential.is_active.is_(True),
        )
        .all()
    )
    for old_cred in existing_device_credentials:
        old_cred.is_active = False
        old_cred.revoked_at = now
    if existing_device_credentials:
        db.flush()

    active_credentials_count = (
        db.query(BiometricCredential)
        .filter(
            BiometricCredential.user_id == current_user.id,
            BiometricCredential.is_active.is_(True),
        )
        .count()
    )
    if active_credentials_count >= settings.MAX_BIOMETRIC_CREDENTIALS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Maximum number of active biometric credentials "
                f"({settings.MAX_BIOMETRIC_CREDENTIALS_PER_USER}) reached"
            ),
        )

    new_credential = BiometricCredential(
        user_id=current_user.id,
        device_id=credential_in.device_id,
        device_name=credential_in.device_name,
        public_key_pem=normalized_pem,
        key_algorithm=credential_in.key_algorithm,
        is_active=True,
    )
    db.add(new_credential)
    db.commit()
    db.refresh(new_credential)

    return DataResponse(
        status=status.HTTP_201_CREATED,
        message="Biometric credential registered successfully",
        data=BiometricCredentialStatusResponse(
            credential_id=new_credential.id,
            status="active",
        ),
    )


@router.get(
    "/credentials",
    response_model=DataResponse[list[BiometricCredentialResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all biometric credentials for the current user",
)
async def list_biometric_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataResponse[list[BiometricCredentialResponse]]:
    credentials = (
        db.query(BiometricCredential)
        .filter(BiometricCredential.user_id == current_user.id)
        .order_by(BiometricCredential.created_at.desc())
        .all()
    )
    return DataResponse(
        status=status.HTTP_200_OK,
        message="Biometric credentials retrieved successfully",
        data=[BiometricCredentialResponse.model_validate(cred) for cred in credentials],
    )


@router.delete(
    "/credentials/{credential_id}",
    response_model=DataResponse[BiometricCredentialStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke a biometric credential owned by the current user",
)
async def revoke_biometric_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataResponse[BiometricCredentialStatusResponse]:
    credential = (
        db.query(BiometricCredential)
        .filter(
            BiometricCredential.id == credential_id,
            BiometricCredential.user_id == current_user.id,
        )
        .first()
    )
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biometric credential not found",
        )

    credential.is_active = False
    credential.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(credential)

    return DataResponse(
        status=status.HTTP_200_OK,
        message="Biometric credential revoked successfully",
        data=BiometricCredentialStatusResponse(
            credential_id=credential.id,
            status="revoked",
        ),
    )


@router.post(
    "/challenge",
    response_model=DataResponse[BiometricChallengeResponse],
    status_code=status.HTTP_200_OK,
    summary="Create a one-time cryptographic challenge for biometric login",
)
async def create_biometric_challenge(
    challenge_in: BiometricChallengeRequest,
    db: Session = Depends(get_db),
) -> DataResponse[BiometricChallengeResponse]:
    credential = (
        db.query(BiometricCredential)
        .filter(
            BiometricCredential.id == challenge_in.credential_id,
            BiometricCredential.is_active.is_(True),
        )
        .first()
    )
    if not credential or not credential.user or not credential.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive biometric credential",
        )

    raw_bytes = secrets.token_bytes(32)
    challenge_b64url = base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")
    challenge_hash = hashlib.sha256(raw_bytes).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.BIOMETRIC_CHALLENGE_EXPIRE_SECONDS
    )

    new_challenge = BiometricChallenge(
        credential_id=credential.id,
        challenge_value=challenge_b64url,
        challenge_hash=challenge_hash,
        expires_at=expires_at,
    )
    db.add(new_challenge)
    db.commit()
    db.refresh(new_challenge)

    return DataResponse(
        status=status.HTTP_200_OK,
        message="Challenge created successfully",
        data=BiometricChallengeResponse(
            challenge_id=new_challenge.id,
            challenge=new_challenge.challenge_value,
            expires_at=new_challenge.expires_at,
        ),
    )


@router.post(
    "/verify",
    response_model=DataResponse[Token],
    status_code=status.HTTP_200_OK,
    summary="Verify signed biometric challenge and issue JWT access token",
)
async def verify_biometric_challenge(
    verify_in: BiometricVerifyRequest,
    db: Session = Depends(get_db),
) -> DataResponse[Token]:
    now = datetime.now(timezone.utc)

    challenge = (
        db.query(BiometricChallenge)
        .filter(BiometricChallenge.id == verify_in.challenge_id)
        .with_for_update()
        .first()
    )
    if (
        not challenge
        or challenge.credential_id != verify_in.credential_id
        or challenge.used_at is not None
        or ensure_utc(challenge.expires_at) <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired biometric challenge",
        )

    credential = (
        db.query(BiometricCredential)
        .filter(BiometricCredential.id == challenge.credential_id)
        .first()
    )
    if not credential or not credential.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive biometric credential",
        )

    user = credential.user
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive biometric credential",
        )

    try:
        challenge_bytes = decode_base64url_challenge(challenge.challenge_value)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid biometric challenge state",
        ) from exc

    if hashlib.sha256(challenge_bytes).hexdigest() != challenge.challenge_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid biometric challenge state",
        )

    signature_bytes = decode_signature_base64(verify_in.signature)

    try:
        public_key = load_pem_public_key(credential.public_key_pem.encode("utf-8"))
        if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(
            public_key.curve, ec.SECP256R1
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid biometric credential key",
            )
        public_key.verify(
            signature_bytes,
            challenge_bytes,
            ec.ECDSA(hashes.SHA256()),
        )
    except HTTPException:
        raise
    except (InvalidSignature, ValueError, TypeError, UnsupportedAlgorithm) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Biometric signature verification failed",
        ) from exc

    challenge.used_at = now
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    token = Token(access_token=access_token, token_type="bearer")
    return DataResponse(
        status=status.HTTP_200_OK,
        message="Login successful",
        data=token,
    )
