"""Parameter discovery module.

This module gathers URLs from the Wayback CDX API (a GAU-like approach) and
extracts parameter names from querystrings. It also merges results with a
local common-parameters wordlist.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Awaitable, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs

import httpx
from rich.console import Console

console = Console()

from .utils import ModuleResult, async_retry, deduplicate_parameters, info, log_duration, normalize_target, prepare_module_output, print_module_summary, safe_artifact_target_name, setup_logging, skipped_result, skip, success, target_output_dir, warn, write_json, write_jsonl

SOURCE_TIMEOUT = 10.0
SOURCE_RETRIES = 0
SOURCE_TOTAL_TIMEOUT = 20.0
MAX_SOURCE_URLS = 5000
COMMON_CRAWL_INDEX_LIMIT = 1


def _exc_message(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__


async def _fetch_wayback(domain: str, timeout: float = SOURCE_TIMEOUT) -> List[str]:
    # using the Wayback CDX API
    api = f"https://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&fl=original&collapse=urlkey"
    info("Querying Wayback...")
    try:
        client_timeout = httpx.Timeout(timeout, connect=10.0)
        async with httpx.AsyncClient(timeout=client_timeout, follow_redirects=True) as client:
            resp = await async_retry(client.get, api, timeout=client_timeout, max_retries=SOURCE_RETRIES, delay=1.0, backoff=2.0)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        warn(f"Wayback unavailable: {_exc_message(exc)}")
        return []

    urls: List[str] = []
    if isinstance(data, list):
        # The first row may be header; entries are strings
        for entry in data:
            if isinstance(entry, str):
                urls.append(entry)
            elif isinstance(entry, list) and entry:
                urls.append(entry[0])
    urls = urls[:MAX_SOURCE_URLS]
    success(f"Wayback: {len(urls)} URLs")
    return urls


async def _fetch_commoncrawl_indexes(client: httpx.AsyncClient, timeout: httpx.Timeout) -> List[str]:
    resp = await async_retry(client.get, "https://index.commoncrawl.org/collinfo.json", timeout=timeout, max_retries=SOURCE_RETRIES, delay=1.0, backoff=2.0)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        return []
    indexes = []
    for item in data:
        if isinstance(item, dict) and item.get("cdx-api"):
            indexes.append(str(item["cdx-api"]))
    return indexes[:COMMON_CRAWL_INDEX_LIMIT]


async def _fetch_commoncrawl(domain: str, timeout: float = SOURCE_TIMEOUT) -> List[str]:
    info("Querying Common Crawl...")
    urls: List[str] = []
    client_timeout = httpx.Timeout(timeout, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=client_timeout, follow_redirects=True) as client:
            indexes = await _fetch_commoncrawl_indexes(client, client_timeout)
            if not indexes:
                warn("Common Crawl unavailable: no indexes returned")
                return []
            for index_url in indexes:
                if len(urls) >= MAX_SOURCE_URLS:
                    break
                query = f"{index_url}?url=*.{domain}/*&output=json&fl=url&filter=status:200&collapse=urlkey&limit={MAX_SOURCE_URLS}"
                try:
                    resp = await async_retry(client.get, query, timeout=client_timeout, max_retries=SOURCE_RETRIES, delay=1.0, backoff=2.0)
                    resp.raise_for_status()
                except Exception as exc:
                    warn(f"Common Crawl index unavailable: {_exc_message(exc)}")
                    continue
                for line in resp.text.splitlines():
                    if len(urls) >= MAX_SOURCE_URLS:
                        break
                    try:
                        item = json.loads(line)
                        url = str(item.get("url") or "").strip()
                        if url:
                            urls.append(url)
                    except Exception:
                        continue
    except Exception as exc:
        warn(f"Common Crawl unavailable: {_exc_message(exc)}")
        return []

    urls = urls[:MAX_SOURCE_URLS]
    success(f"Common Crawl: {len(urls)} URLs")
    return urls


async def _run_source(name: str, coro: Awaitable[List[str]], total_timeout: float = SOURCE_TOTAL_TIMEOUT) -> List[str]:
    try:
        result = await asyncio.wait_for(coro, timeout=total_timeout)
        return result if isinstance(result, list) else []
    except Exception as exc:
        warn(f"{name} unavailable: {_exc_message(exc)}")
        return []


def _load_common_params() -> Set[str]:
    wl = Path(__file__).parents[1] / "wordlists" / "common_parameters.txt"
    if wl.exists():
        return set(deduplicate_parameters(wl.read_text(encoding="utf-8").splitlines()))
    return set()


def _load_custom_params(wordlist: Optional[Path]) -> Set[str]:
    """Load additional parameter names from a user-provided wordlist."""
    if not wordlist:
        return set()
    if not wordlist.exists():
        warn(f"Wordlist not found, skipping: {wordlist}")
        return set()
    return set(deduplicate_parameters(wordlist.read_text(encoding="utf-8").splitlines()))


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _add_url(source_map: Dict[str, List[str]], source: str, value: object) -> None:
    url = str(value or "").strip()
    if _is_http_url(url):
        source_map.setdefault(source, []).append(url)


def _walk_json_urls(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"url", "final_url", "endpoint", "source", "source_page", "host", "matched", "matched-at"}:
                yield str(item)
            yield from _walk_json_urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_urls(item)
    elif isinstance(value, str):
        yield value


def _load_json_urls(path: Path, source: str, source_map: Dict[str, List[str]]) -> None:
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    for url in _walk_json_urls(data):
        _add_url(source_map, source, url)


def _load_alive_probe_urls(path: Path, source_map: Dict[str, List[str]]) -> None:
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    rows = data if isinstance(data, list) else []
    for row in rows:
        if not isinstance(row, dict) or not row.get("alive"):
            continue
        _add_url(source_map, "Live Discovered", row.get("final_url") or row.get("url"))


def _load_text_urls(path: Path, source: str, source_map: Dict[str, List[str]]) -> None:
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            _add_url(source_map, source, line)
    except Exception:
        return


def _collect_fallback_urls(target_name: str, output: Path) -> Tuple[List[str], Dict[str, int], Dict[str, List[str]]]:
    target_dir = target_output_dir(output, target_name)
    source_map: Dict[str, List[str]] = {}

    _load_json_urls(target_dir / "endpoints" / "endpoints.json", "Endpoint Discovery", source_map)
    _load_text_urls(target_dir / "endpoints" / "endpoints.txt", "Endpoint Discovery", source_map)
    _load_json_urls(target_dir / "js" / "js_files.json", "JavaScript Analysis", source_map)
    _load_text_urls(target_dir / "js" / "js_files.txt", "JavaScript Analysis", source_map)
    _load_alive_probe_urls(target_dir / "probe" / "probe.json", source_map)
    _load_text_urls(target_dir / "probe" / "alive.txt", "Live Discovered", source_map)

    inventory_paths = [
        target_dir / "historical" / "urls.txt",
        target_dir / "historical" / "urls.json",
        target_dir / "urls" / "urls.txt",
        target_dir / "urls" / "urls.json",
        target_dir / "crawl" / "urls.txt",
        target_dir / "crawl" / "urls.json",
        target_dir / "crawler" / "urls.txt",
        target_dir / "crawler" / "urls.json",
    ]
    for path in inventory_paths:
        if path.suffix == ".json":
            source = "Historical URL Inventory" if path.parent.name == "historical" else "Internal URL Inventory"
            _load_json_urls(path, source, source_map)
        else:
            source = "Historical URL Inventory" if path.parent.name == "historical" else "Internal URL Inventory"
            _load_text_urls(path, source, source_map)

    counts = {source: len(list(dict.fromkeys(urls))) for source, urls in source_map.items() if urls}
    urls = list(dict.fromkeys(url for urls_for_source in source_map.values() for url in urls_for_source))
    return urls[:MAX_SOURCE_URLS], counts, source_map


def _has_local_attack_surface(target_name: str, output: Path) -> bool:
    target_dir = target_output_dir(output, target_name)
    paths = [
        target_dir / "probe" / "alive.txt",
        target_dir / "endpoints" / "endpoints.txt",
        target_dir / "js" / "js_files.txt",
    ]
    for path in paths:
        try:
            if path.exists() and any(line.strip() for line in path.read_text(encoding="utf-8").splitlines()):
                return True
        except Exception:
            continue
    return False


async def _extract_params_from_urls(urls: List[str]) -> Set[str]:
    info("Extracting parameters...")
    params: Set[str] = set()
    for u in urls:
        try:
            parsed = urlparse(u)
            qs = parse_qs(parsed.query)
            for k in qs.keys():
                params.add(k)
        except Exception as exc:
            warn(f"Skipping malformed URL during parameter extraction: {exc}")
            continue
    success(f"Parameters found: {len(params)}")
    return params


def _extract_params_sync(urls: List[str]) -> Set[str]:
    params: Set[str] = set()
    for url in urls:
        try:
            parsed = urlparse(url)
            for key in parse_qs(parsed.query).keys():
                params.add(key)
        except Exception:
            continue
    return params


def run(target: str, output: Path, wordlist: Optional[Path] = None, resume: bool = False) -> ModuleResult:
    """Run parameter discovery.

    `target` can be a domain (e.g. example.com) or a path to a file containing
    URLs (one per line).
    """
    target_path = Path(target)
    target_name = safe_artifact_target_name(target_path.stem, "file") if target_path.exists() else normalize_target(target)
    out_dir = prepare_module_output(output, target_name, "parameters", resume=resume)
    log = setup_logging(target_name, output, "parameters")
    started = time.perf_counter()

    info(f"Parameter discovery started for {target}")
    log.info("Starting parameter discovery for %s", target)

    async def _run_all() -> ModuleResult:
        info("Loading target")
        urls: List[str] = []
        used_sources: List[str] = []
        confirmed_urls: List[str] = []
        historical_urls: List[str] = []
        if target_path.exists():
            # assume file of URLs
            urls = [l.strip() for l in target_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            confirmed_urls = urls
            used_sources = ["Input File"] if urls else []
            success(f"Loaded {len(urls)} URLs from file")
        else:
            wayback_urls, commoncrawl_urls = await asyncio.gather(
                _run_source("Wayback", _fetch_wayback(target)),
                _run_source("Common Crawl", _fetch_commoncrawl(target)),
            )
            urls = list(wayback_urls) + list(commoncrawl_urls)
            historical_urls = list(urls)
            source_counts = {
                "Wayback": len(wayback_urls),
                "Common Crawl": len(commoncrawl_urls),
            }
            if not urls:
                info("Attempting fallback URL collection")
                fallback_urls, fallback_counts, fallback_source_map = _collect_fallback_urls(target_name, output)
                for source, count in fallback_counts.items():
                    info(f"{source} URLs loaded: {count}")
                info(f"Total fallback URLs collected: {len(fallback_urls)}")
                urls = fallback_urls
                source_counts.update(fallback_counts)
                confirmed_sources = {"Live Discovered", "Endpoint Discovery", "JavaScript Analysis", "Internal URL Inventory"}
                for source, values in fallback_source_map.items():
                    if source in confirmed_sources:
                        confirmed_urls.extend(values)
                    else:
                        historical_urls.extend(values)
            used_sources = [source for source, count in source_counts.items() if count > 0]

        urls = list(dict.fromkeys(urls))
        confirmed_urls = list(dict.fromkeys(confirmed_urls))
        historical_urls = list(dict.fromkeys(historical_urls))
        log.info("Collected %d source URLs for parameter extraction", len(urls))
        info(f"Collected {len(urls)} URLs for parameter extraction")
        if not urls:
            result = skipped_result("No URL sources available")
            skip("Parameter discovery skipped")
            info(f"Reason: {result.reason}")
            print_module_summary(
                "Parameter Summary",
                {
                    "Target": target_name,
                    "Duration": f"{time.perf_counter() - started:.2f}s",
                    "Parameter Status": "Skipped",
                    "Reason": result.reason,
                },
            )
            log.warning("Parameter discovery skipped: %s", result.reason)
            return result

        found = await _extract_params_from_urls(urls)
        confirmed = _extract_params_sync(confirmed_urls)
        historical = _extract_params_sync(historical_urls)
        historical = {item for item in historical if item.lower() not in {p.lower() for p in confirmed}}
        if not found and not _has_local_attack_surface(target_name, output):
            result = skipped_result("No URL-derived parameters or local attack surface available")
            skip("Parameter discovery skipped")
            info(f"Reason: {result.reason}")
            print_module_summary(
                "Parameter Summary",
                {
                    "Target": target_name,
                    "Duration": f"{time.perf_counter() - started:.2f}s",
                    "Parameter Status": "Skipped",
                    "Reason": result.reason,
                },
            )
            log.warning("Parameter discovery skipped: %s", result.reason)
            return result
        success("Continuing parameter extraction")

        info("Loading parameter wordlists")
        common = _load_common_params()
        custom = _load_custom_params(wordlist)
        merged = deduplicate_parameters([*sorted(found), *sorted(common), *sorted(custom)])
        found_lower = {item.lower() for item in found}
        candidates = [item for item in merged if item.lower() not in found_lower]
        info(f"Parameters found: {len(found)} from URLs; {len(merged)} after wordlist merge")

        info("Writing parameter outputs")
        out_dir.mkdir(parents=True, exist_ok=True)
        info("Writing parameters.txt")
        (out_dir / "parameters.txt").write_text("\n".join(merged), encoding="utf-8")
        (out_dir / "parameters_from_urls.txt").write_text("\n".join(sorted(found)), encoding="utf-8")
        (out_dir / "parameters_confirmed.txt").write_text("\n".join(sorted(confirmed)), encoding="utf-8")
        (out_dir / "parameters_historical.txt").write_text("\n".join(sorted(historical)), encoding="utf-8")
        (out_dir / "parameters_candidate.txt").write_text("\n".join(candidates), encoding="utf-8")
        info("Writing parameters.json")
        classes = {
            **{item.lower(): "confirmed" for item in confirmed},
            **{item.lower(): "historical" for item in historical},
            **{item.lower(): "candidate" for item in candidates},
        }
        write_json(out_dir / "parameters.json", [{"parameter": item, "class": classes.get(item.lower(), "candidate")} for item in merged])
        write_jsonl(out_dir / "parameters.jsonl", [{"parameter": item, "class": classes.get(item.lower(), "candidate")} for item in merged])
        write_json(
            out_dir / "metadata.json",
            {
                "source_counts": {source: len([url for url in values if url]) for source, values in {"confirmed": confirmed_urls, "historical": historical_urls}.items()},
                "confirmed_count": len(confirmed),
                "historical_count": len(historical),
                "candidate_count": len(candidates),
                "total_count": len(merged),
                "used_sources": used_sources,
            },
        )
        if custom:
            (out_dir / "parameters_from_wordlist.txt").write_text("\n".join(sorted(custom)), encoding="utf-8")
        success("Parameter output files written")

        log.info("Found %d URL params, %d common params, %d custom params", len(found), len(common), len(custom))
        success(f"Found {len(found)} parameters from URLs; merged {len(merged)} total")
        success(f"Saved: {out_dir / 'parameters.txt'}")
        print_module_summary(
            "Parameter Summary",
            {
                "Target": target_name,
                "Duration": f"{time.perf_counter() - started:.2f}s",
                "URL Parameters": len(found),
                "URL Sources Used": ", ".join(used_sources) if used_sources else "Not Run",
                "Results Found": len(merged),
                "Output Location": out_dir,
            },
        )
        return ModuleResult()

    try:
        with log_duration(log, "parameters"):
            return asyncio.run(_run_all())
    except Exception as exc:
        log.exception("Parameter discovery failed")
        warn(f"Parameter discovery failed: {exc}")
        return ModuleResult(status="failed", reason=str(exc))


if __name__ == "__main__":
    run("example.com", Path("results"))
