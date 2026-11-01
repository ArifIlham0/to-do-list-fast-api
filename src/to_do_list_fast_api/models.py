from datetime import datetime
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from to_do_list_fast_api.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    balance = Column(Float, default=1000000.0, server_default="1000000.0", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    todos = relationship("Todo", back_populates="owner", cascade="all, delete-orphan")
    biometric_credentials = relationship(
        "BiometricCredential",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    favorites = relationship(
        "UserFavorite",
        foreign_keys="UserFavorite.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    favorited_by = relationship(
        "UserFavorite",
        foreign_keys="UserFavorite.favorite_user_id",
        back_populates="favorite_user",
        cascade="all, delete-orphan",
    )
    sent_transfers = relationship(
        "Transfer",
        foreign_keys="Transfer.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
    received_transfers = relationship(
        "Transfer",
        foreign_keys="Transfer.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan",
    )


class UserFavorite(Base):
    __tablename__ = "user_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "favorite_user_id", name="uq_user_favorite"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    favorite_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="favorites")
    favorite_user = relationship(
        "User",
        foreign_keys=[favorite_user_id],
        back_populates="favorited_by",
    )


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiver_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nominal = Column(Float, nullable=False)
    transaction_type = Column(String(100), nullable=False)
    transaction_purpose = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_transfers")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_transfers")


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="todos")


class BiometricCredential(Base):
    __tablename__ = "biometric_credentials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id = Column(String(128), nullable=False, index=True)
    device_name = Column(String(255), nullable=True)
    public_key_pem = Column(Text, nullable=False)
    key_algorithm = Column(String(50), default="ECDSA_P256_SHA256", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="biometric_credentials")
    challenges = relationship(
        "BiometricChallenge",
        back_populates="credential",
        cascade="all, delete-orphan",
    )

    @property
    def credential_id(self) -> str:
        return self.id


class BiometricChallenge(Base):
    __tablename__ = "biometric_challenges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    credential_id = Column(
        String(36),
        ForeignKey("biometric_credentials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    challenge_value = Column(String(128), nullable=False)
    challenge_hash = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    credential = relationship("BiometricCredential", back_populates="challenges")

