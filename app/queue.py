from aio_pika import connect_robust
from aio_pika.abc import AbstractRobustConnection
from app.config import settings


async def get_connection() -> AbstractRobustConnection:
    connection = await connect_robust(settings.RabbitMQ_URL)
    return connection
