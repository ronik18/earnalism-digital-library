from __future__ import annotations

from backend.audiobook_generation.english_model_adapters.base import (
    BaseEnglishAudiobookModelAdapter,
    EnglishAdapterResult,
    EnglishModelEnvironment,
    EnglishModelLicense,
    EnglishModelSpec,
)
from backend.audiobook_generation.english_model_adapters.chatterbox import ChatterboxEnglishAdapter
from backend.audiobook_generation.english_model_adapters.dia import DiaEnglishAdapter
from backend.audiobook_generation.english_model_adapters.dry_run import DryRunEnglishAdapter
from backend.audiobook_generation.english_model_adapters.f5_tts import F5TTSEnglishAdapter
from backend.audiobook_generation.english_model_adapters.kokoro import KokoroEnglishAdapter
from backend.audiobook_generation.english_model_adapters.xtts_v2 import XTTSv2EnglishAdapter


ADAPTER_REGISTRY: dict[str, type[BaseEnglishAudiobookModelAdapter]] = {
    "dry-run": DryRunEnglishAdapter,
    "chatterbox-tts": ChatterboxEnglishAdapter,
    "dia": DiaEnglishAdapter,
    "kokoro-82m": KokoroEnglishAdapter,
    "f5-tts": F5TTSEnglishAdapter,
    "xtts-v2": XTTSv2EnglishAdapter,
}


def adapter_for_model(model_id: str) -> type[BaseEnglishAudiobookModelAdapter]:
    try:
        return ADAPTER_REGISTRY[model_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported English audiobook model: {model_id}") from exc


__all__ = [
    "ADAPTER_REGISTRY",
    "BaseEnglishAudiobookModelAdapter",
    "ChatterboxEnglishAdapter",
    "DiaEnglishAdapter",
    "DryRunEnglishAdapter",
    "EnglishAdapterResult",
    "EnglishModelEnvironment",
    "EnglishModelLicense",
    "EnglishModelSpec",
    "F5TTSEnglishAdapter",
    "KokoroEnglishAdapter",
    "XTTSv2EnglishAdapter",
    "adapter_for_model",
]

