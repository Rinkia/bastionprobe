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
from typing import Callable, Sequence

EmbedFn = Callable[[Sequence[str]], Sequence[Sequence[float]]]


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
