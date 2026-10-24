"""
Ghost Job & Evergreen Listing Detection Engine.

Detects:
1. Evergreen talent pools and pipeline listings ("always hiring", "talent community", etc.).
2. Stale and expired job postings (> 90 days old).
3. Repost churning & fake freshness (old jobs bumped with recent timestamps).
4. Provides deterministic reality classification & authenticity score (0-100%).
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


# Curated phrases that indicate a posting is a perpetual pipeline / talent pool rather than an active opening
EVERGREEN_PHRASES = [
    "always hiring",
    "always looking for",
    "we are always",
    "we're always",
    "talent community",
    "talent pool",
    "talent network",
    "future opportunities",
    "future openings",
    "general application",
    "open application",
    "ongoing recruitment",
    "future hires",
    "pipeline role",
    "pool of candidates",
    "expression of interest",
    "speculative application",
    "talent pipeline",
    "continuous recruitment",
    "general interest",
    "prospective candidates",
    "keep your resume on file",
]

FRESH_WINDOW_DAYS = 14
STALE_AGE_DAYS = 60
GHOST_AGE_DAYS = 90
CONVERGENCE_THRESHOLD = 2


class GhostDetector:
    """
    Evaluates whether a job posting is a real, active opening or a ghost/evergreen pipeline listing.
    Computes time-dependent reality signals dynamically without guessing.
    """

    @classmethod
    def find_evergreen_markers(cls, text: str) -> List[str]:
        if not text:
            return []
        lower = text.lower()
        found = []
        for phrase in EVERGREEN_PHRASES:
            if phrase in lower:
                found.append(phrase)
        return found

    @classmethod
    def evaluate(
        cls,
        title: str,
        company: str,
        description: str = "",
        created_at: Optional[datetime] = None,
        posted_at: Optional[datetime] = None,
        repost_count: int = 1
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        created = created_at or now
        age_days = max(0, int((now - created).total_seconds() / 86400))

        evergreen_markers = cls.find_evergreen_markers(description)
        # Also check title
        title_markers = cls.find_evergreen_markers(title)
        all_markers = list(set(evergreen_markers + title_markers))

        has_evergreen_text = len(all_markers) > 0
        is_old = age_days >= GHOST_AGE_DAYS
        is_stale = age_days >= STALE_AGE_DAYS and not is_old
        is_reposted = repost_count >= 3

        # Fake freshness check: created long ago but posted timestamp bumped within fresh window
        fake_freshness = False
        if is_old and posted_at:
            posted_age = max(0, int((now - posted_at).total_seconds() / 86400))
            if posted_age <= FRESH_WINDOW_DAYS:
                fake_freshness = True

        signals = []
        signal_count = 0

        if has_evergreen_text:
            signals.append(f"Contains evergreen pipeline phrase(s): {', '.join(all_markers[:2])}")
            signal_count += 1

        if is_old:
            signals.append(f"Posting is {age_days} days old (exceeds {GHOST_AGE_DAYS}d active threshold)")
            signal_count += 1

        if is_reposted:
            signals.append(f"Frequently reposted position ({repost_count}+ occurrences)")
            signal_count += 1

        if fake_freshness:
            signals.append("Artificially bumped timestamp (historical requisition republished as fresh)")
            signal_count += 1

        # Classification
        if signal_count >= CONVERGENCE_THRESHOLD or has_evergreen_text:
            reality_class = "likely_ghost"
            label = "👻 Likely Ghost / Evergreen"
            authenticity_score = max(15, 60 - (signal_count * 20))
            is_ghost = True
            summary = "High probability of being an inactive talent pool, speculative pipeline, or stale listing."
        elif is_old or is_stale:
            reality_class = "stale"
            label = "🟡 Stale Listing"
            authenticity_score = 65
            is_ghost = False
            summary = f"Posting has been active for {age_days} days. May still be accepting applications, but hiring may be nearing completion."
        elif age_days <= FRESH_WINDOW_DAYS:
            reality_class = "fresh"
            label = "🟢 Fresh Active Role"
            authenticity_score = 95
            is_ghost = False
            summary = f"Recently published ({age_days}d ago) with genuine active requisition markers."
        else:
            reality_class = "active"
            label = "🔵 Active Opening"
            authenticity_score = 85
            is_ghost = False
            summary = f"Active job listing ({age_days}d old) with no ghost or evergreen warnings."

        return {
            "reality_class": reality_class,
            "label": label,
            "is_ghost": is_ghost,
            "authenticity_score": authenticity_score,
            "age_days": age_days,
            "signals": signals,
            "evergreen_markers": all_markers,
            "summary": summary
        }
