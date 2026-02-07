from __future__ import annotations

import re

from .config import Config
from .sources.base import Opportunity


def score_opportunity(opp: Opportunity, config: Config) -> int:
    title_lower = opp.title.lower()
    desc_lower = opp.description.lower()
    combined = f"{title_lower} {desc_lower} {opp.eligibility.lower()}"

    score = 0.0

    for kw in config.keywords:
        kw_lower = kw.lower()
        pattern = re.compile(re.escape(kw_lower))
        title_hits = len(pattern.findall(title_lower))
        desc_hits = len(pattern.findall(combined))
        score += title_hits * 15 + desc_hits * 5

    for disc in config.disciplines:
        disc_lower = disc.lower()
        if disc_lower in title_lower:
            score += 10
        if disc_lower in combined:
            score += 3

    return min(int(score), 100)


def score_and_filter(
    opportunities: list[Opportunity],
    config: Config,
) -> list[tuple[Opportunity, int]]:
    scored = []
    for opp in opportunities:
        s = score_opportunity(opp, config)
        if s >= config.score_threshold:
            scored.append((opp, s))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
