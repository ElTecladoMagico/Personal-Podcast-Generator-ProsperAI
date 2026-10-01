from fastapi import FastAPI

app = FastAPI(title="Personal Podcast API")


@app.get("/health")
def health() -> dict:
    return {"ok": True}
