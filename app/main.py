from fastapi import FastAPI

from app.mongo import start_mongo, close_mongo
from .routes.jobs import router as job_router
from .routes.hook import router as webhook_router
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_mongo()
    yield
    await close_mongo()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job_router)
app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"ping": "pong"}
