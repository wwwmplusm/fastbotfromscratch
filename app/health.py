import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def serve_health(
    session_factory: async_sessionmaker[AsyncSession],
    host: str,
    port: int,
):
    if port <= 0:
        return None

    async def handle(reader, writer) -> None:
        del reader
        try:
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
            body = b"ok"
            status = b"200 OK"
        except Exception:
            logger.warning("healthcheck database ping failed")
            body = b"db unavailable"
            status = b"503 Service Unavailable"
        header = b"HTTP/1.1 " + status + b"\r\nContent-Length: " + str(len(body)).encode()
        writer.write(header + b"\r\nConnection: close\r\n\r\n" + body)
        try:
            await writer.drain()
        finally:
            writer.close()

    return await asyncio.start_server(handle, host, port)
