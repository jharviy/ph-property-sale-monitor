"""
Philippine address parser.

BSP addresses are freeform strings like:
  "Lot 778 Pls-613-DIgcabugao, Igbaras, Iloilo"
  "n/aPakiing, Mulanay, Quezon"
  "Part of Lot No. 464Casay, San Francisco (Aurora), Quezon"
  "Lot 043, Sitio GuintobalanBalnasan, San Roque, Northern Samar"

Strategy:
  - Strip noise prefixes (lot numbers, sitio, n/a, etc.)
  - Split on commas
  - Last segment → province candidate
  - Second-to-last segment → city/municipality candidate
"""
from __future__ import annotations

import re

# ── Patterns ──────────────────────────────────────────────────────────────────

# Remove parenthetical notes like "(Aurora)" in city name strings
_PAREN_RE = re.compile(r"\([^)]*\)")

# Common BSP address noise prefixes that aren't part of the location name
_NOISE_PREFIX_RE = re.compile(
    r"^(lot\s+[\w\-]+,?\s*|block\s+[\w\-]+,?\s*|blk\.?\s*[\w\-]+,?\s*"
    r"|n/?a\s*|part\s+of\s+lot\s+[^,]+,\s*"
    r"|sitio\s+\w+,?\s*|brgy\.?\s+[\w\s-]+,?\s*)",
    re.IGNORECASE,
)


def parse_address(address: str | None) -> tuple[str | None, str | None]:
    """
    Parse a BSP address string into (city, province).

    Returns:
        (city, province) — either or both may be None if unparseable.
    """
    if not address or not isinstance(address, str):
        return None, None

    # Remove parenthetical strings
    cleaned = _PAREN_RE.sub("", address).strip()

    # Split on commas, discard empties
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]

    if len(parts) >= 2:
        province_candidate = parts[-1]
        city_candidate = parts[-2]

        # Reject obviously-non-location last parts (e.g. TCT refs, lot refs)
        if re.match(r"^[\w\s\-]+$", province_candidate):
            return city_candidate or None, province_candidate or None
        else:
            return None, None

    if len(parts) == 1:
        return None, parts[0]

    return None, None
