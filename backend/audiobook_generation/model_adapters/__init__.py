from __future__ import annotations

from .ai4bharat_indic_tts import AI4BharatIndicTTSAdapter
from .base import BaseAudiobookModelAdapter
from .dry_run import DryRunAdapter
from .f5_tts import F5TTSAdapter
from .mahatts import MahaTTSAdapter
from .svara_tts import SvaraTTSAdapter


ADAPTERS = {
    "dry-run-no-audio": DryRunAdapter,
    "svara-tts-v1": SvaraTTSAdapter,
    "mahatts-v2": MahaTTSAdapter,
    "ai4bharat-indic-tts": AI4BharatIndicTTSAdapter,
    "f5-tts": F5TTSAdapter,
}

__all__ = [
    "ADAPTERS",
    "AI4BharatIndicTTSAdapter",
    "BaseAudiobookModelAdapter",
    "DryRunAdapter",
    "F5TTSAdapter",
    "MahaTTSAdapter",
    "SvaraTTSAdapter",
]
