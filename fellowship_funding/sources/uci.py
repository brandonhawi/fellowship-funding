from __future__ import annotations

import logging
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from .base import Opportunity, Source

logger = logging.getLogger(__name__)

WP_API_URL = "https://grad.uci.edu/wp-json/wp/v2/fellowships"
ANNOUNCEMENTS_URL = "https://grad.uci.edu/funding/fellowship-announcements/"


UCI_LEVEL_MAP = {
    "dissertation": {"current", "advanced"},
    "phd_student": {"current", "prospective", "advanced"},
}


class UCISource(Source):
    name = "UCI Graduate Fellowships"

    def __init__(self, academic_level: str = "phd_student"):
        self.accepted_levels = UCI_LEVEL_MAP.get(academic_level, {"current", "advanced"})

    def fetch(self) -> list[Opportunity]:
        try:
            results = self._fetch_api()
            results.extend(self._fetch_announcements())
            return results
        except Exception:
            logger.exception("Failed to fetch from %s", self.name)
            return []

    def _fetch_api(self) -> list[Opportunity]:
        resp = requests.get(
            WP_API_URL,
            params={"per_page": 100},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data:
            acf = item.get("acf", {})
            if acf.get("application_status") != "open":
                continue
            level = acf.get("academic_level", "")
            if level and level not in self.accepted_levels:
                continue

            deadline = self._parse_deadline(acf.get("deadline", ""))
            desc = BeautifulSoup(
                item.get("content", {}).get("rendered", ""),
                "html.parser",
            ).get_text(strip=True)

            results.append(Opportunity(
                id=f"uci:{item['id']}",
                title=item.get("title", {}).get("rendered", ""),
                url=item.get("link", ""),
                source=self.name,
                description=desc,
                deadline=deadline,
                amount=acf.get("amount", ""),
                eligibility=BeautifulSoup(
                    acf.get("eligibility_criteria", ""), "html.parser"
                ).get_text(strip=True),
                organization="UC Irvine Graduate Division",
            ))

        logger.info("UCI API: fetched %d open fellowships", len(results))
        return results

    def _fetch_announcements(self) -> list[Opportunity]:
        resp = requests.get(ANNOUNCEMENTS_URL, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for link in soup.select("article a[href]"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href:
                continue

            parent = link.find_parent("article")
            desc = parent.get_text(strip=True) if parent else ""

            opp_id = href.rstrip("/").rsplit("/", 1)[-1]
            results.append(Opportunity(
                id=f"uci-announce:{opp_id}",
                title=title,
                url=href,
                source=self.name,
                description=desc,
                deadline=None,
                amount="",
                eligibility="",
                organization="UC Irvine Graduate Division",
            ))

        logger.info("UCI announcements: fetched %d items", len(results))
        return results

    @staticmethod
    def _parse_deadline(raw: str) -> date | None:
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y%m%d").date()
        except ValueError:
            return None
