from sqlmodel import Session, create_engine, select
from sqlalchemy.pool import StaticPool

from app.models.click_event import ClickEvent
from app.services.click_event_batcher import ClickEventBatcher

SQLITE_URL = "sqlite://"


def _make_engine():
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    return engine


class TestRecord:
    def test_adds_record_to_queue(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine, batch_size=500)
        batcher.record(1, "1.2.3.4", "agent", "ref")
        assert batcher.queue.qsize() == 1

    def test_records_multiple_events(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine)
        batcher.record(1, "a", None, None)
        batcher.record(2, "b", None, None)
        batcher.record(3, "c", None, None)
        assert batcher.queue.qsize() == 3

    def test_drops_on_full_queue(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine, max_queue_size=2)
        batcher.record(1, "a", None, None)
        batcher.record(2, "b", None, None)
        assert batcher.dropped_count == 0
        batcher.record(3, "c", None, None)
        assert batcher.dropped_count == 1
        assert batcher.queue.qsize() == 2


class TestFlush:
    def test_flush_writes_to_database(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine)
        batcher.record(1, "1.2.3.4", "agent", "ref")
        batcher.flush()
        with Session(engine) as session:
            clicks = session.exec(select(ClickEvent)).all()
            assert len(clicks) == 1
            click = clicks[0]
            assert click.url_map_id == 1
            assert click.ip_address == "1.2.3.4"
            assert click.user_agent == "agent"
            assert click.referer == "ref"

    def test_flush_all_pending_events(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine)
        for i in range(10):
            batcher.record(i, f"ip.{i}", None, None)
        batcher.flush()
        with Session(engine) as session:
            clicks = session.exec(select(ClickEvent)).all()
            assert len(clicks) == 10

    def test_flush_empty_queue_is_noop(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine)
        batcher.flush()
        with Session(engine) as session:
            clicks = session.exec(select(ClickEvent)).all()
            assert len(clicks) == 0

    def test_flush_writes_in_batches(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine, batch_size=50)
        for i in range(120):
            batcher.record(i, None, None, None)
        batcher.flush()
        with Session(engine) as session:
            clicks = session.exec(select(ClickEvent)).all()
            assert len(clicks) == 120

    def test_nullable_fields_are_null(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine)
        batcher.record(1, None, None, None)
        batcher.flush()
        with Session(engine) as session:
            click = session.exec(select(ClickEvent)).first()
            assert click is not None
            assert click.ip_address is None
            assert click.user_agent is None
            assert click.referer is None

    def test_clicked_at_is_set(self):
        engine = _make_engine()
        batcher = ClickEventBatcher(engine)
        batcher.record(1, None, None, None)
        batcher.flush()
        with Session(engine) as session:
            click = session.exec(select(ClickEvent)).first()
            assert click.clicked_at is not None
