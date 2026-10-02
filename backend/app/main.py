from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import jobs
from app.config import settings
from app.routers import audio, episodes, events, me, voices


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.scheduler_enabled:  # off in tests
        jobs.recover_interrupted()
    yield
    jobs.executor.shutdown(wait=False, cancel_futures=True)  # unfinished ones resume on restart


app = FastAPI(title="Personal Podcast API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(me.router)
app.include_router(audio.router)
app.include_router(episodes.router)
app.include_router(voices.router)
app.include_router(events.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
