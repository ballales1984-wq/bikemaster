"""Training stress repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, insert, select

_METADATA = MetaData()
TRAINING_STRESS_DAYS_TABLE = Table(
    "training_stress_days",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("athlete_id", Integer, nullable=False, index=True),
    Column("date", String(20), nullable=False),
    Column("tss", Float),
    Column("atl", Float),
    Column("ctl", Float),
    Column("tsb", Float),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
)


class TrainingStressRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    @property
    def _table(self):
        return TRAINING_STRESS_DAYS_TABLE

    async def upsert_day(self, athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float) -> None:
        if self._session_factory:
            return await self._upsert_async(athlete_id, date, tss, atl, ctl, tsb)
        if self._sync_conn:
            return self._sync_conn.upsert_training_stress_day(athlete_id, date, tss, atl, ctl, tsb)
        return self._upsert_sync(athlete_id, date, tss, atl, ctl, tsb)

    async def get_history(self, athlete_id: int, limit: int = 90) -> list[dict]:
        if self._session_factory:
            return await self._get_history_async(athlete_id, limit)
        if self._sync_conn:
            return self._sync_conn.get_training_stress_days(athlete_id, limit)
        return self._get_history_sync(athlete_id, limit)

    async def get_latest(self, athlete_id: int) -> dict | None:
        if self._session_factory:
            return await self._get_latest_async(athlete_id)
        if self._sync_conn:
            return self._sync_conn.get_latest_training_stress(athlete_id)
        return self._get_latest_sync(athlete_id)

    async def _upsert_async(self, athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            stmt = (
                insert(self._table)
                .values(
                    athlete_id=athlete_id,
                    date=date,
                    tss=tss,
                    atl=atl,
                    ctl=ctl,
                    tsb=tsb,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[self._table.athlete_id, self._table.date],
                    set_={
                        "tss": tss,
                        "atl": atl,
                        "ctl": ctl,
                        "tsb": tsb,
                        "updated_at": now,
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def _get_history_async(self, athlete_id: int, limit: int = 90) -> list[dict]:
        async with self._session_factory() as session:
            stmt = (
                select(self._table)
                .where(self._table.athlete_id == athlete_id)
                .order_by(self._table.date.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [self._row_to_day(row) for row in result.mappings().all()]

    async def _get_latest_async(self, athlete_id: int) -> dict | None:
        history = await self._get_history_async(athlete_id, limit=1)
        return history[0] if history else None

    def _row_to_day(self, row: dict) -> dict:
        return {
            "date": row["date"],
            "tss": row["tss"],
            "atl": row["atl"],
            "ctl": row["ctl"],
            "tsb": row["tsb"],
        }

    def _upsert_sync(self, athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float) -> None:
        from ..db.database import upsert_training_stress_day
        upsert_training_stress_day(athlete_id, date, tss, atl, ctl, tsb)

    def _get_history_sync(self, athlete_id: int, limit: int = 90) -> list[dict]:
        from ..db.database import get_training_stress_days
        return get_training_stress_days(athlete_id, limit)

    def _get_latest_sync(self, athlete_id: int) -> dict | None:
        from ..db.database import get_latest_training_stress
        return get_latest_training_stress(athlete_id)
