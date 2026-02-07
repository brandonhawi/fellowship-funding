from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from .base import Opportunity, Source

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path("data/jhu_early_career.xlsx")


class JHUSource(Source):
    name = "JHU Early Career Funding"

    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or DEFAULT_PATH

    def fetch(self) -> list[Opportunity]:
        if not self.file_path.exists():
            logger.info(
                "JHU: Excel file not found at %s, skipping. "
                "Download from https://research.jhu.edu/rdt/funding-opportunities/early-career/",
                self.file_path,
            )
            return []

        try:
            return self._fetch()
        except Exception:
            logger.exception("Failed to fetch from %s", self.name)
            return []

    def _fetch(self) -> list[Opportunity]:
        import openpyxl

        wb = openpyxl.load_workbook(self.file_path, read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            return []

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        header = [str(h).strip().lower() if h else "" for h in rows[0]]
        col_idx = {name: i for i, name in enumerate(header) if name}

        results = []
        for row in rows[1:]:
            def get(name: str) -> str:
                idx = col_idx.get(name)
                if idx is None:
                    return ""
                val = row[idx] if idx < len(row) else None
                return str(val).strip() if val else ""

            title = get("opportunity") or get("title") or get("name")
            if not title:
                continue

            deadline = None
            raw_deadline = get("deadline") or get("due date")
            if raw_deadline:
                deadline = self._parse_date(raw_deadline)
            # Also try the cell value directly if it's a datetime
            deadline_idx = col_idx.get("deadline") or col_idx.get("due date")
            if deadline is None and deadline_idx is not None:
                val = row[deadline_idx] if deadline_idx < len(row) else None
                if isinstance(val, datetime):
                    deadline = val.date()
                elif isinstance(val, date):
                    deadline = val

            results.append(Opportunity(
                id=f"jhu:{hash(title) & 0xFFFFFFFF:08x}",
                title=title,
                url=get("url") or get("link") or get("website")
                    or "https://research.jhu.edu/rdt/funding-opportunities/early-career/",
                source=self.name,
                description=get("description") or get("subject") or get("subject matter"),
                deadline=deadline,
                amount=get("amount") or get("funding") or get("award amount"),
                eligibility=get("eligibility") or get("requirements"),
                organization=get("organization") or get("funder") or get("sponsor"),
            ))

        wb.close()
        logger.info("JHU: parsed %d opportunities from Excel", len(results))
        return results

    @staticmethod
    def _parse_date(raw: str) -> date | None:
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None
