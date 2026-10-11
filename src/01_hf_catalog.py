#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-ku · FASE 1 — Catálogo de repositorios (ARQUITECTURA CLEAN-ROOM).

Función: construir el catálogo de repositorios upstream SIN descargar ni un byte
de contenido del dataset de Hugging Face. Dos fuentes, por config/tópico:

  a) "hf-statistics"   → endpoint /statistics de datasets-server: agregación
     server-side. Devuelve frecuencias de repo_name (nº de archivos por repo).
     Solo metadatos; jamás la columna `content`.
  b) "github-topics"    → fallback (configs de cardinalidad alta donde el servidor
     omite las frecuencias): Search API de GitHub `topic:{t}` ordenado por
     estrellas. Descubrimiento 100% independiente de Hugging Face.

Salidas:
  catalog/{topic}.json       catálogo por tópico (fuente + repos)
  catalog/_union.json        unión deduplicada de todos los repos con sus tópicos
  audit/topics_audit.json    auditoría de estructura del dataset (shards, filas, fuente)

Uso:
  export HF_TOKEN=...        # lectura; gate del dataset aceptado
  export GITHUB_TOKEN=...    # lectura (search)
  python src/01_hf_catalog.py [--fallback-pages 5]
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

DS = "https://datasets-server.huggingface.co"
HUB = "https://huggingface.co/api/datasets"
GH = "https://api.github.com"
DATASET = "tandevllc/offsec_redteam_codes"

# 30 configs presentes en la revisión actual del dataset (sha 210b925).
# 'raw' (lista obligatoria original) NO existe como config en esta revisión.
CONFIGS = [
    "adversary-emulation", "adversary-simulation", "binary-exploitation", "bug-bounty",
    "bugbounty", "c2", "command-and-control", "ctf", "ethical-hacking", "exploit",
    "exploitation", "forensics", "lateral-movement", "malware-analysis", "offensive-security",
    "osint", "penetration-testing", "pentesting", "persistence", "post-exploitation",
    "privilege-escalation", "pwn", "recon", "reconnaissance", "red-team", "redteam",
    "reverse-engineering", "security", "threat-hunting", "webhacking",
]
MANDATORY = CONFIGS + ["raw"]  # 31 tópicos de la directiva; 'raw' documentado como ausente


def http_json(url, headers=None, timeout=180, retries=3, backoff=5):
    """GET JSON con reintentos exponenciales."""
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8")), dict(r.headers)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            last = f"HTTP {e.code}: {body}"
            if e.code in (429, 500, 502, 503):
                time.sleep(backoff * (i + 1))
                continue
            raise RuntimeError(f"{url} → {last}") from e
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(backoff * (i + 1))
    raise RuntimeError(f"{url} → {last}")


def hf_stats(config, token):
    """/statistics → (num_examples, partial, repo_freqs, license_freqs, lang_freqs)."""
    url = (f"{DS}/statistics?dataset={urllib.parse.quote(DATASET, safe='')}"
           f"&config={urllib.parse.quote(config, safe='')}&split=train")
    d, _ = http_json(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    out = {"num_examples": d.get("num_examples"), "partial": d.get("partial"),
           "repo_freqs": {}, "license_freqs": {}, "lang_freqs": {}}
    for col in d.get("statistics", []):
        sd = col.get("column_statistics", {})
        if not isinstance(sd, dict):
            continue
        name = col.get("column_name")
        if name == "repo_name" and sd.get("frequencies"):
            out["repo_freqs"] = sd["frequencies"]
        elif name == "license" and sd.get("frequencies"):
            out["license_freqs"] = sd["frequencies"]
        elif name == "lang" and sd.get("frequencies"):
            out["lang_freqs"] = sd["frequencies"]
    return out


def gh_topic_search(topic, token, pages, per_page=100):
    """Search API topic:{t} ordenado por estrellas. Devuelve [(repo, stars)]."""
    found, seen = [], set()
    for page in range(1, pages + 1):
        q = urllib.parse.quote(f"topic:{topic}")
        url = (f"{GH}/search/repositories?q={q}&sort=stars&order=desc"
               f"&per_page={per_page}&page={page}")
        d, hdrs = http_json(url, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        items = d.get("items", [])
        for it in items:
            full = it.get("full_name")
            if full and full not in seen:
                seen.add(full)
                found.append({
                    "repo": full,
                    "stars": it.get("stargazers_count", 0),
                    "spdx_hint": (it.get("license") or {}).get("spdx_id"),
                    "size_kb": it.get("size", 0),
                })
        if len(items) < per_page:
            break
        time.sleep(2.5)  # Search API: 30 req/min autenticado
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fallback-pages", type=int, default=5,
                    help="páginas de Search API por tópico en fallback (100/página)")
    args = ap.parse_args()

    hf_token = os.environ.get("HF_TOKEN", "")
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if not hf_token:
        sys.exit("ERROR: exporta HF_TOKEN (lectura, gate aceptado).")
    if not gh_token:
        sys.exit("ERROR: exporta GITHUB_TOKEN (lectura; necesario para el fallback).")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cat_dir = os.path.join(root, "catalog")
    audit_dir = os.path.join(root, "audit")
    os.makedirs(cat_dir, exist_ok=True)
    os.makedirs(audit_dir, exist_ok=True)

    # --- 0. estructura del dataset (metadatos del Hub) -----------------------
    hub, _ = http_json(f"{HUB}/{DATASET}", headers={"Authorization": f"Bearer {hf_token}"})
    shards = {}
    for s in hub.get("siblings", []):
        name = s.get("rfilename", "")
        if name.endswith(".parquet"):
            cfg = name.split("/")[0]
            shards[cfg] = shards.get(cfg, 0) + 1

    audit = {"dataset": DATASET, "sha": hub.get("sha"), "gated": hub.get("gated"),
             "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "hf_license_note": "compilación TanDev Proprietary — solo catálogo, contenido prohibido",
             "topics": {}}
    union = {}

    for cfg in CONFIGS:
        print(f"[{cfg:22s}] ", end="", flush=True)
        try:
            st = hf_stats(cfg, hf_token)
        except Exception as e:  # noqa: BLE001
            print(f"stats ERROR: {e}")
            audit["topics"][cfg] = {"config": True, "shards": shards.get(cfg, 0), "error": str(e)}
            continue

        if st["repo_freqs"]:
            repos = sorted(
                ({"repo": k, "n_files": v} for k, v in st["repo_freqs"].items()),
                key=lambda r: (-r["n_files"], r["repo"]))
            entry = {
                "topic": cfg, "source": "hf-statistics",
                "num_examples_hf": st["num_examples"], "partial_stats": st["partial"],
                "hf_license_distribution": st["license_freqs"],
                "n_repos": len(repos), "repos": repos,
            }
            for r in repos:
                union.setdefault(r["repo"], {"repo": r["repo"], "topics": [], "n_files": 0})
                union[r["repo"]]["topics"].append(cfg)
                union[r["repo"]]["n_files"] += r["n_files"]
            print(f"hf-statistics  {len(repos):4d} repos (rows={st['num_examples']}, partial={st['partial']})")
        else:
            repos = gh_topic_search(cfg, gh_token, args.fallback_pages)
            entry = {
                "topic": cfg, "source": "github-topics",
                "num_examples_hf": st["num_examples"], "partial_stats": st["partial"],
                "note": "cardinalidad alta: /statistics omite frecuencias de repo_name; catálogo por descubrimiento independiente en GitHub",
                "n_repos": len(repos), "repos": repos,
            }
            for r in repos:
                union.setdefault(r["repo"], {"repo": r["repo"], "topics": [], "n_files": 0, "stars": r.get("stars", 0)})
                union[r["repo"]]["topics"].append(cfg)
            print(f"github-topics {len(repos):4d} repos (rows={st['num_examples']})")

        entry["_meta"] = {"dataset_sha": hub.get("sha"), "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        with open(os.path.join(cat_dir, f"{cfg}.json"), "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=1)

        audit["topics"][cfg] = {
            "config": True, "shards": shards.get(cfg, 0),
            "rows_hf": st["num_examples"], "catalog_source": entry["source"],
            "n_repos": entry["n_repos"], "partial_stats": st["partial"],
        }

    # 'raw': obligatorio en la directiva, ausente como config en esta revisión
    audit["topics"]["raw"] = {
        "config": False, "shards": 0, "rows_hf": None,
        "catalog_source": "none",
        "note": "config inexistente en la revisión actual (sha "
                f"{(hub.get('sha') or '')[:7]}); sin catálogo. Cubierto semánticamente por configs afines (exploit/pwn/ctf).",
    }

    union_list = sorted(union.values(), key=lambda r: (-r.get("n_files", 0), r["repo"]))
    with open(os.path.join(cat_dir, "_union.json"), "w", encoding="utf-8") as f:
        json.dump({"n_repos": len(union_list), "repos": union_list}, f, ensure_ascii=False, indent=1)

    audit["summary"] = {
        "configs": len(CONFIGS),
        "total_shards": sum(shards.values()),
        "repos_unicos_union": len(union_list),
        "por_fuente": {t: a.get("catalog_source") for t, a in audit["topics"].items()},
    }
    with open(os.path.join(audit_dir, "topics_audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)

    print(f"\n== FASE 1 COMPLETA: {len(union_list)} repos únicos en la unión ==")
    print(f"   catálogo: {cat_dir}/  ·  auditoría: {audit_dir}/topics_audit.json")


if __name__ == "__main__":
    main()
