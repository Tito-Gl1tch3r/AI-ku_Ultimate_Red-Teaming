"""Unit tests for CVECache SQLite-backed cache."""

from __future__ import annotations

import tempfile

from tengu.resources.cve import CVECache


class TestCVECacheGetSet:
    def _make_cache(self) -> tuple[CVECache, str]:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            path = tmp.name
        return CVECache(path), path

    def test_get_returns_none_for_missing(self):
        cache, _ = self._make_cache()
        assert cache.get_cve("CVE-2024-9999") is None

    def test_set_and_get_roundtrip(self):
        cache, _ = self._make_cache()
        data = {"id": "CVE-2023-1234", "score": 9.8}
        cache.set_cve("CVE-2023-1234", data)
        result = cache.get_cve("CVE-2023-1234")
        assert result == data

    def test_cve_id_normalized_to_uppercase(self):
        cache, _ = self._make_cache()
        cache.set_cve("cve-2023-1234", {"id": "lower"})
        result = cache.get_cve("CVE-2023-1234")
        assert result is not None

    def test_expired_entry_returns_none(self):
        cache, _ = self._make_cache()
        cache.set_cve("CVE-2023-0001", {"id": "old"})
        # TTL of 0 hours means everything is expired
        result = cache.get_cve("CVE-2023-0001", ttl_hours=0)
        assert result is None

    def test_overwrite_existing_entry(self):
        cache, _ = self._make_cache()
        cache.set_cve("CVE-2023-1234", {"v": 1})
        cache.set_cve("CVE-2023-1234", {"v": 2})
        result = cache.get_cve("CVE-2023-1234")
        assert result == {"v": 2}

    def test_multiple_cve_entries(self):
        cache, _ = self._make_cache()
        for i in range(5):
            cache.set_cve(f"CVE-2023-{i:04d}", {"idx": i})
        for i in range(5):
            result = cache.get_cve(f"CVE-2023-{i:04d}")
            assert result == {"idx": i}


class TestSearchCache:
    def _make_cache(self) -> CVECache:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            path = tmp.name
        return CVECache(path)

    def test_get_search_returns_none_for_missing(self):
        cache = self._make_cache()
        assert cache.get_search("apache remote") is None

    def test_set_and_get_search_roundtrip(self):
        cache = self._make_cache()
        data = {"results": [{"id": "CVE-2021-41773"}], "total": 1}
        cache.set_search("apache-rce", data)
        result = cache.get_search("apache-rce")
        assert result == data

    def test_search_expired_returns_none(self):
        cache = self._make_cache()
        cache.set_search("key", {"x": 1})
        result = cache.get_search("key", ttl_hours=0)
        assert result is None

    def test_search_overwrite(self):
        cache = self._make_cache()
        cache.set_search("key", {"v": 1})
        cache.set_search("key", {"v": 2})
        result = cache.get_search("key")
        assert result == {"v": 2}
