from fastapi import FastAPI

from app.routers import me

app = FastAPI(title="Personal Podcast API")
app.include_router(me.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
