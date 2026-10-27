from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from factory import jobs
from factory.api import handlers
from factory.api.paths import SAMPLES
from factory.api.routes import catalog, episodes, images, projects, storage, system, voice
from factory.core import DATA, EPISODES, FORMATS, PROJECTS
from factory.music import library


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    jobs.handlers.update(handlers.HANDLERS)
    jobs.start()
    yield


app = FastAPI(title="Content Factory", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    # the Tauri webview and the Vite dev server; no other site may drive the local engine
    allow_origins=["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost", "http://localhost:1420"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_app_header(request, call_next):
    """A page on any website can fire a plain POST at localhost without asking. Writes must carry a custom
    header, which a foreign page can only send after a CORS preflight that the allow-list above refuses."""
    if (
        request.url.path.startswith("/api/")
        and request.method not in ("GET", "HEAD", "OPTIONS")
        and request.headers.get("x-factory") != "1"
    ):
        return JSONResponse({"detail": "missing X-Factory header"}, status_code=403)
    return await call_next(request)


for d in (EPISODES, PROJECTS, SAMPLES, DATA / "formats", library.DIR):
    d.mkdir(parents=True, exist_ok=True)
app.mount("/files/episodes", StaticFiles(directory=EPISODES), name="episodes")
app.mount("/files/projects", StaticFiles(directory=PROJECTS), name="projects")
app.mount("/files/formats", StaticFiles(directory=FORMATS), name="formats")
app.mount("/files/data-formats", StaticFiles(directory=DATA / "formats"), name="data-formats")
app.mount("/files/music", StaticFiles(directory=library.DIR), name="music")
app.mount("/files/samples", StaticFiles(directory=SAMPLES), name="samples")

for router in (
    system.router,
    catalog.router,
    episodes.router,
    projects.router,
    images.router,
    storage.router,
    voice.router,
):
    app.include_router(router, prefix="/api")


def run(port: int = 8790) -> None:
    import uvicorn

    # the /api/events stream never ends on its own: without a cap a stopped engine waits for it forever
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=2)
