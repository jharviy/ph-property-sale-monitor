"""
Abstract base class for all data transformers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import List

from src.models.schemas import PropertyRecord


class BaseTransformer(ABC):
    """
    Contract every source transformer must fulfill.

    Subclasses handle:
    - Parsing source-specific file format / structure
    - Cleaning and normalising raw data
    - Validating rows as PropertyRecord objects
    """

    source_name: str = ""

    @abstractmethod
    def transform(self, raw_file: Path, run_date: date) -> List[PropertyRecord]:
        """
        Parse raw file → list of validated PropertyRecord objects.

        Args:
            raw_file: Path to the downloaded source file.
            run_date: Date associated with this batch.

        Returns:
            List of validated PropertyRecord objects (invalid rows are logged
            and dropped rather than raising exceptions).
        """
