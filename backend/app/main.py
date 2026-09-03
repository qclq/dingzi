from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.configs import router as configs_router
from app.api.v1.detections import router as detections_router
from app.api.v1.exports import router as exports_router
from app.api.v1.health import router as health_router
from app.api.v1.me import router as me_router
from app.api.v1.realtime import router as realtime_router
from app.api.v1.realtime import ws_router
from app.api.v1.system import router as system_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title="定子冲片缺陷检测 Web API", version="0.1.0", debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(me_router, prefix=settings.api_v1_prefix)
app.include_router(realtime_router, prefix=settings.api_v1_prefix)
app.include_router(detections_router, prefix=settings.api_v1_prefix)
app.include_router(exports_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)
app.include_router(configs_router, prefix=settings.api_v1_prefix)
app.include_router(ws_router)
app.include_router(system_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
