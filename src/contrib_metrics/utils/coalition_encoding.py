from __future__ import annotations

import json
from typing import Any, Iterable, FrozenSet


def normalize_coalition(value: Any) -> FrozenSet[int]:
    if isinstance(value, frozenset):
        return frozenset(int(x) for x in value)
    if isinstance(value, set):
        return frozenset(int(x) for x in value)
    if isinstance(value, list):
        return frozenset(int(x) for x in value)
    if isinstance(value, int):
        return _from_bitmask(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return frozenset()
        # tuple-like string e.g. "('0','1')" or "(0,1)"
        if s.startswith("(") and s.endswith(")"):
            inner = s.strip("()").strip()
            if not inner:
                return frozenset()
            cleaned = []
            for part in inner.split(","):
                part = part.strip().strip("'").strip('"')
                if part:
                    cleaned.append(int(part))
            return frozenset(cleaned)
        if s.startswith("{") and s.endswith("}"):
            inner = s.strip("{}").strip()
            if not inner:
                return frozenset()
            return frozenset(int(x.strip()) for x in inner.split(","))
        if s.startswith("[") and s.endswith("]"):
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return frozenset(int(x) for x in parsed)
        if set(s) <= {"0", "1"}:
            return _from_bitstring(s)
        return frozenset(int(x.strip()) for x in s.split(",") if x.strip())
    return frozenset()


def _from_bitmask(mask: int) -> FrozenSet[int]:
    players: set[int] = set()
    i = 0
    while mask:
        if mask & 1:
            players.add(i)
        mask >>= 1
        i += 1
    return frozenset(players)


def _from_bitstring(bits: str) -> FrozenSet[int]:
    players: set[int] = set()
    for i, b in enumerate(reversed(bits)):
        if b == "1":
            players.add(i)
    return frozenset(players)
