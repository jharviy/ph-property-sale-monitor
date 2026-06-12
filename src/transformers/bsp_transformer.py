"""
BSP XLS transformer.

XLS file structure (1-indexed rows):
  1–2   : Title rows  ("Bangko Sentral ng Pilipinas", date)
  3–13  : Filter metadata (property type, region, price range, etc.)
  14    : Column headers
  15    : Category divider row  ("Real Estate" spanning all columns)
  16+   : Data rows

Transform steps:
  1. Read XLS, skip 13 metadata rows → row 14 becomes header.
  2. Rename columns to snake_case.
  3. Drop category-divider rows (e.g. "Real Estate").
  4. Parse numeric fields (handle comma separators, coerce 0.00 → None).
  5. Split "Category - Classification" into two columns.
  6. Parse city / province from address.
  7. Enrich province → region via lookup table.
  8. Validate each row with Pydantic; log and drop invalid rows.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger
from pydantic import ValidationError

from config.settings import SOURCES
from src.models.schemas import PropertyRecord
from src.transformers.base_transformer import BaseTransformer
from src.utils.address_parser import parse_address
from src.utils.ph_regions import get_region

# Rows that are section dividers, not actual property records
_DIVIDER_RE = re.compile(
    r"^(real\s+estate|commercial|industrial|agricultural|residential)$",
    re.IGNORECASE,
)

# Expected column names after the header row
_COLUMN_RENAME: dict[str, str] = {
    "Property Acct. No.": "property_acct_no",
    "Category - Classification": "category_classification",
    "TCT Number": "tct_number",
    "Address": "address",
    "Lot Area (sq m)": "lot_area_sqm",
    "Floor Area (sq m)": "floor_area_sqm",
    "Price (Php)": "price_php",
    "Other Remarks": "other_remarks",
}


class BSPTransformer(BaseTransformer):
    """Transforms BSP XLS downloads into validated PropertyRecord lists."""

    source_name = "BSP"
    # _METADATA_ROWS: int = SOURCES["BSP"]["metadata_rows"]

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_engine(path: Path) -> str:
        """Pick the right pandas Excel engine from the file extension."""
        ext = path.suffix.lower()
        if ext == ".xls":
            return "xlrd"
        if ext in (".xlsx", ".xlsm"):
            return "openpyxl"
        raise ValueError(f"Unsupported Excel format: {ext!r}")

    def _read_raw(self, path: Path) -> pd.DataFrame:
        """Load XLS and do minimal structural normalisation."""
        engine = self._detect_engine(path)

        df_list = pd.read_html(
            path,
            header=0,                       # Works identical: sets the first remaining row as header
            )
        # df_list[1].to_csv("check.csv", index=False)
        df = df_list[1].astype(str).replace('nan', None)
        # df = pd.read_excel(
        #     path,
        #     skiprows=self._METADATA_ROWS,   # skip rows 1–13; row 14 → header
        #     header=0,
        #     engine=engine,
        #     dtype=str,                       # read everything as str first
        # )
        # Normalise column names
        df.columns = [str(c).strip() for c in df.columns]
        df = df.rename(columns=_COLUMN_RENAME)
        return df

    @staticmethod
    def _drop_dividers(df: pd.DataFrame) -> pd.DataFrame:
        """Remove category-divider rows and fully-empty rows."""

        col = "property_acct_no"
        df = df[df[col].notna()].copy()
        df = df[~df[col].str.strip().str.match(_DIVIDER_RE, na=False)].copy()
        df = df[df[col].str.strip().str.len() > 0].copy()
        return df

    @staticmethod
    def _split_category(df: pd.DataFrame) -> pd.DataFrame:
        """Split 'category_classification' → 'category' + 'classification'."""
        if "category_classification" not in df.columns:
            df["category"] = None
            df["classification"] = None
            return df

        split = df["category_classification"].str.split(" - ", n=1, expand=True)
        df["category"] = split.get(0, pd.Series(dtype=str)).str.strip()
        df["classification"] = split.get(1, pd.Series(dtype=str)).str.strip()
        return df.drop(columns=["category_classification"])

    @staticmethod
    def _coerce_numerics(df: pd.DataFrame) -> pd.DataFrame:
        """Remove comma separators; coerce 0.00 floor-area to NaN."""
        for col in ("lot_area_sqm", "floor_area_sqm", "price_php"):
            if col not in df.columns:
                continue
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
                .replace({"nan": None, "": None, "None": None, "N/A": None})
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # BSP uses 0.00 to mean "no floor area data"
        if "floor_area_sqm" in df.columns:
            df["floor_area_sqm"] = df["floor_area_sqm"].replace(0.0, float("nan"))

        return df

    @staticmethod
    def _enrich_location(df: pd.DataFrame) -> pd.DataFrame:
        """Parse city/province from address; look up region."""
        if "address" not in df.columns:
            df["city"] = None
            df["province"] = None
            df["region"] = None
            return df

        parsed = df["address"].map(
            lambda x: parse_address(x) if pd.notna(x) else (None, None)
        )
        df["city"] = parsed.map(lambda t: t[0])
        df["province"] = parsed.map(lambda t: t[1])
        df["region"] = df["province"].map(get_region)
        return df

    # ── Public API ────────────────────────────────────────────────────────────

    def transform(self, raw_file: Path, run_date: date) -> List[PropertyRecord]:
        """
        Full transform pipeline for a BSP XLS file.

        Returns validated PropertyRecord objects; invalid rows are skipped.
        """
        logger.info(f"Transforming: {raw_file.name}")

        df = self._read_raw(raw_file)
        logger.debug(f"Rows after header skip: {len(df)}")

        df = self._drop_dividers(df)
        logger.debug(f"Rows after dropping dividers: {len(df)}")

        df = self._split_category(df)
        df = self._coerce_numerics(df)
        df = self._enrich_location(df)

        df["source"] = self.source_name
        df["date_scraped"] = run_date

        records: List[PropertyRecord] = []
        validation_errors = 0

        for _, row in df.iterrows():
            try:
                record = PropertyRecord(
                    property_acct_no=str(row.get("property_acct_no", "")).strip(),
                    category=row.get("category"),
                    classification=row.get("classification"),
                    tct_number=row.get("tct_number"),
                    address=row.get("address"),
                    city=row.get("city"),
                    province=row.get("province"),
                    region=row.get("region"),
                    lot_area_sqm=row.get("lot_area_sqm"),
                    floor_area_sqm=row.get("floor_area_sqm"),
                    price_php=row.get("price_php"),
                    other_remarks=row.get("other_remarks"),
                    source=str(row.get("source", "BSP")),
                    date_scraped=run_date,
                )
                records.append(record)
            except ValidationError as exc:
                validation_errors += 1
                logger.debug(
                    f"Skipped row {row.get('property_acct_no', '?')}: {exc}"
                )

        logger.success(
            f"Transformation complete — "
            f"{len(records)} valid records | {validation_errors} skipped"
        )
        return records
