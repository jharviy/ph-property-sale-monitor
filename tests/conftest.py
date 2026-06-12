"""Shared pytest fixtures."""
import io
from datetime import date
from pathlib import Path

import pandas as pd
import pytest


SAMPLE_DATE = date(2026, 6, 12)

# Minimal realistic rows matching the BSP XLS structure post-header
SAMPLE_ROWS = [
    {
        "Property Acct. No.": "1-0001-000007089",
        "Category - Classification": "Agricultural - Agricultural / Residential",
        "TCT Number": "F-970",
        "Address": "Lot 778 Pls-613-DIgcabugao, Igbaras, Iloilo",
        "Lot Area (sq m)": "4,875.00",
        "Floor Area (sq m)": "0.00",
        "Price (Php)": "464,000.00",
        "Other Remarks": None,
    },
    {
        "Property Acct. No.": "1-0001-000007077",
        "Category - Classification": "Agricultural - Cocoland",
        "TCT Number": "TD No. 3894",
        "Address": "n/aPakiing, Mulanay, Quezon",
        "Lot Area (sq m)": "100,000.00",
        "Floor Area (sq m)": "0.00",
        "Price (Php)": "3,800,000.00",
        "Other Remarks": None,
    },
    {
        "Property Acct. No.": "1-0001-000011813",
        "Category - Classification": "Agricultural - Cocoland",
        "TCT Number": "TD No. 102",
        "Address": "Lot 043, Sitio GuintobalanBalnasan, San Roque, Northern Samar",
        "Lot Area (sq m)": "33,085.00",
        "Floor Area (sq m)": "0.00",
        "Price (Php)": "1,257,000.00",
        "Other Remarks": None,
    },
]

DIVIDER_ROW = {k: None for k in SAMPLE_ROWS[0]}
DIVIDER_ROW["Property Acct. No."] = "Real Estate"


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """DataFrame matching BSP column names (after skiprows)."""
    return pd.DataFrame(SAMPLE_ROWS)


@pytest.fixture
def sample_df_with_divider() -> pd.DataFrame:
    """DataFrame that includes a category-divider row."""
    rows = [DIVIDER_ROW] + SAMPLE_ROWS
    return pd.DataFrame(rows)


@pytest.fixture
def sample_xls(tmp_path: Path) -> Path:
    """
    Write a minimal XLS file that mimics the BSP download structure.
    Uses openpyxl (.xlsx) because creating legacy .xls in tests is non-trivial;
    the transformer's engine-detection handles both extensions.
    """
    path = tmp_path / "bsp_properties_2026-06-12.xlsx"

    # 13 metadata rows + header + divider + data
    meta = [["Bangko Sentral ng Pilipinas"]] + [[""] for _ in range(12)]
    header = list(SAMPLE_ROWS[0].keys())
    divider = ["Real Estate"] + [""] * (len(header) - 1)
    data = [[str(r.get(h, "") or "") for h in header] for r in SAMPLE_ROWS]

    all_rows = meta + [header] + [divider] + data
    df_out = pd.DataFrame(all_rows)
    df_out.to_excel(path, index=False, header=False)
    return path


@pytest.fixture
def run_date() -> date:
    return SAMPLE_DATE
