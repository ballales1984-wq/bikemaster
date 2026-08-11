"""Training stress repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    select,
)

_METADATA = MetaData()
TRAINING_STRESS_DAYS_TABLE = Table(
    "training_stress_days",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("athlete_id", Integer, nullable=False, index=True),
    Column("tenant_id", Integer, nullable=False, default=0, index=True),
    Column("date", String(20), nullable=False),
    Column("tss", Float),
    Column("atl", Float),
    Column("ctl", Float),
    Column("tsb", Float),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    UniqueConstraint("athlete_id", "date", name="uq_training_stress_days"),
)


class TrainingStressRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    @property
    def _table(self):
        return TRAINING_STRESS_DAYS_TABLE

    async def upsert_day(
        self, athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float, tenant_id: int = 0
    ) -> None:
        if self._session_factory:
            return await self._upsert_async(athlete_id, date, tss, atl, ctl, tsb, tenant_id)
        if self._sync_conn:
            return self._sync_conn.upsert_training_stress_day(athlete_id, date, tss, atl, ctl, tsb, tenant_id)
        return self._upsert_sync(athlete_id, date, tss, atl, ctl, tsb)

    async def get_history(self, athlete_id: int, limit: int = 90, tenant_id: int | None = None) -> list[dict]:
        if self._session_factory:
            return await self._get_history_async(athlete_id, limit, tenant_id)
        if self._sync_conn:
            return self._sync_conn.get_training_stress_days(athlete_id, limit, tenant_id)
        return self._get_history_sync(athlete_id, limit, tenant_id)

    async def get_latest(self, athlete_id: int, tenant_id: int | None = None) -> dict | None:
        if self._session_factory:
            return await self._get_latest_async(athlete_id, tenant_id)
        if self._sync_conn:
            return self._sync_conn.get_latest_training_stress(athlete_id, tenant_id)
        return self._get_latest_sync(athlete_id, tenant_id)

    async def _upsert_async(
        self, athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float, tenant_id: int = 0
    ) -> None:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        now = datetime.now(UTC)
        async with self._session_factory() as session:
            stmt = (
                sqlite_insert(self._table)
                .values(
                    athlete_id=athlete_id,
                    tenant_id=tenant_id,
                    date=date,
                    tss=tss,
                    atl=atl,
                    ctl=ctl,
                    tsb=tsb,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[self._table.c.athlete_id, self._table.c.date],
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

    async def _get_history_async(self, athlete_id: int, limit: int = 90, tenant_id: int | None = None) -> list[dict]:
        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.c.athlete_id == athlete_id)
            if tenant_id is not None:
                stmt = stmt.where(self._table.c.tenant_id == tenant_id)
            stmt = stmt.order_by(self._table.c.date.desc()).limit(limit)
            result = await session.execute(stmt)
            return [self._row_to_day(row) for row in result.mappings().all()]

    async def _get_latest_async(self, athlete_id: int, tenant_id: int | None = None) -> dict | None:
        history = await self._get_history_async(athlete_id, limit=1, tenant_id=tenant_id)
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
        from ..db.repositories.training_stress_repository import upsert_training_stress_day

        upsert_training_stress_day(athlete_id, date, tss, atl, ctl, tsb)

    def _get_history_sync(self, athlete_id: int, limit: int = 90, tenant_id: int | None = None) -> list[dict]:
        from ..db.repositories.training_stress_repository import get_training_stress_days

        return get_training_stress_days(athlete_id, limit, tenant_id)

    def _get_latest_sync(self, athlete_id: int, tenant_id: int | None = None) -> dict | None:
        from ..db.repositories.training_stress_repository import get_latest_training_stress

        return get_latest_training_stress(athlete_id, tenant_id)
