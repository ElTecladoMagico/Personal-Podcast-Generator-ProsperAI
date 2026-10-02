from fastapi import APIRouter

from app.voices import VOICES, Voice

router = APIRouter()


@router.get("/voices")
def list_voices() -> list[Voice]:
    return VOICES
