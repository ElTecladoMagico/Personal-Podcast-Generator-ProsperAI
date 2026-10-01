from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import audio, me

app = FastAPI(title="Personal Podcast API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(me.router)
app.include_router(audio.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
