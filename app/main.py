from fastapi import FastAPI

from app.mongo import start_mongo, close_mongo
from .routes.jobs import router as job_router
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_mongo()
    yield
    await close_mongo()


app = FastAPI(lifespan=lifespan)

app.include_router(job_router)


@app.webhooks.post(path="/vendor-webhook/{vendor}")
def hook(vendor: str): ...
