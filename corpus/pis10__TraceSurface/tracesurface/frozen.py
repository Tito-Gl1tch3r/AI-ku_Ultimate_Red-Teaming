from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class FrozenDict(Mapping[K, V], Generic[K, V]):
    __slots__ = ("_items", "_dict")

    def __init__(self, items: Mapping[K, V] | Iterable[tuple[K, V]] = ()) -> None:
        data = dict(items)
        self._items: tuple[tuple[K, V], ...] = tuple(data.items())
        self._dict: dict[K, V] = data

    def __getitem__(self, key: K) -> V:
        return self._dict[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def __repr__(self) -> str:
        return repr(self._dict)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other.items())
        return False

    def __reduce__(self):
        return (type(self), (self._items,))


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: to_jsonable(item) for key, item in value.items()}

    if isinstance(value, tuple | list):
        return [to_jsonable(item) for item in value]

    return value
