#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-ku · FASE 2a — Verificación de licencias upstream en GitHub.

Puerta dura del pipeline: para cada repo del catálogo, consulta la API de GitHub
(GET /repos/{owner}/{repo}) y valida la licencia FORMAL del repositorio según el
detector licensee de GitHub (que analiza el LICENSE de la raíz). Solo se admiten
los SPDX de la rúbrica (fase_1_licencia.accepted_spdx).

Salidas:
  catalog/github/verified.jsonl   un registro por repo con veredicto y metadatos
  catalog/github/_summary.json    conteos por veredicto/razón y por tópico
  catalog/github/_checkpoint.json punto de reanudación (repo → registro)

Uso:
  export GITHUB_TOKEN=...
  python src/02_github_verify.py [--per-topic 25] [--delay 0.22] [--limit 0]
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

GH = "https://api.github.com"
RUBRIC_KEYS = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"]


def load_accepted_spdx(root):
    with open(os.path.join(root, "rubric.json"), encoding="utf-8") as f:
        rub = json.load(f)
    return rub["fase_1_licencia"]["accepted_spdx"]


def http_json(url, token, timeout=60):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), dict(r.headers), r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        return {"_http_error": e.code, "_body": body}, dict(e.headers), e.code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-topic", type=int, default=0,
                    help="verificar solo el top-N por tópico (0 = todos)")
    ap.add_argument("--delay", type=float, default=0.22, help="segundos entre llamadas API")
    ap.add_argument("--limit", type=int, default=0, help="tope global de repos (0 = sin tope)")
    ap.add_argument("--max-runtime", type=float, default=0,
                    help="salir limpiamente tras N segundos (0 = sin límite); checkpoint reanudable")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        sys.exit("ERROR: exporta GITHUB_TOKEN (lectura).")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cat_dir = os.path.join(root, "catalog")
    out_dir = os.path.join(cat_dir, "github")
    os.makedirs(out_dir, exist_ok=True)
    accepted = load_accepted_spdx(root) or RUBRIC_KEYS

    # colas por tópico desde el catálogo de la fase 1
    queues = {}
    for fn in sorted(os.listdir(cat_dir)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        with open(os.path.join(cat_dir, fn), encoding="utf-8") as f:
            entry = json.load(f)
        topic = entry["topic"]
        repos = entry["repos"]
        if args.per_topic > 0:
            repos = repos[: args.per_topic]
        queues[topic] = [r["repo"] for r in repos]

    # punto de reanudación
    ck_path = os.path.join(out_dir, "_checkpoint.json")
    done = {}
    if os.path.exists(ck_path):
        with open(ck_path, encoding="utf-8") as f:
            done = json.load(f)
        print(f"reanudando: {len(done)} repos ya verificados")

    # unión deduplicada (un repo puede estar en varios tópicos)
    seen, plan = set(), []
    for topic, repos in queues.items():
        for repo in repos:
            if repo not in seen:
                seen.add(repo)
                plan.append((topic, repo))
    if args.limit > 0:
        plan = plan[: args.limit]
    print(f"plan: {len(plan)} repos únicos a verificar "
          f"(per-topic={'todos' if args.per_topic == 0 else args.per_topic})")

    rate_floor = 100
    t0 = time.time()
    for i, (topic, repo) in enumerate(plan, 1):
        if repo in done:
            continue
        data, hdrs, code = http_json(f"{GH}/repos/{repo}", token)

        remaining = hdrs.get("X-RateLimit-Remaining")
        reset = hdrs.get("X-RateLimit-Reset")
        try:
            remaining = int(remaining) if remaining is not None else 9999
        except ValueError:
            remaining = 9999
        if remaining < rate_floor:
            now = time.time()
            try:
                target = int(reset) + 3 if reset else 0
            except (TypeError, ValueError):
                target = 0
            wait = (target - now) if target > now else 60
            wait = max(30.0, min(wait, 3700.0))
            print(f"  [rate-limit] remaining={remaining}; espera {int(wait)}s hasta reset", flush=True)
            left = wait
            while left > 0:  # porciones; NUNCA exceder el presupuesto de runtime del chunk
                elapsed = time.time() - t0
                if args.max_runtime and elapsed > args.max_runtime:
                    break
                budget = (args.max_runtime - elapsed) if args.max_runtime else left
                time.sleep(max(1.0, min(480.0, left, budget)))
                left -= 480.0
            if args.max_runtime and (time.time() - t0) > args.max_runtime:
                break

        if code == 404 or (isinstance(data, dict) and data.get("_http_error") == 404):
            rec = {"repo": repo, "topics": [topic], "verdict": "rejected",
                   "reason": "REPO_MISSING", "spdx": None}
        elif code == 451 or (isinstance(data, dict) and data.get("_http_error") == 451):
            # bloqueo DMCA / legal: veredicto terminal, el repo NO se mina jamás
            rec = {"repo": repo, "topics": [topic], "verdict": "rejected",
                   "reason": "DMCA_BLOCKED", "spdx": None}
        elif code != 200:
            print(f"  [{repo}] HTTP {code}: {str(data.get('_body'))[:80]} — reintentar en siguiente tanda")
            continue
        else:
            spdx = (data.get("license") or {}).get("spdx_id")
            ok = spdx in accepted
            rec = {
                "repo": repo, "topics": [topic],
                "spdx": spdx,
                "verdict": "accepted" if ok else "rejected",
                "reason": None if ok else "LICENSE_NON_PERMISSIVE",
                "size_kb": data.get("size", 0),
                "stars": data.get("stargazers_count", 0),
                "language": data.get("language"),
                "archived": data.get("archived", False),
                "default_branch": data.get("default_branch"),
                "pushed_at": data.get("pushed_at"),
            }
        done[repo] = rec
        if i % 50 == 0 or i == len(plan):
            with open(ck_path, "w", encoding="utf-8") as f:
                json.dump(done, f, ensure_ascii=False)
            print(f"  {i}/{len(plan)} verificados ({sum(1 for r in done.values() if r['verdict']=='accepted')} aceptados)", flush=True)
        if args.max_runtime and (time.time() - t0) > args.max_runtime:
            with open(ck_path, "w", encoding="utf-8") as f:
                json.dump(done, f, ensure_ascii=False)
            print(f"  --max-runtime alcanzado ({int(time.time()-t0)}s): {len(done)}/{len(plan)} verificados. Reanudable.", flush=True)
            break
        time.sleep(args.delay)

    with open(ck_path, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False)

    # consolidar tópicos (un repo verificado una vez, tópicos agregados)
    topic_map = {}
    for t, repos in queues.items():
        for r in repos:
            topic_map.setdefault(r, []).append(t)
    records = []
    for repo, rec in done.items():
        rec["topics"] = topic_map.get(repo, rec.get("topics", []))
        records.append(rec)

    out_path = os.path.join(out_dir, "verified.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in sorted(records, key=lambda r: r["repo"]):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    by_reason, by_topic_acc = {}, {}
    for rec in records:
        by_reason[rec.get("reason") or "accepted"] = by_reason.get(rec.get("reason") or "accepted", 0) + 1
        if rec["verdict"] == "accepted":
            for t in rec["topics"]:
                by_topic_acc[t] = by_topic_acc.get(t, 0) + 1
    summary = {
        "total": len(records),
        "accepted": sum(1 for r in records if r["verdict"] == "accepted"),
        "rejected": sum(1 for r in records if r["verdict"] == "rejected"),
        "by_reason": by_reason,
        "accepted_by_topic": dict(sorted(by_topic_acc.items(), key=lambda kv: -kv[1])),
        "spdx_accepted_list": accepted,
    }
    with open(os.path.join(out_dir, "_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    print(f"\n== FASE 2a COMPLETA ==")
    print(f"   aceptados: {summary['accepted']}/{summary['total']}  ·  {out_path}")


if __name__ == "__main__":
    main()
