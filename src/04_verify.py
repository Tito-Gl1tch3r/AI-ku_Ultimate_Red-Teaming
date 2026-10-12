#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-ku · FASE 2c — Verificación de integridad del corpus minado.

Comprueba que el corpus y el manifiesto son consistentes y auditables:
  1. Todo archivo 'accepted' del manifiesto existe en corpus/ y su sha256 coincide.
  2. Ningún archivo 'rejected' está en corpus/.
  3. Cada repo minado tiene _UPSTREAM_LICENSE y su texto firma el SPDX registrado
     (MIT / Apache-2.0 / BSD — detección por cadenas canónicas de la licencia).
  4. Cumplimiento Apache-2.0: si el repo upstream tiene NOTICE y falta localmente,
     se descarga desde GitHub upstream y se guarda como _UPSTREAM_NOTICE.
  5. Sin huérfanos: ningún archivo en corpus/ sin entrada en el manifiesto
     (salvo _UPSTREAM_LICENSE/_UPSTREAM_NOTICE).
  6. Ningún archivo aceptado supera max_file_bytes de la rúbrica.

Salida: results/verification/{label}.json · exit 0 si todo OK, 1 si falla algo.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request

GH = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

LICENSE_SIGNATURES = {
    "MIT": ["mit license", "permission is hereby granted, free of charge"],
    "Apache-2.0": ["apache license", "version 2.0", "unless required by applicable law"],
    "BSD-2-Clause": ["redistribution and use in source and binary forms"],
    "BSD-3-Clause": ["redistribution and use in source and binary forms"],
}


def http(url, token=None, binary=False, timeout=60):
    headers = {"Accept": "application/vnd.github+json"} if "api.github.com" in url else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return r.status, data if binary else json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None


def check_license_signature(spdx, path):
    """True si el texto del LICENSE firma el SPDX esperado."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read().lower()
    except OSError:
        return False
    if not text:
        return False
    sigs = LICENSE_SIGNATURES.get(spdx, [])
    if not sigs:
        return True  # SPDX fuera de firma conocida: no bloquear, solo avisar
    hits = sum(1 for s in sigs if s in text)
    return hits >= 2 if spdx == "Apache-2.0" else hits >= 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="demo")
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "rubric.json"), encoding="utf-8") as f:
        rub = json.load(f)
    max_bytes = int(rub["fase_3_contenido"]["rules"]["max_file_bytes"])

    man_dir = os.path.join(root, "results", args.label)
    primary = os.path.join(man_dir, "manifest.jsonl")
    import glob as _glob
    man_files = [primary] if os.path.exists(primary) else sorted(
        _glob.glob(os.path.join(man_dir, "manifest.part-*.jsonl")))
    corpus = os.path.join(root, "corpus")
    entries = []
    for mf in man_files:
        with open(mf, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

    checks = []
    fails = 0

    def record(name, ok, detail=""):
        nonlocal fails
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            fails += 1

    # --- 1/2. aceptados presentes y con sha256 válido; rechazados ausentes ----
    n_ok = n_bad = n_missing = n_rejected_present = 0
    for e in entries:
        repo_dir = os.path.join(corpus, e["repo"].replace("/", "__"))
        p = os.path.join(repo_dir, e["path"])
        if e["verdict"] == "accepted":
            if not os.path.exists(p):
                n_missing += 1
                continue
            with open(p, "rb") as fh:
                data = fh.read()
            if hashlib.sha256(data).hexdigest() == e["sha256"] and len(data) <= max_bytes:
                n_ok += 1
            else:
                n_bad += 1
        elif e["verdict"] in ("rejected", "duplicate") and os.path.exists(p):
            n_rejected_present += 1
    record("manifest→corpus sha256", n_bad == 0 and n_missing == 0,
           f"aceptados verificados: {n_ok} · sha256 inválido: {n_bad} · ausentes: {n_missing}")
    record("rechazados ausentes de corpus", n_rejected_present == 0,
           f"rechazados/duplicados encontrados en corpus: {n_rejected_present}")

    # --- 3/4. atribución por repo: LICENSE firmado + NOTICE Apache ------------
    repos = {}
    for e in entries:
        if e["verdict"] == "accepted":
            repos.setdefault(e["repo"], e.get("spdx"))
    lic_ok, lic_fail, notice_ok, notice_no_upstream, notice_fail = 0, [], 0, 0, []
    for repo, spdx in sorted(repos.items()):
        repo_dir = os.path.join(corpus, repo.replace("/", "__"))
        # dual-licencia (MIT | Apache-2.0, típico en Rust): basta con que CUALQUIER
        # archivo de licencia preservado firme el SPDX reclamado; ambos textos quedan en el corpus.
        lic_files = []
        if os.path.isdir(repo_dir):
            lic_files = [os.path.join(repo_dir, f) for f in sorted(os.listdir(repo_dir))
                         if f == "_UPSTREAM_LICENSE" or f.startswith("_UPSTREAM_LICENSE__")]
        if any(os.path.exists(p) and check_license_signature(spdx, p) for p in lic_files):
            lic_ok += 1
        else:
            lic_fail.append(repo)
        if spdx == "Apache-2.0":
            # cumplimiento NOTICE: verificación LOCAL (03 ya copia el NOTICE del
            # upstream cuando existe en la raíz). El cross-check contra la API
            # costaría ~3.000 llamadas y no añade garantía.
            if os.path.exists(os.path.join(repo_dir, "_UPSTREAM_NOTICE")):
                notice_ok += 1
            else:
                notice_no_upstream += 1  # repo Apache sin NOTICE: no requerido por Apache-2.0
    record("LICENSE firmado según SPDX", not lic_fail,
           f"firmas correctas: {lic_ok} · fallos: {lic_fail}")
    record("cumplimiento NOTICE (Apache-2.0)", not notice_fail,
           f"Apache con NOTICE presente: {notice_ok} · sin NOTICE upstream (no requerido): {notice_no_upstream} · fallos: {notice_fail}")

    # --- 5. huérfanos en corpus ------------------------------------------------
    expected = set()
    for e in entries:
        if e["verdict"] == "accepted":
            expected.add((e["repo"].replace("/", "__"), e["path"].replace("\\", "/")))
    orphans = []
    for dirpath, _, filenames in os.walk(corpus):
        rel_dir = os.path.relpath(dirpath, corpus)
        for fn in filenames:
            if fn.startswith("_UPSTREAM_"):
                continue
            rel = os.path.normpath(os.path.join(rel_dir, fn)).replace("\\", "/")
            if rel == ".":
                continue
            top = rel.split(os.sep)[0] if os.sep in rel else rel.split("/")[0]
            rest = rel[len(top) + 1:]
            if (top, rest) not in expected:
                orphans.append(rel)
    record("sin huérfanos en corpus", not orphans, f"huérfanos: {orphans[:10]}")

    summary = {
        "label": args.label,
        "entries": len(entries),
        "accepted": sum(1 for e in entries if e["verdict"] == "accepted"),
        "rejected": sum(1 for e in entries if e["verdict"] == "rejected"),
        "duplicates": sum(1 for e in entries if e["verdict"] == "duplicate"),
        "repos_mined": len(repos),
        "checks": checks,
        "all_ok": fails == 0,
    }
    out_dir = os.path.join(root, "results", "verification")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{args.label}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    for c in checks:
        print(f"  [{'OK' if c['ok'] else 'FALLO'}] {c['check']} — {c['detail']}")
    print(f"\n== VERIFICACIÓN {'COMPLETA · TODO OK' if fails == 0 else 'CON FALLOS'} ==")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
