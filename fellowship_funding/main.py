from __future__ import annotations

import logging
import sys

from .config import load_config
from .dedup import filter_new, load_seen, mark_seen, save_seen
from .email import send_digest
from .scoring import score_and_filter
from .sources import ALL_SOURCES
from .sources.base import Opportunity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    logger.info("Loaded config with %d keywords", len(config.keywords))

    # Fetch from all sources
    all_opportunities: list[Opportunity] = []
    for source_cls in ALL_SOURCES:
        source_name = source_cls.name
        try:
            source = _init_source(source_cls, config)
            opps = source.fetch()
            all_opportunities.extend(opps)
            logger.info("✓ %s: %d opportunities", source_name, len(opps))
        except Exception:
            logger.exception("✗ %s: failed to initialize", source_name)

    logger.info("Total fetched: %d opportunities", len(all_opportunities))

    # Score and filter
    scored = score_and_filter(all_opportunities, config)
    logger.info("After scoring (threshold=%d): %d opportunities", config.score_threshold, len(scored))

    # Dedup
    seen = load_seen()
    new_opps = filter_new(scored, seen)
    logger.info("New (unseen) opportunities: %d", len(new_opps))

    if not new_opps:
        logger.info("No new opportunities to report. Done.")
        return

    # Send email
    try:
        send_digest(new_opps, config)
    except Exception:
        logger.exception("Failed to send digest email")
        sys.exit(1)

    # Update seen tracker only after successful send
    updated_seen = mark_seen(new_opps, seen)
    save_seen(updated_seen)

    logger.info("Done. Sent %d new opportunities.", len(new_opps))


def _init_source(source_cls: type, config):
    name = source_cls.__name__
    if name == "UCLASource":
        return source_cls(disciplines=config.disciplines, academic_level=config.academic_level)
    elif name == "UCISource":
        return source_cls(academic_level=config.academic_level)
    elif name == "ZintellectSource":
        return source_cls(
            keywords=config.keywords,
            academic_level=config.academic_level,
            citizenship=config.citizenship,
        )
    elif name == "PathwaysSource":
        return source_cls(keywords=config.keywords)
    else:
        return source_cls()


if __name__ == "__main__":
    main()
