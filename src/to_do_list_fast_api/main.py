from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from to_do_list_fast_api.database import Base, engine
from to_do_list_fast_api.routers.auth import router as auth_router
from to_do_list_fast_api.routers.todos import router as todos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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

app.include_router(auth_router)
app.include_router(todos_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to To-Do List API",
        "documentation": "/docs",
        "redoc": "/redoc",
    }