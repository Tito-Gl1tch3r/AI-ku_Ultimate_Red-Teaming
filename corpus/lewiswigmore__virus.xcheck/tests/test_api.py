"""Tests for VirusExchangeAPI and VirusTotalAPI classes."""

import pytest
from unittest.mock import MagicMock, patch
import requests

from virusxcheck import VirusExchangeAPI, VirusTotalAPI


SAMPLE_HASH = "a" * 64


# --- VirusExchangeAPI Tests ---


class TestVirusExchangeAPIGetSampleDetails:
    """Tests for VirusExchangeAPI.get_sample_details."""

    def _make_api(self):
        api = VirusExchangeAPI(api_key="test-key")
        api.session = MagicMock()
        return api

    def test_200_returns_found(self):
        api = self._make_api()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sha256": SAMPLE_HASH, "tags": ["trojan"]}
        api.session.get.return_value = mock_resp

        result = api.get_sample_details(SAMPLE_HASH)

        assert result["status"] == "Found in VX database"
        assert result["details"] == {"sha256": SAMPLE_HASH, "tags": ["trojan"]}
        assert SAMPLE_HASH in result["virustotal_url"]

    def test_404_returns_not_found(self):
        api = self._make_api()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        api.session.get.return_value = mock_resp

        result = api.get_sample_details(SAMPLE_HASH)

        assert result["status"] == "Not found in VX database"
        assert SAMPLE_HASH in result["virustotal_url"]

    def test_other_status_returns_error(self):
        api = self._make_api()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        api.session.get.return_value = mock_resp

        result = api.get_sample_details(SAMPLE_HASH)

        assert "Error: HTTP 500" in result["status"]
        assert SAMPLE_HASH in result["virustotal_url"]

    def test_request_exception_returns_error(self):
        api = self._make_api()
        api.session.get.side_effect = requests.RequestException("connection failed")

        result = api.get_sample_details(SAMPLE_HASH)

        assert "Request Error" in result["status"]
        assert "connection failed" in result["status"]
        assert SAMPLE_HASH in result["virustotal_url"]


class TestVirusExchangeAPIFallbackCheck:
    """Tests for VirusExchangeAPI.fallback_check."""

    def _make_api(self):
        api = VirusExchangeAPI(api_key="test-key")
        api.session = MagicMock()
        return api

    def test_200_returns_found_with_url(self):
        api = self._make_api()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        api.session.head.return_value = mock_resp

        result = api.fallback_check(SAMPLE_HASH)

        assert "Found in VX database (fallback check)" in result["status"]
        assert result["vx_url"] is not None
        assert SAMPLE_HASH in result["vx_url"]
        assert SAMPLE_HASH in result["virustotal_url"]

    def test_404_returns_not_found(self):
        api = self._make_api()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        api.session.head.return_value = mock_resp

        result = api.fallback_check(SAMPLE_HASH)

        assert result["status"] == "Not found in VX database"
        assert SAMPLE_HASH in result["virustotal_url"]

    def test_request_exception_returns_error(self):
        api = self._make_api()
        api.session.head.side_effect = requests.RequestException("timeout")

        result = api.fallback_check(SAMPLE_HASH)

        assert "Request Error" in result["status"]
        assert "timeout" in result["status"]
        assert SAMPLE_HASH in result["virustotal_url"]


# --- VirusTotalAPI Tests ---


class TestVirusTotalAPIGetFileReport:
    """Tests for VirusTotalAPI.get_file_report."""

    def _make_api(self, api_key="test-vt-key"):
        api = VirusTotalAPI(api_key=api_key)
        api.session = MagicMock()
        return api

    def test_200_returns_parsed_json(self):
        api = self._make_api()
        expected = {"data": {"attributes": {"size": 1234}}}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = expected
        api.session.get.return_value = mock_resp

        result = api.get_file_report(SAMPLE_HASH)

        assert result == expected

    def test_404_returns_error_dict(self):
        api = self._make_api()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        api.session.get.return_value = mock_resp

        result = api.get_file_report(SAMPLE_HASH)

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_no_api_key_returns_none(self):
        api = self._make_api(api_key="")

        result = api.get_file_report(SAMPLE_HASH)

        assert result is None

    def test_request_exception_returns_error_dict(self):
        api = self._make_api()
        api.session.get.side_effect = requests.RequestException("dns failure")

        result = api.get_file_report(SAMPLE_HASH)

        assert "error" in result
        assert "Request Error" in result["error"]


class TestVirusTotalAPIExtractScanResults:
    """Tests for VirusTotalAPI.extract_scan_results."""

    def _make_api(self):
        return VirusTotalAPI(api_key="test-vt-key")

    def test_valid_response_extracts_fields(self):
        api = self._make_api()
        vt_data = {
            "data": {
                "attributes": {
                    "names": ["malware.exe"],
                    "size": 2048,
                    "type_description": "Win32 EXE",
                    "first_submission_date": 1609459200,
                    "last_analysis_date": 1609545600,
                    "times_submitted": 5,
                    "last_analysis_stats": {"malicious": 30, "undetected": 40},
                    "popular_threat_classification": {"suggested_threat_label": "trojan"},
                    "tags": ["peexe"],
                    "last_analysis_results": {
                        "EngineA": {
                            "category": "malicious",
                            "result": "Trojan.Gen",
                            "method": "blacklist",
                            "engine_name": "EngineA",
                            "engine_version": "1.0"
                        }
                    }
                }
            }
        }

        result = api.extract_scan_results(vt_data)

        assert result["names"] == ["malware.exe"]
        assert result["size"] == 2048
        assert result["type_description"] == "Win32 EXE"
        assert result["times_submitted"] == 5
        assert result["last_analysis_stats"] == {"malicious": 30, "undetected": 40}
        assert result["tags"] == ["peexe"]
        assert "EngineA" in result["scan_results"]
        assert result["scan_results"]["EngineA"]["category"] == "malicious"
        assert result["scan_results"]["EngineA"]["result"] == "Trojan.Gen"

    def test_error_response_passes_through(self):
        api = self._make_api()
        error_data = {"error": "File not found on VirusTotal"}

        result = api.extract_scan_results(error_data)

        assert result == error_data

    def test_none_input_returns_none(self):
        api = self._make_api()

        result = api.extract_scan_results(None)

        assert result is None
