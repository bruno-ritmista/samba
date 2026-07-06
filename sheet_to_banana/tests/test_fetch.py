"""Tests for fetch.py (Increment 1).

These tests never make real network calls — all HTTP is mocked.
"""

import pytest
import requests
from unittest.mock import patch, Mock

from sheet_to_banana.fetch import extract_sheet_info, build_export_url, fetch_csv


# ---------------------------------------------------------------------------
# extract_sheet_info
# ---------------------------------------------------------------------------

class TestExtractSheetInfo:
    def test_edit_url_with_hash_gid(self):
        url = "https://docs.google.com/spreadsheets/d/1abc123XYZ/edit#gid=456789"
        sheet_id, gid = extract_sheet_info(url)
        assert sheet_id == "1abc123XYZ"
        assert gid == "456789"

    def test_edit_url_without_gid(self):
        url = "https://docs.google.com/spreadsheets/d/1abc123XYZ/edit"
        sheet_id, gid = extract_sheet_info(url)
        assert sheet_id == "1abc123XYZ"
        assert gid is None

    def test_export_url_with_query_gid(self):
        url = "https://docs.google.com/spreadsheets/d/1abc123XYZ/export?format=csv&gid=0"
        sheet_id, gid = extract_sheet_info(url)
        assert sheet_id == "1abc123XYZ"
        assert gid == "0"

    def test_share_url_no_gid(self):
        # Share links look like /d/SHEET_ID/view
        url = "https://docs.google.com/spreadsheets/d/abc-DEF_123/view"
        sheet_id, gid = extract_sheet_info(url)
        assert sheet_id == "abc-DEF_123"
        assert gid is None

    def test_invalid_url_raises_value_error(self):
        with pytest.raises(ValueError, match="Not a valid Google Sheets URL"):
            extract_sheet_info("https://example.com/not-a-sheet")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_sheet_info("")


# ---------------------------------------------------------------------------
# build_export_url
# ---------------------------------------------------------------------------

class TestBuildExportUrl:
    def test_with_gid(self):
        url = build_export_url("1abc123", "456")
        assert url == "https://docs.google.com/spreadsheets/d/1abc123/export?format=csv&gid=456"

    def test_without_gid(self):
        url = build_export_url("1abc123", None)
        assert url == "https://docs.google.com/spreadsheets/d/1abc123/export?format=csv"

    def test_gid_zero(self):
        # gid=0 is a valid sheet tab — make sure it is not treated as falsy
        url = build_export_url("1abc123", "0")
        assert "&gid=0" in url


# ---------------------------------------------------------------------------
# fetch_csv
# ---------------------------------------------------------------------------

class TestFetchCsv:
    def _make_mock_response(self, text: str, status_code: int = 200, headers: dict | None = None) -> Mock:
        mock = Mock()
        mock.text = text
        mock.status_code = status_code
        mock.headers = headers if headers is not None else {"Content-Type": "text/csv"}
        if status_code >= 400:
            mock.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        else:
            mock.raise_for_status = Mock()
        return mock

    def test_calls_correct_export_url(self):
        mock_response = self._make_mock_response("col1,col2\nval1,val2")
        with patch("sheet_to_banana.fetch.requests.get", return_value=mock_response) as mock_get:
            fetch_csv("https://docs.google.com/spreadsheets/d/MYID/edit")
            mock_get.assert_called_once_with(
                "https://docs.google.com/spreadsheets/d/MYID/export?format=csv", timeout=15
            )

    def test_includes_gid_when_present(self):
        mock_response = self._make_mock_response("a,b")
        with patch("sheet_to_banana.fetch.requests.get", return_value=mock_response) as mock_get:
            fetch_csv("https://docs.google.com/spreadsheets/d/MYID/edit#gid=99")
            mock_get.assert_called_once_with(
                "https://docs.google.com/spreadsheets/d/MYID/export?format=csv&gid=99", timeout=15
            )

    def test_returns_csv_text(self):
        expected = "instrument,note\nCaixa,X"
        mock_response = self._make_mock_response(expected)
        with patch("sheet_to_banana.fetch.requests.get", return_value=mock_response):
            result = fetch_csv("https://docs.google.com/spreadsheets/d/MYID/edit")
        assert result == expected

    def test_raises_on_http_error(self):
        mock_response = self._make_mock_response("", status_code=403)
        with patch("sheet_to_banana.fetch.requests.get", return_value=mock_response):
            with pytest.raises(Exception):
                fetch_csv("https://docs.google.com/spreadsheets/d/MYID/edit")

    def test_raises_on_invalid_url(self):
        with pytest.raises(ValueError):
            fetch_csv("https://not-a-google-sheet.com/something")

    def test_raises_clear_message_on_html_content_type(self):
        # Private sheets redirect to a sign-in page: 200 OK with an HTML body.
        mock_response = self._make_mock_response(
            "<html>sign in</html>", headers={"Content-Type": "text/html; charset=utf-8"}
        )
        with patch("sheet_to_banana.fetch.requests.get", return_value=mock_response):
            with pytest.raises(Exception, match="doesn't look public"):
                fetch_csv("https://docs.google.com/spreadsheets/d/MYID/edit")

    def test_raises_clear_message_on_timeout(self):
        with patch("sheet_to_banana.fetch.requests.get", side_effect=requests.exceptions.Timeout):
            with pytest.raises(Exception, match="check your internet connection"):
                fetch_csv("https://docs.google.com/spreadsheets/d/MYID/edit")
