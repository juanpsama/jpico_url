import asyncio

import logging
import queue as pyqueue
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import Request
from sqlmodel import Session, insert

from app.models.click_event import ClickEvent

logger = logging.getLogger("uvicorn.error")


@dataclass
class ClickEventRecord:
    url_map_id: int
    ip_address: str | None
    user_agent: str | None
    referer: str | None
    clicked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ClickEventBatcher:
    def __init__(
        self,
        engine,
        flush_interval: float = 5.0,
        batch_size: int = 500,
        max_queue_size: int = 100_000,
    ):
        self.engine = engine
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.queue: pyqueue.Queue[ClickEventRecord] = pyqueue.Queue(maxsize=max_queue_size)
        self.max_queue_size = max_queue_size
        self._task: asyncio.Task | None = None
        self._running = False
        self.dropped_count = 0

    def record(
        self,
        url_map_id: int,
        ip_address: str | None,
        user_agent: str | None,
        referer: str | None,
    ):
        record = ClickEventRecord(
            url_map_id=url_map_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
        )
        try:
            self.queue.put_nowait(record)
        except pyqueue.Full:
            self.dropped_count += 1
            logger.warning(
                "Click event queue full, dropped event (total dropped: %d)",
                self.dropped_count,
            )

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())
        logger.info(
            "ClickEventBatcher started (flush_interval=%ss, batch_size=%d, max_queue_size=%d)",
            self.flush_interval,
            self.batch_size,
            self.max_queue_size,
        )

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.flush()

    def flush(self):
        while True:
            batch = self._drain_batch()
            if not batch:
                break
            self._write_batch(batch)

    def _drain_batch(self) -> list[ClickEventRecord]:
        batch: list[ClickEventRecord] = []
        while len(batch) < self.batch_size:
            try:
                batch.append(self.queue.get_nowait())
            except pyqueue.Empty:
                break
        return batch
    

    async def _flush_loop(self):
        loop = asyncio.get_running_loop()
        while self._running:
            await asyncio.sleep(self.flush_interval)
            try:
                batch = self._drain_batch()
                if batch:
                    await loop.run_in_executor(None, self._write_batch, batch)
            except Exception:
                logger.exception("Failed to flush click events")

    def _write_batch(self, batch: list[ClickEventRecord]):
        with Session(self.engine) as session:
            # if self._is_postgres:
            # else:
            self._write_copy(session, batch)
            # self._write_insert(session, batch)
            session.commit()

    def _write_copy(self, session: Session, batch: list[ClickEventRecord]):
        raw_conn = session.connection().connection
        with raw_conn.cursor() as cursor, cursor.copy(
            "COPY clickevent (url_map_id, clicked_at, ip_address, user_agent, referer) "
            "FROM STDIN WITH DELIMITER '\t' CSV NULL ''",
        ) as copy:
            for rec in batch:
                copy.write_row([
                    rec.url_map_id,
                    rec.clicked_at.isoformat(),
                    rec.ip_address or "",
                    rec.user_agent or "",
                    rec.referer or "",
                ])

    def _write_insert(self, session: Session, batch: list[ClickEventRecord]):
        rows = [
            {
                "url_map_id": rec.url_map_id,
                "clicked_at": rec.clicked_at,
                "ip_address": rec.ip_address,
                "user_agent": rec.user_agent,
                "referer": rec.referer,
            }
            for rec in batch
        ]
        session.execute(insert(ClickEvent), rows)


def get_click_batcher(request: Request) -> ClickEventBatcher:
    return request.app.state.click_batcher
