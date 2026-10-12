#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-ku · FASE 2d — Exploración de datasets públicos en Hugging Face.

Busca datasets existentes orientados a los tópicos deficitarios (pwn,
binary-exploitation, ctf, reverse-engineering, exploit-code, osint) y clasifica
cada uno según su licencia DECLARADA (metadatos + tarjeta), sin descargar jamás
su contenido.

REGLA DE LICENCIA ESTRICTA (aplicable solo a datasets de HF, no al código GitHub):
  ACEPTADO   : licencia declarada formalmente permisiva — MIT, Apache-2.0,
               BSD-2/3-Clause, CC-BY-4.0.
  REVISAR    : permisiva declarada PERO compilación de terceros (exige licencias
               por registro o síntesis propia antes de usarla).
  RECHAZADO  : CC-BY-NC*, GPL/AGPL/LGPL, 'other'/privativa, o sin licencia explícita.

Salida: audit/hf_datasets_candidates.json + tabla por consola.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HUB = "https://huggingface.co"
QUERIES = ["pwn", "binary-exploitation", "binary exploitation", "ctf",
           "reverse-engineering", "reverse engineering", "exploit", "exploit-code", "osint"]
PERMISSIVE = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "cc-by-4.0"}
REJECT_PREFIXES = ("cc-by-nc", "gpl", "agpl", "lgpl")
RELEVANCE = ["pwn", "exploit", "ctf", "osint", "reverse engineer", "reverse-engineer",
             "binary exploitation", "offensive", "red team", "red-team", "penetration",
             "hacking", "vulnerab", "security", "capture the flag"]
COMPILATION_HINTS = ["github", "collected", "scraped", "curated", "compilation",
                     "repositories", "repositorios", "corpus of", "compiled from"]
AGGREGATOR_IDS = ("tandevllc",)


def http_json(url, token, timeout=60):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def norm_license(entry):
    """Extrae licencia declarada: cardData.license o tag license:*."""
    lic = (entry.get("cardData") or {}).get("license")
    if not lic:
        for tag in entry.get("tags", []):
            if str(tag).startswith("license:"):
                lic = str(tag)[len("license:"):]
                break
    lic = str(lic or "").strip().lower()
    return lic or "unlabeled"


def main():
    token = os.environ.get("HF_TOKEN", "")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = {}

    for q in QUERIES:
        url = f"{HUB}/api/datasets?search={urllib.parse.quote(q)}&limit=100&full=true"
        try:
            items = http_json(url, token)
        except Exception as e:  # noqa: BLE001
            print(f"[{q}] ERROR: {e}", file=sys.stderr)
            continue
        for it in items:
            did = it.get("id")
            if not did:
                continue
            prev = found.get(did)
            if prev is None or ((it.get("cardData") or {}) and not (prev.get("cardData") or {})):
                found[did] = it
        time.sleep(1.0)
    print(f"datasets encontrados (sin dedup de relevancia): {len(found)}")

    # fallback por dataset si falta cardData (solo para relevantes, tope 40)
    relevant = {}
    for did, it in found.items():
        text = " ".join([
            did, " ".join(str(t) for t in it.get("tags", [])),
            str(it.get("description") or ""), str((it.get("cardData") or {}).get("pretty_name") or ""),
        ]).lower()
        if any(k in text for k in RELEVANCE):
            relevant[did] = it
    fallbacks = 0
    for did, it in list(relevant.items()):
        if not (it.get("cardData") or {}).get("license") and fallbacks < 40:
            try:
                full = http_json(f"{HUB}/api/datasets/{did}?full=true", token)
                relevant[did] = full
                fallbacks += 1
                time.sleep(0.4)
            except Exception:  # noqa: BLE001
                pass
    print(f"relevantes tras filtro: {len(relevant)} (fallbacks de tarjeta: {fallbacks})")

    rows = []
    for did, it in sorted(relevant.items()):
        lic = norm_license(it)
        desc = str(it.get("description") or "")
        text = " ".join([did, desc, " ".join(str(t) for t in it.get("tags", []))]).lower()
        compilation = any(h in text for h in COMPILATION_HINTS) or any(a in did.lower() for a in AGGREGATOR_IDS)

        if any(did.lower().startswith(a) or a in did.lower() for a in AGGREGATOR_IDS) or lic == "other":
            cls, why = "RECHAZADO", "compilación privativa o licencia 'other' declarada"
        elif lic == "unlabeled":
            cls, why = "RECHAZADO", "sin licencia explícita en metadatos/tarjeta"
        elif lic.startswith(REJECT_PREFIXES):
            cls, why = "RECHAZADO", f"licencia no admisible: {lic}"
        elif lic not in PERMISSIVE:
            cls, why = "RECHAZADO", f"licencia fuera de la lista permisiva: {lic}"
        elif compilation:
            cls, why = "REVISAR", f"permisiva ({lic}) pero parece compilación de terceros: exigir licencias por registro o síntesis propia"
        else:
            cls, why = "ACEPTADO", f"licencia declarada permisiva: {lic}"

        rows.append({
            "id": did,
            "likes": it.get("likes", 0),
            "downloads": it.get("downloads", 0),
            "declared_license": lic,
            "classification": cls,
            "reason": why,
            "compilation_risk": compilation,
            "last_modified": it.get("lastModified"),
        })

    order = {"ACEPTADO": 0, "REVISAR": 1, "RECHAZADO": 2}
    rows.sort(key=lambda r: (order[r["classification"]], -r["likes"]))
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "rule": "Solo datasets con licencia declarada permisiva (MIT, Apache-2.0, BSD-2/3, CC-BY-4.0). NC/GPL/other/sin licencia → rechazado. Compilaciones permisivas → revisar (licencias por registro o síntesis propia).",
        "queries": QUERIES,
        "counts": {c: sum(1 for r in rows if r["classification"] == c)
                   for c in ("ACEPTADO", "REVISAR", "RECHAZADO")},
        "candidates": rows,
    }
    with open(os.path.join(root, "audit", "hf_datasets_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"\n== CANDIDATOS HF (clasificación por licencia declarada) ==")
    print(f"   ACEPTADO: {out['counts']['ACEPTADO']} · REVISAR: {out['counts']['REVISAR']} · RECHAZADO: {out['counts']['RECHAZADO']}")
    print(f"\n{'dataset':48s} {'licencia':14s} {'likes':>6s} {'cls':9s} motivo")
    print("-" * 110)
    for r in rows:
        if r["classification"] != "RECHAZADO":
            print(f"{r['id']:48s} {r['declared_license']:14s} {r['likes']:>6d} {r['classification']:9s} {r['reason'][:60]}")


if __name__ == "__main__":
    main()
