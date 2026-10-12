#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-ku · FASE 2e — Expansión dirigida en GitHub (tópicos deficitarios).

Compensa el desbalance de 'pwn', 'exploit' y 'osint' (los de menor % de licencia
permisiva en el catálogo heredado de HF):

  1. topic:{t} stars:>=25  → baja el corte de popularidad (el código de nicho
     técnico especializado en pwn/reversing suele tener pocas estrellas).
  2. Búsquedas por palabra clave (writeups, exploit development, osint tooling).
  3. Orgs curadas con tooling de seguridad y plataformas CTF:
     pwn-college (pwn.college), Gallopsled (pwntools), specterops, nccgroup,
     googleprojectzero.

Los repos NUEVOS se añaden a catalog/{topic}.json con campo "discovery" —
nunca se eliminan los existentes. La puerta de licencia (02) se aplica igual:
solo SPDX permisivo pasa a minería.

Uso:
  export GITHUB_TOKEN=...
  python src/05_expand_github.py [--pages 10] [--stars 25]
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

GH = "https://api.github.com"
TARGETS = {
    "pwn": ["pwn writeup", "ctf pwn", "exploit development"],
    "exploit": ["exploit writeup", "exploit development", "vulnerability research"],
    "osint": ["osint framework", "osint tool", "osint tooling"],
}
CURATED_ORGS = ["pwn-college", "Gallopsled", "specterops", "nccgroup", "googleprojectzero"]


def http_json(url, token, timeout=60):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8")), dict(r.headers)


def gh_search(q, token, pages, per_page=100):
    out, seen = [], set()
    for page in range(1, pages + 1):
        url = (f"{GH}/search/repositories?q={urllib.parse.quote(q)}"
               f"&sort=stars&order=desc&per_page={per_page}&page={page}")
        try:
            d, _ = http_json(url, token)
        except Exception as e:  # noqa: BLE001
            print(f"    search error ({q}): {e}", file=sys.stderr)
            break
        items = d.get("items", [])
        for it in items:
            fn = it.get("full_name")
            if fn and fn not in seen:
                seen.add(fn)
                out.append({
                    "repo": fn, "stars": it.get("stargazers_count", 0),
                    "spdx_hint": (it.get("license") or {}).get("spdx_id"),
                    "size_kb": it.get("size", 0), "fork": it.get("fork", False),
                })
        if len(items) < per_page:
            break
        time.sleep(2.5)  # Search API: 30 req/min
    return out


def org_repos(org, token):
    """Org pública → lista de repos (hasta 300); fallback a user."""
    out = []
    for endpoint in (f"{GH}/orgs/{org}/repos", f"{GH}/users/{org}/repos"):
        for page in range(1, 4):
            url = f"{endpoint}?per_page=100&page={page}"
            try:
                items, _ = http_json(url, token)
            except Exception:  # noqa: BLE001
                items = []
            if not items:
                break
            for it in items:
                out.append({
                    "repo": it.get("full_name"), "stars": it.get("stargazers_count", 0),
                    "spdx_hint": (it.get("license") or {}).get("spdx_id"),
                    "size_kb": it.get("size", 0), "fork": it.get("fork", False),
                })
            if len(items) < 100:
                break
        if out:
            return out, endpoint.split("/")[3]
    return [], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=10, help="páginas de search por consulta (100/página)")
    ap.add_argument("--stars", type=int, default=25, help="corte mínimo de estrellas")
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        sys.exit("ERROR: exporta GITHUB_TOKEN.")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cat_dir = os.path.join(root, "catalog")

    # orgs curadas (una vez)
    curated = {}
    for org in CURATED_ORGS:
        repos, kind = org_repos(org, token)
        curated[org] = repos
        print(f"[curated] {org:20s} ({kind or 'NO ENCONTRADA'}): {len(repos)} repos")
        time.sleep(1.0)
    curated_pool = {}
    for org, repos in curated.items():
        for r in repos:
            if r["repo"] and not r.get("fork"):
                r = dict(r)
                r["discovery"] = f"curated-org:{org}"
                curated_pool[r["repo"]] = r

    for topic, extra_qs in TARGETS.items():
        path = os.path.join(cat_dir, f"{topic}.json")
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        before = {r["repo"] for r in entry["repos"]}
        added = []

        queries = [f"topic:{topic} stars:>={args.stars}"] + [f"{q} stars:>={args.stars}" for q in extra_qs]
        for q in queries:
            found = gh_search(q, token, args.pages)
            tag = "topic-stars" if q.startswith("topic:") else "keyword"
            for r in found:
                if r["repo"] in before or r["repo"] in {a["repo"] for a in added}:
                    continue
                if r.get("fork"):
                    continue
                r2 = dict(r)
                r2["discovery"] = f"{tag}:{q}"
                added.append(r2)
            print(f"  [{topic}] +{q!r}: {len(found)} resultados, {len(added)} nuevos acumulados")
            time.sleep(2.5)

        for repo, r in curated_pool.items():
            if repo not in before and repo not in {a["repo"] for a in added}:
                added.append(r)

        entry["repos"] = entry["repos"] + added
        entry["n_repos"] = len(entry["repos"])
        entry["source"] = entry.get("source", "") + "+expansion(stars>=25,keyword,curated-orgs)"
        entry.setdefault("_meta", {})["expansion"] = {
            "run": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "stars_cutoff": args.stars,
            "added": len(added),
            "queries": queries,
            "curated_orgs": CURATED_ORGS,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=1)
        print(f"[{topic}] catálogo: {len(before)} → {len(entry['repos'])} (+{len(added)})")

    print("\n== EXPANSIÓN COMPLETA: re-ejecuta 02 para verificar los nuevos repos ==")


if __name__ == "__main__":
    main()
