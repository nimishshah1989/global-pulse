"""Ranking endpoints for country, sector, and stock RS rankings."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/rankings", tags=["rankings"])
