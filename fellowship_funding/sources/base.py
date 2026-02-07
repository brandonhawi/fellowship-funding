from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Opportunity:
    id: str
    title: str
    url: str
    source: str
    description: str
    deadline: date | None
    amount: str
    eligibility: str
    organization: str
    notes: str = ""


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> list[Opportunity]:
        ...
