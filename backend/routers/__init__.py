from __future__ import annotations

from fastapi import APIRouter
from . import cost_sheet

router = APIRouter()
router.include_router(cost_sheet.router)
