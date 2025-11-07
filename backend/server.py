from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import Response

from .app.cost_sheet_service import cost_sheet_service
from .app.config import get_cost_settings
from .routers import router as api_router
from .services import cost_grid


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cfg = get_cost_settings()
    if cfg.cost_sheet_path:
        try:
            cost_sheet_service.ensure_open(cfg.cost_sheet_path)
        except Exception as e:
            # Don't crash the server if Excel isn't present; the API can be used to set later
            print(f"[warn] Failed to open cost sheet at startup: {e}")
    yield
    # Shutdown
    try:
        from .app.excel_xlwings import excel_manager
        excel_manager.close()
    except Exception:
        pass
    try:
        cost_grid.close_excel_and_save_if_dirty()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="RDS Generator", version="1.0.0", lifespan=lifespan)
    app.include_router(api_router)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        """Return an empty response so browsers stop logging 404 errors."""

        return Response(status_code=204)

    return app


app = create_app()
