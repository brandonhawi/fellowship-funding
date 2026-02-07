from __future__ import annotations

import logging
from datetime import date, datetime

import requests

from .base import Opportunity, Source

logger = logging.getLogger(__name__)

SEARCH_URL = "https://zintellect.com/Catalog/Index_DataTableResult"
DETAIL_URL = "https://zintellect.com/Opportunity/Details"

ACADEMIC_LEVELS = {
    "phd_student": 1006145,
    "postdoc": 1006146,
    "post_masters": 1006147,
    "post_bachelors": 1006162,
}

CITIZENSHIP_MAP = {
    "us_citizen": 3,
    "us_lpr": 2,
    "none": 1,
}


class ZintellectSource(Source):
    name = "Zintellect/ORISE"

    def __init__(
        self,
        keywords: list[str] | None = None,
        academic_level: str = "phd_student",
        citizenship: str = "us_citizen",
    ):
        self.keywords = keywords or []
        self.academic_level = academic_level
        self.citizenship = citizenship

    def fetch(self) -> list[Opportunity]:
        try:
            return self._fetch()
        except Exception:
            logger.exception("Failed to fetch from %s", self.name)
            return []

    def _fetch(self) -> list[Opportunity]:
        seen_ids: set[int] = set()
        results: list[Opportunity] = []

        search_terms = self.keywords[:4] if self.keywords else [""]

        for term in search_terms:
            opps = self._search(term)
            for opp in opps:
                if opp["id"] not in seen_ids:
                    seen_ids.add(opp["id"])
                    results.append(self._to_opportunity(opp))

        logger.info("Zintellect: fetched %d unique opportunities", len(results))
        return results

    def _search(self, keyword: str) -> list[dict]:
        payload = {
            "draw": 1,
            "start": 0,
            "length": 200,
            "Keyword": keyword,
            "AcademicLevels": ACADEMIC_LEVELS.get(self.academic_level, 1006145),
            "Citizenship": CITIZENSHIP_MAP.get(self.citizenship, 3),
            "ShowOnlyResumeMatches": "false",
            "IsCatalogSortedByElasticSearchScore": "true" if keyword else "false",
        }

        resp = requests.post(
            SEARCH_URL,
            data=payload,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def _to_opportunity(self, item: dict) -> Opportunity:
        ref_code = item.get("referenceCode", "")
        deadline = self._parse_date(item.get("expirationDate", ""))

        return Opportunity(
            id=f"zintellect:{item.get('id', '')}",
            title=item.get("title", ""),
            url=f"{DETAIL_URL}/{ref_code}",
            source=self.name,
            description=item.get("title", ""),
            deadline=deadline,
            amount="",
            eligibility="",
            organization="ORISE",
        )

    @staticmethod
    def _parse_date(raw: str) -> date | None:
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%m-%d-%Y").date()
        except ValueError:
            return None
