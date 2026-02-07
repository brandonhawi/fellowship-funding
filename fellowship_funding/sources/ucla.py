from __future__ import annotations

import logging
from datetime import date, datetime

import requests

from .base import Opportunity, Source

logger = logging.getLogger(__name__)

SOLR_URL = "https://grad.ucla.edu/se/grapes_main/select"

DISCIPLINE_FIELDS = {
    "public health": "publichealth",
    "social sciences": "socialsciences",
    "life sciences": "lifesciences",
}


class UCLASource(Source):
    name = "UCLA Graduate Funding"

    def __init__(self, disciplines: list[str] | None = None, academic_level: str = "phd_student"):
        self.disciplines = disciplines or []
        self.academic_level = academic_level

    def fetch(self) -> list[Opportunity]:
        try:
            return self._fetch()
        except Exception:
            logger.exception("Failed to fetch from %s", self.name)
            return []

    def _fetch(self) -> list[Opportunity]:
        fq_parts = []
        for disc in self.disciplines:
            field = DISCIPLINE_FIELDS.get(disc.lower())
            if field:
                fq_parts.append(f"{field}:true")

        fq_parts.append("currentgrad:true")
        if self.academic_level == "dissertation":
            fq_parts.append("doctoraldiss:true")
        fq = " OR ".join(fq_parts)

        resp = requests.get(
            SOLR_URL,
            params={
                "q": "*:*",
                "wt": "json",
                "indent": "true",
                "fq": fq,
                "rows": 200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for doc in data.get("response", {}).get("docs", []):
            record_no = doc.get("recordno", "")
            deadline = self._parse_deadline(doc.get("CombinedDeadline", ""))
            amount_val = doc.get("awardamountyearly")
            amount = f"${amount_val:,.0f}" if amount_val else ""

            results.append(Opportunity(
                id=f"ucla:{record_no}",
                title=doc.get("awardtitle", ""),
                url=f"https://grad.ucla.edu/funding/#/detail/{record_no}",
                source=self.name,
                description=doc.get("description", ""),
                deadline=deadline,
                amount=amount,
                eligibility=doc.get("awardtype", ""),
                organization=doc.get("agency1", ""),
            ))

        logger.info("UCLA: fetched %d opportunities", len(results))
        return results

    @staticmethod
    def _parse_deadline(raw: str) -> date | None:
        if not raw:
            return None
        for fmt in ("%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None
