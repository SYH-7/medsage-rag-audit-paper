from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence
import numpy as np


class TextEncoder(ABC):
    @abstractmethod
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError


def build_encoder(config: dict) -> TextEncoder:
    backend = config.get("backend", "sentence_transformer")
    if backend == "hashing":
        from .hashing import HashingTextEncoder
        return HashingTextEncoder(dimension=int(config.get("hashing_dim", 768)))
    if backend == "sentence_transformer":
        from .sentence_transformer import SentenceTransformerEncoder
        return SentenceTransformerEncoder(
            model_name=config.get("model_name", "BAAI/bge-m3"),
            batch_size=int(config.get("batch_size", 32)),
            normalize=bool(config.get("normalize", True)),
            device=config.get("device"),
        )
    raise ValueError(f"Unknown encoder backend: {backend}")
