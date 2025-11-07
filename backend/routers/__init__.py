from __future__ import annotations

from fastapi import APIRouter

from . import cost_sheet, panel3_cost

router = APIRouter()
router.include_router(cost_sheet.router)
router.include_router(panel3_cost.router)
