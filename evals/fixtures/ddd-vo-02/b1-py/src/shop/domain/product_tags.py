from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class ProductTags:
    values: Set[str]
    reserved: frozenset[str] = frozenset({"sale", "new"})

    def has(self, tag: str) -> bool:
        return tag in self.values
