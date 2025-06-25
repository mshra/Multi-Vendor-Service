from fastapi import FastAPI, status, Body
from urllib.parse import urljoin
from app.config import settings
from fastapi.responses import JSONResponse
import asyncio
import httpx
from fastapi.middleware.cors import CORSMiddleware


vendor_app = FastAPI()

vendor_app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@vendor_app.post("/vendor/sync", status_code=status.HTTP_200_OK)
def sync_vendor(data=Body()):
    return {
        "request_id": data.get("request_id"),
        "final_data": data,
    }


@vendor_app.post("/vendor/async")
async def async_vendor(data=Body()):
    asyncio.create_task(delayed_webhook_post(data))
    return JSONResponse(
        content={"message": "Accepted"}, status_code=status.HTTP_202_ACCEPTED
    )


async def delayed_webhook_post(data):
    await asyncio.sleep(random.uniform(3, 6))
    async with httpx.AsyncClient() as client:
        url = urljoin(settings.APP_SERVICE_URL, "vendor-webhook/async")
        await client.post(
            url,
            json={
                "request_id": data.get("request_id"),
                "final_data": data,
            },
        )


@vendor_app.get("/health")
def health():
    return {"ping": "pong"}
