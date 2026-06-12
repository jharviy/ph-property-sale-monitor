"""
Abstract base class for all data source extractors.
Implementing a new source = subclassing BaseExtractor + registering in SOURCES.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path


class BaseExtractor(ABC):
    """
    Contract every source extractor must fulfill.

    Subclasses handle:
    - Authenticating / navigating to the source
    - Downloading the raw file
    - Returning the local path to that file
    """

    source_name: str = ""

    @abstractmethod
    def extract(self, save_dir: Path, run_date: date) -> Path:
        """
        Download raw data from the source and save it locally.

        Args:
            save_dir: Directory where the raw file should be written.
            run_date: The logical date of the scrape run (used for naming).

        Returns:
            Absolute path to the downloaded file.
        """

    @abstractmethod
    def validate_source(self) -> bool:
        """
        Confirm the source URL / endpoint is reachable.

        Returns:
            True if reachable, False otherwise.
        """
