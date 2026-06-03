"""API routes."""
from __future__ import annotations
from typing import List
from fastapi import APIRouter
from ..models.models import Ride
from ..analytics.analytics import calculate_summary, analyze_ride

router = APIRouter()

@router.get("/health")
async def health_check(): return {"status": "ok", "service": "bikemaster"}

@router.post("/rides/analyze")
async def analyze_rides(rides: List[dict]):
    return calculate_summary([Ride(**r) for r in rides])

@router.post("/rides/{ride_id}/analyze")
async def analyze_single_ride(ride_id: int, ride_data: dict):
    return analyze_ride(Ride(id=ride_id, **ride_data))