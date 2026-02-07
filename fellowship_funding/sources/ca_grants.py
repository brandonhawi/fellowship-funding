from __future__ import annotations

import logging
from datetime import date, datetime

import requests

from .base import Opportunity, Source

logger = logging.getLogger(__name__)

CKAN_URL = "https://data.ca.gov/api/3/action/datastore_search_sql"
RESOURCE_ID = "111c8c88-21f6-453c-ae2c-b4785a0624f5"


class CAGrantsSource(Source):
    name = "California Grants Portal"

    def fetch(self) -> list[Opportunity]:
        try:
            return self._fetch()
        except Exception:
            logger.exception("Failed to fetch from %s", self.name)
            return []

    def _fetch(self) -> list[Opportunity]:
        sql = (
            'SELECT "Title", "Categories", "ApplicationDeadline", '
            '"EstAvailFunds", "EstAmounts", "Purpose", "GrantURL", '
            '"ApplicantType", "Description", "FundingSource", "_id" '
            f'FROM "{RESOURCE_ID}" '
            "WHERE \"Status\" = 'active' "
            "AND (\"Categories\" LIKE '%Health%' "
            "OR \"Categories\" LIKE '%Food%' "
            "OR \"Categories\" LIKE '%Education%') "
            "ORDER BY \"ApplicationDeadline\" ASC"
        )

        resp = requests.get(CKAN_URL, params={"sql": sql}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        records = data.get("result", {}).get("records", [])
        results = []
        for rec in records:
            deadline = self._parse_deadline(rec.get("ApplicationDeadline", ""))
            amount_parts = []
            if rec.get("EstAvailFunds"):
                amount_parts.append(f"Total: {rec['EstAvailFunds']}")
            if rec.get("EstAmounts"):
                amount_parts.append(f"Per award: {rec['EstAmounts']}")

            results.append(Opportunity(
                id=f"ca-grants:{rec.get('_id', '')}",
                title=rec.get("Title", ""),
                url=rec.get("GrantURL", ""),
                source=self.name,
                description=rec.get("Description") or rec.get("Purpose", ""),
                deadline=deadline,
                amount=" | ".join(amount_parts),
                eligibility=rec.get("ApplicantType", ""),
                organization=rec.get("FundingSource", "California"),
            ))

        logger.info("CA Grants: fetched %d opportunities", len(results))
        return results

    @staticmethod
    def _parse_deadline(raw: str) -> date | None:
        if not raw:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw[:19], fmt).date()
            except ValueError:
                continue
        return None
