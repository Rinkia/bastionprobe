"""Offline embedders for the co-evolution loop.

A real deployment plugs in a sentence-transformer or an embeddings API. For a
zero-dependency, deterministic loop we provide a feature-hashing bag-of-words
embedder: stable across calls (hashlib, not Python's salted hash), fixed
dimension without a shared vocabulary, and it generalizes weakly — texts sharing
tokens get similar vectors, so a SemanticDetector seeded with a landed attack
also flags close paraphrases. Weak generalization, but enough to make A's
hardening visibly move the benchmark; swap in a real model for real coverage.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Optional, Sequence

EmbedFn = Callable[[Sequence[str]], Sequence[Sequence[float]]]


def sentence_transformer_embedder(
    model_name: str = "all-MiniLM-L6-v2",
    model: Optional[Any] = None,
    normalize: bool = True,
) -> EmbedFn:
    """A real dense embedder via sentence-transformers. Generalizes across
    paraphrases far better than the hashing bag-of-words, so A's hardening covers
    whole attack families instead of only token-overlapping restatements.

    `model` may be injected (a preloaded SentenceTransformer, or a stand-in for
    tests); otherwise it is lazily loaded from `model_name` on first use — which
    needs `pip install "bastionprobe[embeddings]"` and a one-time model download.

    Pair it with a HIGHER SemanticDetector threshold (~0.6) than the BoW embedder
    (~0.4): dense cosine similarities for genuine paraphrases sit much higher.
    """
    state: dict = {"model": model}

    def _get() -> Any:
        if state["model"] is None:
            from sentence_transformers import SentenceTransformer  # optional dep

            state["model"] = SentenceTransformer(model_name)
        return state["model"]

    def embed(texts: Sequence[str]) -> Sequence[Sequence[float]]:
        vecs = _get().encode(list(texts), normalize_embeddings=normalize)
        return [list(map(float, v)) for v in vecs]

    return embed


def hashing_embedder(dim: int = 256) -> EmbedFn:
    def _bucket(token: str) -> int:
        return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dim

    def embed(texts: Sequence[str]) -> Sequence[Sequence[float]]:
        vecs: list[list[float]] = []
        for t in texts:
            v = [0.0] * dim
            for tok in t.lower().split():
                v[_bucket(tok)] += 1.0
            vecs.append(v)
        return vecs

    return embed
