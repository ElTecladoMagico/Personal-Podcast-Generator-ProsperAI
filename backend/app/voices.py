"""Voice catalog (contract §9). A constant: the ElevenLabs key has no voices_read permission.

Spanish voices are Castilian library voices chosen by ear (docs/plans/06b-voz-espana.md);
English ones are ElevenLabs premades. Each voice previews in its own language.
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas import Host


class Voice(BaseModel):
    id: str
    name: str
    language: Literal["es", "en"]  # the language it sounds native in (all are multilingual)
    gender: Literal["female", "male"]
    descriptor: dict[str, str]  # {"en": …, "es": …}
    preview: str  # static file in the web app


def voice(id: str, name: str, language, gender, en: str, es: str) -> Voice:
    return Voice(
        id=id,
        name=name,
        language=language,
        gender=gender,
        descriptor={"en": en, "es": es},
        preview=f"/voices/{id}.mp3",
    )


VOICES = [
    voice(
        "gD1IexrzCvsXPHUuT0s3",
        "Sara",
        "es",
        "female",
        "Young, conversational",
        "Joven y conversacional",
    ),
    voice(
        "LlZr3QuzbW4WrPjgATHG",
        "Martín",
        "es",
        "male",
        "Easygoing, made for dialogue",
        "Cercano, hecho para conversar",
    ),
    voice("Nh2zY9kknu6z4pZy6FhD", "David", "es", "male", "Young and confident", "Joven y seguro"),
    voice("RgXx32WYOGrd7gFNifSf", "Eva", "es", "female", "Warm and soft", "Cálida y suave"),
    voice("EXAVITQu4vr4xnSDxMaL", "Sarah", "en", "female", "Soft and confident", "Suave y segura"),
    voice(
        "JBFqnCBsd6RMkjVDRZzb",
        "George",
        "en",
        "male",
        "Warm British storyteller",
        "Narrador británico cálido",
    ),
    voice(
        "XB0fDUnXU5powFXDhCwa",
        "Charlotte",
        "en",
        "female",
        "Bright and expressive",
        "Brillante y expresiva",
    ),
    voice("nPczCjzI2devNBz1zQrb", "Brian", "en", "male", "Deep and steady", "Grave y sereno"),
    voice("FGY2WhTYpPnrIDTdsKH5", "Laura", "en", "female", "Upbeat and lively", "Animada y viva"),
    voice(
        "TX3LPaxmHKxFdv7VOQHJ", "Liam", "en", "male", "Articulate and energetic", "Claro y enérgico"
    ),
]
BY_ID = {v.id: v for v in VOICES}
DEFAULT_PAIRS = {"es": ("gD1IexrzCvsXPHUuT0s3", "LlZr3QuzbW4WrPjgATHG")}
DEFAULT_PAIR = ("EXAVITQu4vr4xnSDxMaL", "JBFqnCBsd6RMkjVDRZzb")  # any other language


def default_hosts(language: str) -> list[Host]:
    pair = DEFAULT_PAIRS.get(language, DEFAULT_PAIR)
    return [Host(name=BY_ID[i].name, voice_id=i) for i in pair]
