"""Unit tests for the BSP transformer."""
import pytest
import pandas as pd

from src.transformers.bsp_transformer import BSPTransformer, _DIVIDER_RE
from src.utils.address_parser import parse_address
from src.utils.ph_regions import get_region


# ── Address parser ────────────────────────────────────────────────────────────

class TestParseAddress:
    def test_three_part_address(self):
        city, province = parse_address("Lot 778, Igbaras, Iloilo")
        assert province == "Iloilo"
        assert city == "Igbaras"

    def test_n_a_prefix(self):
        city, province = parse_address("n/aPakiing, Mulanay, Quezon")
        assert province == "Quezon"

    def test_parenthetical_stripped(self):
        _, province = parse_address("Lot 1, San Francisco (Aurora), Quezon")
        assert province == "Quezon"

    def test_single_word(self):
        city, province = parse_address("Iloilo")
        assert city is None
        assert province == "Iloilo"

    def test_none_returns_none(self):
        assert parse_address(None) == (None, None)

    def test_empty_returns_none(self):
        assert parse_address("") == (None, None)


# ── Region lookup ─────────────────────────────────────────────────────────────

class TestGetRegion:
    def test_known_province(self):
        assert get_region("Iloilo") == "Region VI"
        assert get_region("Quezon") == "Region IV-A"
        assert get_region("Northern Samar") == "Region VIII"

    def test_case_insensitive(self):
        assert get_region("iloilo") == "Region VI"
        assert get_region("QUEZON") == "Region IV-A"

    def test_unknown_returns_none(self):
        assert get_region("Atlantis") is None

    def test_none_returns_none(self):
        assert get_region(None) is None


# ── Divider regex ─────────────────────────────────────────────────────────────

class TestDividerPattern:
    @pytest.mark.parametrize("val", ["Real Estate", "real estate", "REAL ESTATE",
                                      "Commercial", "Agricultural", "Industrial"])
    def test_matches_dividers(self, val):
        assert _DIVIDER_RE.match(val)

    @pytest.mark.parametrize("val", ["1-0001-000007089", "TD No. 3894", ""])
    def test_no_match_on_valid_data(self, val):
        assert not _DIVIDER_RE.match(val)


# ── BSPTransformer internals ──────────────────────────────────────────────────

class TestBSPTransformer:
    t = BSPTransformer()

    def test_drop_dividers_removes_header_row(self, sample_df_with_divider):
        result = self.t._drop_dividers(sample_df_with_divider)
        assert "Real Estate" not in result["property_acct_no"].values
        assert len(result) == 3

    def test_split_category(self, sample_df):
        df = sample_df.rename(columns={"Category - Classification": "category_classification"})
        result = self.t._split_category(df)
        assert "category" in result.columns
        assert "classification" in result.columns
        assert result["category"].iloc[0] == "Agricultural"
        assert result["classification"].iloc[0] == "Agricultural / Residential"

    def test_coerce_numerics_strips_commas(self, sample_df):
        df = sample_df.rename(columns={
            "Lot Area (sq m)": "lot_area_sqm",
            "Floor Area (sq m)": "floor_area_sqm",
            "Price (Php)": "price_php",
        })
        result = self.t._coerce_numerics(df)
        assert result["lot_area_sqm"].iloc[0] == pytest.approx(4875.0)
        assert result["price_php"].iloc[0] == pytest.approx(464_000.0)

    def test_coerce_zero_floor_area_becomes_nan(self, sample_df):
        df = sample_df.rename(columns={
            "Lot Area (sq m)": "lot_area_sqm",
            "Floor Area (sq m)": "floor_area_sqm",
            "Price (Php)": "price_php",
        })
        result = self.t._coerce_numerics(df)
        import math
        assert all(math.isnan(v) for v in result["floor_area_sqm"])

    def test_full_transform(self, sample_xls, run_date):
        records = self.t.transform(sample_xls, run_date)
        assert len(records) == 3
        assert all(r.source == "BSP" for r in records)
        assert all(r.date_scraped == run_date for r in records)
        # price_per_sqm auto-computed
        assert records[0].price_per_sqm == pytest.approx(464_000 / 4875, rel=1e-3)

    def test_transform_enriches_region(self, sample_xls, run_date):
        records = self.t.transform(sample_xls, run_date)
        regions = {r.region for r in records if r.region}
        assert "Region VI" in regions   # Iloilo
        assert "Region VIII" in regions  # Northern Samar
