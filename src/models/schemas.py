"""
Pydantic schemas: runtime validation and serialization layer.
These are transport/validation objects, not ORM models.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class PropertyRecord(BaseModel):
    """Represents one validated, transformed property listing."""

    property_acct_no: str
    category: Optional[str] = None
    classification: Optional[str] = None
    tct_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    region: Optional[str] = None
    lot_area_sqm: Optional[float] = None
    floor_area_sqm: Optional[float] = None
    price_php: Optional[float] = None
    price_per_sqm: Optional[float] = None   # computed
    other_remarks: Optional[str] = None
    source: str = "BSP"
    date_scraped: date

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("property_acct_no")
    @classmethod
    def non_empty_acct_no(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("property_acct_no must not be empty")
        return v

    @field_validator("lot_area_sqm", "floor_area_sqm", "price_php", mode="before")
    @classmethod
    def coerce_numeric(cls, v):
        """Accept strings with commas, strip whitespace, reject negatives."""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.replace(",", "").strip()
            if v in ("", "nan", "None", "N/A", "n/a"):
                return None
        try:
            result = float(v)
            return None if (math.isnan(result) or result < 0) else result
        except (ValueError, TypeError):
            return None

    @field_validator("category", "classification", "tct_number", "address",
                     "city", "province", "region", "other_remarks", mode="before")
    @classmethod
    def clean_string(cls, v):
        """Strip whitespace; replace empty / null-ish strings with None."""
        if v is None:
            return None
        v = str(v).strip()
        return None if v.lower() in ("", "nan", "none", "n/a") else v

    @model_validator(mode="after")
    def compute_derived_fields(self) -> "PropertyRecord":
        """Auto-compute price per sqm from price and lot area."""
        # BSP encodes 'no floor area' as 0.00 — already coerced to None above.
        # Use lot_area as primary denominator; fall back to floor_area.
        area = self.lot_area_sqm or self.floor_area_sqm
        if self.price_php and area and area > 0:
            self.price_per_sqm = round(self.price_php / area, 2)
        return self


class ScrapeRunRecord(BaseModel):
    """Metadata logged for every pipeline execution."""

    source: str
    date_scraped: date
    records_extracted: int = 0
    records_loaded: int = 0
    status: str = "pending"          # pending | success | failed
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
