from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from to_do_list_fast_api.database import Base, engine
from to_do_list_fast_api.routers.auth import router as auth_router
from to_do_list_fast_api.routers.biometric import router as biometric_router
from to_do_list_fast_api.routers.todos import router as todos_router
from to_do_list_fast_api.routers.transfer import router as transfer_router
from to_do_list_fast_api.routers.users import router as users_router
from to_do_list_fast_api.schemas import DataResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS balance "
                    "DOUBLE PRECISION NOT NULL DEFAULT 1000000.0"
                )
            )
    except Exception as e:
        print(f"Database connection skipped during startup: {e}")
    yield



app = FastAPI(
    title="To-Do List API",
    description="FastAPI To-Do List REST API with JWT Authentication and PostgreSQL",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "message": str(exc.detail),
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_messages = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []) if item != "body")
        msg = err.get("msg", "Validation error")
        if loc:
            error_messages.append(f"{loc}: {msg}")
        else:
            error_messages.append(msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "; ".join(error_messages) if error_messages else "Validation error",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Internal server error",
        },
    )


app.include_router(auth_router)
app.include_router(biometric_router)
app.include_router(users_router)
app.include_router(transfer_router)
app.include_router(todos_router)


@app.get("/", tags=["Root"], response_model=DataResponse[dict[str, str]])
def root():
    return DataResponse(
        status=status.HTTP_200_OK,
        message="Welcome to To-Do List API",
        data={
            "documentation": "/docs",
            "redoc": "/redoc",
        },
    )