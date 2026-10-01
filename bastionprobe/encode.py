"""Encode payloads: the obfuscation-jailbreak side of the attack.

A model reads base64, binary or rot13 fluently; a text detector usually does not.
`--encode` re-fires every payload encoded, so land rate can be compared per
encoding against the plain baseline. The canary is filled in BEFORE encoding (an
encoded `{canary}` placeholder could never be filled).

bastioncorpus ships the decoders (`bastioncorpus.variants`); the encoders live
here because only the attack side needs them.
"""

from __future__ import annotations

import base64
import codecs
import urllib.parse
from dataclasses import replace

from .corpus import Payload

_MORSE = {"a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.", "g": "--.",
          "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..", "m": "--", "n": "-.",
          "o": "---", "p": ".--.", "q": "--.-", "r": ".-.", "s": "...", "t": "-", "u": "..-",
          "v": "...-", "w": ".--", "x": "-..-", "y": "-.--", "z": "--..", "0": "-----",
          "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....",
          "7": "--...", "8": "---..", "9": "----.", ".": ".-.-.-", "@": ".--.-.", "/": "-..-."}
_LEET = str.maketrans({"o": "0", "i": "1", "e": "3", "a": "4", "s": "5", "t": "7"})


def _morse(s: str) -> str:
    words = ["".join(c for c in w.lower() if c in _MORSE) for w in s.split()]
    return " / ".join(" ".join(_MORSE[c] for c in w) for w in words if w)


def _spaced(s: str) -> str:
    return "  ".join(" ".join(w) for w in s.split())  # letters 1 space apart, words 2


ENCODERS = {
    "base64": lambda s: base64.b64encode(s.encode()).decode(),
    "base64url": lambda s: base64.urlsafe_b64encode(s.encode()).decode().rstrip("="),
    "base32": lambda s: base64.b32encode(s.encode()).decode(),
    "hex": lambda s: s.encode().hex(),
    "binary": lambda s: " ".join(f"{b:08b}" for b in s.encode()),
    "ascii85": lambda s: base64.a85encode(s.encode(), adobe=True).decode(),
    "base85": lambda s: base64.b85encode(s.encode()).decode(),
    "morse": _morse,
    "percent": lambda s: urllib.parse.quote(s, safe=""),
    "escape": lambda s: "".join(f"\\u{ord(c):04x}" for c in s),
    "tags": lambda s: "".join(chr(0xE0000 + ord(c)) for c in s),
    "rot13": lambda s: codecs.encode(s, "rot13"),
    "leet": lambda s: s.lower().translate(_LEET),
    "reversed": lambda s: s[::-1],
    "spaced": _spaced,
}
NAMES = tuple(ENCODERS)


def parse_names(spec: str) -> tuple[str, ...]:
    """`all` or a comma list; raises ValueError naming the unknown ones."""
    if spec.strip().lower() == "all":
        return NAMES
    names = tuple(n.strip().lower() for n in spec.split(",") if n.strip())
    unknown = sorted(set(names) - set(NAMES))
    if unknown or not names:
        raise ValueError(f"unknown encoding(s) {unknown or [spec]}; choose from: all, {', '.join(NAMES)}")
    return names


def encode(text: str, name: str) -> str:
    return ENCODERS[name](text)


def encoded_payloads(payloads: list[Payload], names: tuple[str, ...]) -> list[Payload]:
    """Each plain payload once per encoding (tactic `<tactic>+enc-<name>`). Rows that
    are already encoded (`enc-*`) are kept as they are when their encoding is chosen."""
    out = []
    for p in payloads:
        if p.tactic.startswith("enc-"):
            if p.tactic[4:] in names:
                out.append(p)
            continue
        for name in names:
            out.append(replace(p, id=f"{p.id}+{name}", encoding=name,
                               tactic=f"{p.tactic or 'plain'}+enc-{name}"))
    return out
