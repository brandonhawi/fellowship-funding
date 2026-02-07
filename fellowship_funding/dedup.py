from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from .sources.base import Opportunity

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path("data/seen.json")
MAX_AGE_DAYS = 180


def load_seen(path: Path = DEFAULT_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not read %s, starting fresh", path)
        return {}


def save_seen(seen: dict[str, str], path: Path = DEFAULT_PATH) -> None:
    cutoff = (date.today() - timedelta(days=MAX_AGE_DAYS)).isoformat()
    pruned = {k: v for k, v in seen.items() if v >= cutoff}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pruned, indent=2) + "\n")
    logger.info("Saved %d seen IDs (%d pruned)", len(pruned), len(seen) - len(pruned))


def filter_new(
    opportunities: list[tuple[Opportunity, int]],
    seen: dict[str, str],
) -> list[tuple[Opportunity, int]]:
    return [(opp, score) for opp, score in opportunities if opp.id not in seen]


def mark_seen(
    opportunities: list[tuple[Opportunity, int]],
    seen: dict[str, str],
) -> dict[str, str]:
    today = date.today().isoformat()
    updated = dict(seen)
    for opp, _ in opportunities:
        updated[opp.id] = today
    return updated
