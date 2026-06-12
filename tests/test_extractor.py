"""Unit tests for the BSP extractor (network calls mocked)."""
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.bsp_extractor import BSPExtractor


class TestBSPExtractor:
    def test_validate_source_returns_true_on_200(self):
        extractor = BSPExtractor()
        with patch("requests.head") as mock_head:
            mock_head.return_value = MagicMock(status_code=200)
            assert extractor.validate_source() is True

    def test_validate_source_returns_false_on_exception(self):
        extractor = BSPExtractor()
        with patch("requests.head", side_effect=Exception("timeout")):
            assert extractor.validate_source() is False

    def test_extract_returns_cached_file(self, tmp_path, run_date):
        extractor = BSPExtractor()
        cached = tmp_path / f"bsp_properties_{run_date.isoformat()}.xls"
        cached.write_bytes(b"cached content")

        with patch("requests.get") as mock_get:
            result = extractor.extract(tmp_path, run_date)
            mock_get.assert_not_called()  # should not hit network
        assert result == cached

    def test_extract_downloads_when_no_cache(self, tmp_path, run_date):
        extractor = BSPExtractor()
        dummy_content = b"fake xls bytes"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = dummy_content
        mock_response.raise_for_status = lambda: None

        with patch("requests.get", return_value=mock_response):
            result = extractor.extract(tmp_path, run_date)

        assert result.exists()
        assert result.read_bytes() == dummy_content

    def test_extract_retries_on_failure(self, tmp_path, run_date):
        extractor = BSPExtractor()

        import requests as req
        side_effects = [
            req.RequestException("fail 1"),
            req.RequestException("fail 2"),
            req.RequestException("fail 3"),
        ]

        with patch("requests.get", side_effect=side_effects):
            with patch("time.sleep"):  # skip back-off delay in tests
                with pytest.raises(RuntimeError, match="after 3 attempts"):
                    extractor.extract(tmp_path, run_date)
