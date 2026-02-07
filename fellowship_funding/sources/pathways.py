from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup, Tag

from .base import Opportunity, Source

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pathwaystoscience.org"
SEARCH_URL = f"{BASE_URL}/programs.aspx"
DELAY = 1.5


class PathwaysSource(Source):
    name = "Pathways to Science"

    def __init__(self, keywords: list[str] | None = None):
        self.keywords = keywords or []

    def fetch(self) -> list[Opportunity]:
        try:
            return self._fetch()
        except Exception:
            logger.exception("Failed to fetch from %s", self.name)
            return []

    def _fetch(self) -> list[Opportunity]:
        seen_ids: set[str] = set()
        results: list[Opportunity] = []

        queries: list[dict[str, str]] = [
            {"u": "GradPhDs_Graduate Students (PhD)", "p": "YesPortable"},
        ]
        for kw in self.keywords[:3]:
            queries.append({
                "u": "GradPhDs_Graduate Students (PhD)",
                "ft": kw,
            })

        for params in queries:
            params.update({"adv": "adv", "submit": "y"})
            opps = self._search(params)
            for opp in opps:
                if opp.id not in seen_ids:
                    seen_ids.add(opp.id)
                    results.append(opp)
            time.sleep(DELAY)

        logger.info("Pathways: fetched %d unique opportunities", len(results))
        return results

    def _search(self, params: dict) -> list[Opportunity]:
        resp = requests.get(SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return self._parse_results(soup)

    def _parse_results(self, soup: BeautifulSoup) -> list[Opportunity]:
        results = []
        divs = soup.select("div.progigert")

        current_institution = ""
        for div in divs:
            # Header divs contain h2 with institution name
            h2 = div.find("h2")
            if h2:
                current_institution = h2.get_text(strip=True)
                continue

            # Content divs contain program links
            link = div.find("a", href=lambda h: h and "programhub" in h)
            if not link:
                continue

            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"{BASE_URL}/{href.lstrip('/')}"

            match = re.search(r"sort=(.+?)(?:&|$)", href)
            prog_id = match.group(1) if match else href

            title = link.get_text(strip=True)
            if title == "...read more":
                continue

            # Description is in a child div
            desc_div = div.find("div")
            description = desc_div.get_text(strip=True) if desc_div else ""
            # Remove the "...read more" suffix
            description = re.sub(r"\s*\.\.\.read more\s*$", "", description)

            results.append(Opportunity(
                id=f"pathways:{prog_id}",
                title=title,
                url=href,
                source=self.name,
                description=description,
                deadline=None,
                amount="",
                eligibility="PhD Students",
                organization=current_institution,
            ))

        return results
