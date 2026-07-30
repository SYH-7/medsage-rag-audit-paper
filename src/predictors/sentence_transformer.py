from __future__ import annotations

from typing import Sequence
import numpy as np
from .base import TextEncoder


class SentenceTransformerEncoder(TextEncoder):
    def __init__(
        self,
        model_name: str,
        batch_size: int = 32,
        normalize: bool = True,
        device: str | None = None,
    ):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required. Install with: pip install -e '.[models]'"
            ) from exc
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize = normalize
        self.model = SentenceTransformer(model_name, device=device)
        self._dimension = int(self.model.get_sentence_embedding_dimension())

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)
        return np.asarray(
            self.model.encode(
                list(texts),
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
                convert_to_numpy=True,
            ),
            dtype=np.float32,
        )
