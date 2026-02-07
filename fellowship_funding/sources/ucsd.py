from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime

import requests

from .base import Opportunity, Source

logger = logging.getLogger(__name__)

EMBED_URL = "https://airtable.com/embed/appNF4vTlbabvmXko/shrMkLwSoo2DJOXw6"
APP_ID = "appNF4vTlbabvmXko"


class UCSDSource(Source):
    name = "UCSD Young Investigator"

    def fetch(self) -> list[Opportunity]:
        try:
            return self._fetch()
        except Exception:
            logger.exception("Failed to fetch from %s", self.name)
            return []

    def _fetch(self) -> list[Opportunity]:
        session = requests.Session()

        # Step 1: Get embed page and extract data URL
        resp = session.get(f"{EMBED_URL}?viewControls=on", timeout=30)
        resp.raise_for_status()

        # Extract urlWithParams directly — the prefetch object uses JS syntax (unquoted keys)
        url_match = re.search(
            r'urlWithParams:\s*"([^"]+)"',
            resp.text,
        )
        if not url_match:
            logger.warning("UCSD: could not find urlWithParams in embed page")
            return []

        # Decode unicode escapes like \u002F -> /
        data_url = url_match.group(1).encode().decode("unicode_escape")
        if not data_url:
            logger.warning("UCSD: no urlWithParams in prefetch")
            return []

        if not data_url.startswith("http"):
            data_url = f"https://airtable.com{data_url}"

        # Step 2: Fetch actual data
        resp2 = session.get(
            data_url,
            headers={
                "x-airtable-application-id": APP_ID,
                "X-Requested-With": "XMLHttpRequest",
                "x-time-zone": "America/Los_Angeles",
            },
            timeout=30,
        )
        resp2.raise_for_status()
        data = resp2.json()

        return self._parse_records(data)

    def _parse_records(self, data: dict) -> list[Opportunity]:
        table = data.get("data", {}).get("table", {})
        rows = table.get("rows", [])
        columns = table.get("columns", [])

        col_map = {col["id"]: col for col in columns}
        col_by_name = {}
        for col in columns:
            col_by_name[col.get("name", "")] = col["id"]

        # Build choice maps for multiselect fields
        choice_maps: dict[str, dict[str, str]] = {}
        for col in columns:
            type_opts = col.get("typeOptions") or {}
            choices = type_opts.get("choices") or {}
            if choices:
                choice_maps[col["id"]] = {
                    cid: c.get("name", cid) for cid, c in choices.items()
                }

        results = []
        for row in rows:
            cells = row.get("cellValuesByColumnId", {})
            title = self._get_text(cells, col_by_name, "Funding Opportunity")
            funder = self._get_text(cells, col_by_name, "Funder")
            url = self._get_text(cells, col_by_name, "Link to Opportunity")
            amount = self._get_text(cells, col_by_name, "Funding Amount | Period")
            deadline_raw = self._get_text(cells, col_by_name, "Deadline")

            # Resolve multiselect keywords
            kw_col = col_by_name.get("Keywords", "")
            kw_ids = cells.get(kw_col, [])
            choice_map = choice_maps.get(kw_col, {})
            keywords = [choice_map.get(kid, kid) for kid in kw_ids] if isinstance(kw_ids, list) else []

            deadline = None
            if deadline_raw:
                try:
                    deadline = datetime.fromisoformat(deadline_raw).date()
                except (ValueError, TypeError):
                    pass

            results.append(Opportunity(
                id=f"ucsd:{row.get('id', '')}",
                title=title,
                url=url or "https://cfr.ucsd.edu/funding-opportunities/young-investigators.html",
                source=self.name,
                description=" | ".join(keywords) if keywords else "",
                deadline=deadline,
                amount=amount,
                eligibility="Young Investigators / Early Career",
                organization=funder,
            ))

        logger.info("UCSD: fetched %d opportunities", len(results))
        return results

    @staticmethod
    def _get_text(cells: dict, col_by_name: dict, name: str) -> str:
        col_id = col_by_name.get(name, "")
        val = cells.get(col_id, "")
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        return str(val) if val else ""
