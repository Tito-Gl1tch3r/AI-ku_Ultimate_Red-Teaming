#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-ku · FASE 2b — Minería limpia desde GitHub con la rúbrica.

Clona repositorios upstream verificados (licencia permisiva formal) directamente
de GitHub y extrae los archivos que superan la rúbrica (rubric.json). Todo el
criterio es determinista y local: sin LLM, sin contenido de Hugging Face.

Por cada repo: git clone --depth 1 → walk → rúbrica por archivo →
  ACCEPT   → corpus/{owner}__{repo}/{ruta} + copia del LICENSE upstream
  REJECT   → razón determinista registrada en el manifiesto

Salidas (results/{label}/):
  manifest.jsonl   trazabilidad por archivo (repo, commit, sha256, score, razón)
  stats.md         resumen de la tanda
  dedup.json       duplicados exactos por sha256

Uso:
  python src/03_mine_github.py --topics ctf,pwn --repos-per-topic 1 \
      --max-repo-mb 200 --label demo
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

GH_URL = "https://github.com"


# ---------------------------------------------------------------- rúbrica
def load_rubric(root):
    with open(os.path.join(root, "rubric.json"), encoding="utf-8") as f:
        rub = json.load(f)
    r2 = rub["fase_2_rutas"]
    r3 = rub["fase_3_contenido"]["rules"]
    r4 = rub["fase_4_calidad"]
    return {
        "dirs": {d.lower() for d in r2["exclude_dirs"]},
        "files": [p.lower() for p in r2["exclude_file_patterns"]],
        "exts": {e.lower() for e in r2["include_extensions"]},
        "max_bytes": int(r3["max_file_bytes"]),
        "min_bytes": int(r3["min_file_bytes"]),
        "min_useful": int(r3["min_useful_chars"]),
        "scan_head": int(r3["autogen_markers_scan_head"]),
        "autogen": [m.lower() for m in r3["autogen_markers"]],
        "accept_min": int(r4["accept_min_score"]),
        "depth_kw": [k.lower() for k in r4["signals"]["S4_profundidad_tecnica"]["keywords"]],
    }


RE_DEF = re.compile(r"^\s*(def\s|class\s|function\s|func\s|fn\s|impl\s|sub\s|struct\s|public\s|#!/)", re.M)
RE_IMP = re.compile(r"^\s*(import\b|from\s+\S+\s+import|#include|using\b|require\(|use\s)", re.M)
RE_CMT = re.compile(r"^\s*(#|//|\*|/\*)")


def judge_file(rel, data, R):
    """Verdict determinista según rubric.json. Devuelve (verdict, reason, score, meta)."""
    name = os.path.basename(rel).lower()
    segs = [s.lower() for s in rel.split(os.sep)[:-1]]

    if any(s in R["dirs"] for s in segs):
        return "rejected", "PATH_EXCLUDED_DIR", 0, {}
    if any(fnmatch.fnmatch(name, pat) for pat in R["files"]):
        return "rejected", "PATH_EXCLUDED_FILE", 0, {}
    ext = os.path.splitext(name)[1]
    if ext not in R["exts"]:
        return "rejected", "EXT_NOT_ALLOWED", 0, {}

    n_bytes = len(data)
    if n_bytes > R["max_bytes"]:
        return "rejected", "TOO_LARGE", 0, {}
    if b"\x00" in data[:4096]:
        return "rejected", "BINARY_OR_NULL", 0, {}

    text = data.decode("utf-8", "replace")
    useful = len(re.sub(r"\s+", "", text))
    if n_bytes < R["min_bytes"] or useful < R["min_useful"]:
        return "rejected", "TOO_SMALL", 0, {}

    lines = text.splitlines()
    nonempty = [l for l in lines if l.strip()] or [""]
    avg = sum(len(l) for l in nonempty) / len(nonempty)
    max_line = max(len(l) for l in nonempty)
    n_ne = len(nonempty)
    if (n_ne <= 8 and avg >= 180) or (len(lines) <= 2 and max_line > 500):
        return "rejected", "MINIFIED", 0, {}

    head = text[: R["scan_head"]].lower()
    if any(m in head for m in R["autogen"]):
        return "rejected", "AUTOGEN", 0, {}

    # --- puntuación (fase 4) -------------------------------------------------
    score = 0
    n_def = len(RE_DEF.findall(text))
    score += 25 if n_def >= 3 else (10 if n_def >= 1 else 0)
    n_lines = len(lines)
    score += 20 if n_lines >= 40 else (10 if n_lines >= 15 else 0)
    n_cmt = len(RE_CMT.findall(text))
    ratio_cmt = n_cmt / max(1, n_lines)
    score += 15 if (n_cmt >= 3 and ratio_cmt >= 0.04) else 0
    low = text.lower()
    n_depth = sum(1 for k in R["depth_kw"] if k in low)
    score += 20 if n_depth >= 2 else 0
    score += 10 if 1000 <= n_bytes <= 150000 else 0
    n_imp = len(RE_IMP.findall(text))
    score += 10 if n_imp >= 2 else 0

    if score < R["accept_min"]:
        return "rejected", "LOW_SCORE", score, {"n_def": n_def, "n_depth": n_depth}
    return "accepted", None, score, {"n_def": n_def, "n_depth": n_depth, "n_imp": n_imp}


def safe_name(repo):
    return repo.replace("/", "__")


def git_clone(repo, dest, max_mb):
    url = f"{GH_URL}/{repo}.git"
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        out = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--quiet", url, dest],
            capture_output=True, text=True, timeout=900, env=env, check=True)
        sha = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        return sha, None
    except subprocess.TimeoutExpired:
        return None, "CLONE_TIMEOUT"
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or "").strip().splitlines()
        return None, "CLONE_ERROR: " + (msg[-1] if msg else str(e.returncode))


def pick_repo(cands, window):
    """Elige repo determinista: dentro de ventana, el más cercano a 500 KB."""
    lo, hi = window
    inside = [c for c in cands if lo <= (c.get("size_kb") or 0) <= hi]
    pool = inside or cands
    if not pool:
        return None
    anchor = 500 if inside else (lo if all((c.get("size_kb") or 0) < lo for c in pool) else hi)
    return sorted(pool, key=lambda c: (abs((c.get("size_kb") or 0) - anchor), c["repo"]))[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", default="", help="lista csv de tópicos (vacío = todos)")
    ap.add_argument("--repos-per-topic", type=int, default=1)
    ap.add_argument("--max-repo-mb", type=int, default=200)
    ap.add_argument("--min-repo-kb", type=int, default=20)
    ap.add_argument("--window", default="100,3000", help="rango KB preferente para elegir repo demo")
    ap.add_argument("--label", default="demo")
    ap.add_argument("--purge-duplicates", action="store_true")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    R = load_rubric(root)
    ver_path = os.path.join(root, "catalog", "github", "verified.jsonl")
    if not os.path.exists(ver_path):
        sys.exit("ERROR: falta catalog/github/verified.jsonl — ejecuta antes 02_github_verify.py")

    wanted = {t.strip() for t in args.topics.split(",") if t.strip()}
    by_topic = {}
    with open(ver_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("verdict") != "accepted":
                continue
            if rec.get("archived"):
                continue  # flag: no minamos repos archivados (se documentan en stats)
            if (rec.get("size_kb") or 0) > args.max_repo_mb * 1024:
                continue
            if (rec.get("size_kb") or 0) < args.min_repo_kb:
                continue
            for t in rec.get("topics", []):
                if not wanted or t in wanted:
                    by_topic.setdefault(t, []).append(rec)

    window = tuple(int(x) for x in args.window.split(","))
    plan = []
    for t in sorted(by_topic):
        for _ in range(min(args.repos_per_topic, len(by_topic[t]))):
            c = pick_repo(by_topic[t], window)
            if c and c["repo"] not in {p[0] for p in plan}:
                plan.append((t, c))
                by_topic[t].remove(c)
    if not plan:
        sys.exit("ERROR: ningún repo aceptado cumple los criterios de selección.")

    ws = os.path.join(root, ".workspace")
    corpus = os.path.join(root, "corpus")
    res = os.path.join(root, "results", args.label)
    for d in (ws, corpus, res):
        os.makedirs(d, exist_ok=True)

    manifest_path = os.path.join(res, "manifest.jsonl")
    manifest = open(manifest_path, "w", encoding="utf-8")
    stats = {"repos": {}, "by_reason": {}, "accepted": 0, "rejected": 0, "dir_skips": {}}

    print(f"plan de minería: {len(plan)} repos → {[p[1]['repo'] for p in plan]}")
    for topic, rec in plan:
        repo = rec["repo"]
        dest = os.path.join(ws, safe_name(repo))
        if os.path.exists(dest):
            shutil.rmtree(dest)
        print(f"\n[{repo}] clonando… ", end="", flush=True)
        sha, err = git_clone(repo, dest, args.max_repo_mb)
        if err:
            print(err)
            stats["repos"][repo] = {"verdict": "REPO_FAIL", "reason": err, "topic": topic}
            stats["by_reason"][err.split(":")[0]] = stats["by_reason"].get(err.split(":")[0], 0) + 1
            continue
        print(f"commit {sha[:8]}")

        repo_dir = os.path.join(corpus, safe_name(repo))
        os.makedirs(repo_dir, exist_ok=True)
        # atribución: copiar LICENSE (y NOTICE si existe) upstream junto al código
        ATTRIBUTION = {
            "_UPSTREAM_LICENSE": ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt"),
            "_UPSTREAM_NOTICE": ("NOTICE", "NOTICE.txt", "NOTICE.md"),
        }
        for dst_name, candidates in ATTRIBUTION.items():
            for lic in candidates:
                src = os.path.join(dest, lic)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(repo_dir, dst_name))
                    break

        r_accepted = r_rejected = 0
        for dirpath, dirnames, filenames in os.walk(dest):
            rel_dir = os.path.relpath(dirpath, dest)
            pruned = [d for d in dirnames if d.lower() not in R["dirs"]]
            for d in list(dirnames):
                if d not in pruned:
                    stats["dir_skips"][d] = stats["dir_skips"].get(d, 0) + 1
            dirnames[:] = pruned
            for fn in filenames:
                rel = os.path.normpath(os.path.join(rel_dir, fn))
                if rel == ".":
                    continue
                try:
                    with open(os.path.join(dirpath, fn), "rb") as fh:
                        data = fh.read(R["max_bytes"] + 1)
                except OSError:
                    continue
                verdict, reason, score, extra = judge_file(rel, data, R)
                entry = {
                    "repo": repo, "commit": sha, "topic": topic, "path": rel.replace("\\", "/"),
                    "lang": os.path.splitext(fn)[1].lstrip("."), "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "score": score, "verdict": verdict, "reason": reason,
                    "spdx": rec.get("spdx"), "mined_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                }
                manifest.write(json.dumps(entry, ensure_ascii=False) + "\n")
                if verdict == "accepted":
                    tgt = os.path.join(repo_dir, rel)
                    os.makedirs(os.path.dirname(tgt), exist_ok=True)
                    shutil.copy2(os.path.join(dirpath, fn), tgt)
                    r_accepted += 1
                else:
                    r_rejected += 1
                    stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1
        stats["repos"][repo] = {
            "verdict": "MINED", "topic": topic, "spdx": rec.get("spdx"),
            "commit": sha, "accepted": r_accepted, "rejected": r_rejected,
        }
        stats["accepted"] += r_accepted
        stats["rejected"] += r_rejected
        print(f"    aceptados: {r_accepted}  ·  rechazados: {r_rejected}")
        shutil.rmtree(dest, ignore_errors=True)

    manifest.close()

    # dedup exacto por sha256 (mantener primera aparición)
    seen_hash, dups = {}, {}
    with open(manifest_path, encoding="utf-8") as f:
        lines = f.readlines()
    with open(manifest_path, "w", encoding="utf-8") as f:
        for line in lines:
            e = json.loads(line)
            if e["verdict"] == "accepted":
                h = e["sha256"]
                if h in seen_hash:
                    dups[h] = dups.get(h, [])
                    dups[h].append(e["repo"] + ":" + e["path"])
                    e["verdict"] = "duplicate"
                    e["reason"] = "DUPLICATE_OF " + seen_hash[h][0] + ":" + seen_hash[h][1]
                    if args.purge_duplicates:
                        p = os.path.join(corpus, safe_name(e["repo"]), e["path"])
                        if os.path.exists(p):
                            os.remove(p)
                else:
                    seen_hash[h] = (e["repo"], e["path"])
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(res, "dedup.json"), "w", encoding="utf-8") as f:
        json.dump({"duplicates": len(dups), "detail": dups}, f, ensure_ascii=False, indent=1)

    # stats.md
    md = [
        f"# Resultados de minería — tanda `{args.label}`",
        f"\n- Fecha: {time.strftime('%Y-%m-%d %H:%M %z')}",
        f"- Repos minados: {len([r for r in stats['repos'].values() if r['verdict']=='MINED'])}",
        f"- Archivos aceptados: {stats['accepted']}  ·  rechazados: {stats['rejected']}",
        f"- Duplicados exactos eliminados/marcados: {len(dups)}",
        "\n## Por repositorio\n",
        "| repo | tópico | SPDX | commit | aceptados | rechazados |",
        "|---|---|---|---|---:|---:|",
    ]
    for repo, r in stats["repos"].items():
        if r["verdict"] == "MINED":
            md.append(f"| {repo} | {r['topic']} | {r['spdx']} | {r['commit'][:8]} | {r['accepted']} | {r['rejected']} |")
        else:
            md.append(f"| {repo} | {r['topic']} | — | — | 0 | 0 (**{r['reason']}**) |")
    md.append("\n## Razones de rechazo\n")
    md.append("| razón | nº |")
    md.append("|---|---:|")
    for k, v in sorted(stats["by_reason"].items(), key=lambda kv: -kv[1]):
        md.append(f"| {k} | {v} |")
    md.append("\n## Directorios podados en el walk\n")
    md.append(", ".join(f"{k}×{v}" for k, v in sorted(stats["dir_skips"].items())) or "—")
    with open(os.path.join(res, "stats.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\n== FASE 2b COMPLETA ({args.label}) ==")
    print(f"   aceptados: {stats['accepted']} · rechazados: {stats['rejected']} · duplicados: {len(dups)}")
    print(f"   corpus: {corpus}/ · resultados: {res}/")


if __name__ == "__main__":
    main()
