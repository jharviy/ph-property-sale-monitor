"""
BSP (Bangko Sentral ng Pilipinas) asset properties extractor.

The BSP publishes a fresh XLS snapshot daily at a stable URL.
No browser interaction is required — the download endpoint is stateless.
"""
from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import requests
from loguru import logger

from config.settings import REQUEST_HEADERS, REQUEST_RETRY_COUNT, REQUEST_TIMEOUT, SOURCES
from src.extractors.base_extractor import BaseExtractor


class BSPExtractor(BaseExtractor):
    """Downloads the BSP foreclosed-properties XLS file."""

    source_name = "BSP"

    def __init__(self) -> None:
        cfg = SOURCES["BSP"]
        self._download_url: str = cfg["download_url"]
        self._extension: str = cfg["file_extension"]

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_source(self) -> bool:
        """HEAD-request the download URL to verify availability."""
        try:
            resp = requests.head(
                self._download_url,
                headers=REQUEST_HEADERS,
                timeout=10,
                allow_redirects=True,
            )
            ok = resp.status_code < 400
            if ok:
                logger.debug(f"BSP source reachable (HTTP {resp.status_code})")
            else:
                logger.warning(f"BSP source returned HTTP {resp.status_code}")
            return ok
        except requests.RequestException as exc:
            logger.warning(f"BSP source validation failed: {exc}")
            return False

    def extract(self, save_dir: Path, run_date: date) -> Path:
        """
        Download the daily BSP XLS file.

        Caches by date — re-running on the same day returns the existing file
        without hitting the network again.

        Returns:
            Path to the (possibly cached) downloaded file.
        """
        filename = f"bsp_properties_{run_date.isoformat()}{self._extension}"
        output_path = save_dir / filename

        if output_path.exists():
            logger.info(f"Cache hit — skipping download: {output_path.name}")
            return output_path

        logger.info(f"Downloading: {self._download_url}")

        for attempt in range(1, REQUEST_RETRY_COUNT + 1):
            try:
                response = requests.get(
                    self._download_url,
                    headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    stream=True,
                )
                response.raise_for_status()

                output_path.write_bytes(response.content)
                size_kb = len(response.content) / 1024
                logger.success(
                    f"Downloaded {size_kb:.1f} KB → {output_path.name}"
                )
                return output_path

            except requests.RequestException as exc:
                logger.warning(f"Attempt {attempt}/{REQUEST_RETRY_COUNT} failed: {exc}")
                if attempt < REQUEST_RETRY_COUNT:
                    time.sleep(2 ** attempt)  # exponential back-off
                else:
                    raise RuntimeError(
                        f"BSP download failed after {REQUEST_RETRY_COUNT} attempts: {exc}"
                    ) from exc

        raise RuntimeError("Unexpected exit from retry loop")  # unreachable
