#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-ku · FASE 2f — Mantenimiento del corpus: purga de duplicados y reparación de atribución.

Acciones idempotentes dirigidas por el manifiesto de una tanda:

  --purge-duplicates  elimina de corpus/ los archivos con veredicto "duplicate"
                      (el manifiesto ya los marca; el corpus debe ser el conjunto limpio).

  --fix-attribution   para repos minados sin _UPSTREAM_LICENSE: re-clona --depth 1,
                      busca en la raíz archivos de la familia LICEN[CS]E/COPYING/NOTICE
                      (incluye variantes: LICENCE, LICENSE-MIT, LICENSE.APACHE...) y copia
                      el principal como _UPSTREAM_LICENSE (+ extras como _UPSTREAM_LICENSE__X).

Uso:
  python src/07_repair_attribution.py --label full-1 --purge-duplicates --fix-attribution
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import time

GH_URL = "https://github.com"
LIC_RE = re.compile(r"^(licen[cs]e|copying)([._-].*)?$", re.I)
NOTICE_RE = re.compile(r"^notice([._-].*)?$", re.I)


def gh_url(repo):
    t = os.environ.get("GITHUB_TOKEN", "")
    return f"https://x-access-token:{t}@github.com/{repo}.git" if t else f"{GH_URL}/{repo}.git"


def sanitize(text):
    t = os.environ.get("GITHUB_TOKEN", "")
    return text.replace(t, "***") if t else text


def safe_name(repo):
    return repo.replace("/", "__")


def attr_priority(name):
    n = name.lower()
    if n in ("license", "licence", "copying", "notice"):
        return 0
    if "mit" in n:
        return 1
    return 2


def copy_attribution(dest, repo_dir):
    """Copia los archivos de licencia/NOTICE de la raíz del clon. Devuelve dict con lo copiado."""
    copied = {"license": [], "notice": []}
    try:
        entries = os.listdir(dest)
    except OSError:
        return copied
    files = [f for f in entries if os.path.isfile(os.path.join(dest, f))]
    lics = sorted([f for f in files if LIC_RE.match(f)], key=lambda f: (attr_priority(f), f))
    notices = sorted([f for f in files if NOTICE_RE.match(f)], key=lambda f: (attr_priority(f), f))
    for i, f in enumerate(lics):
        dst = "_UPSTREAM_LICENSE" if i == 0 else "_UPSTREAM_LICENSE__" + re.sub(r"[^A-Za-z0-9]", "_", f)
        shutil.copy2(os.path.join(dest, f), os.path.join(repo_dir, dst))
        copied["license"].append(dst)
    for i, f in enumerate(notices):
        dst = "_UPSTREAM_NOTICE" if i == 0 else "_UPSTREAM_NOTICE__" + re.sub(r"[^A-Za-z0-9]", "_", f)
        shutil.copy2(os.path.join(dest, f), os.path.join(repo_dir, dst))
        copied["notice"].append(dst)
    return copied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--purge-duplicates", action="store_true")
    ap.add_argument("--fix-attribution", action="store_true")
    ap.add_argument("--max-runtime", type=float, default=0,
                    help="salir limpiamente tras N segundos (0 = sin límite)")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    corpus = os.path.join(root, "corpus")
    res = os.path.join(root, "results", args.label)
    ws = os.path.join(root, ".workspace", "repair")
    primary = os.path.join(res, "manifest.jsonl")
    import glob as _glob
    man_files = [primary] if os.path.exists(primary) else sorted(
        _glob.glob(os.path.join(res, "manifest.part-*.jsonl")))
    entries = []
    for mf in man_files:
        with open(mf, encoding="utf-8") as fh:
            for l in fh:
                if l.strip():
                    entries.append(json.loads(l))

    if args.purge_duplicates:
        removed = 0
        for e in entries:
            if e.get("verdict") != "duplicate":
                continue
            p = os.path.join(corpus, safe_name(e["repo"]), e["path"])
            if os.path.exists(p):
                os.remove(p)
                removed += 1
        # podar directorios vacíos hacia arriba
        for dirpath, dirnames, _ in os.walk(corpus, topdown=False):
            if os.path.basename(dirpath) in ("corpus",):
                continue
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
            except OSError:
                pass
        print(f"[purge] duplicados eliminados del corpus: {removed}")

    if args.fix_attribution:
        ck = json.load(open(os.path.join(res, "_mined.json"), encoding="utf-8"))
        att_path = os.path.join(res, "_attribution.json")
        attempts = {}
        if os.path.exists(att_path):
            attempts = json.load(open(att_path, encoding="utf-8"))
        targets = []
        for repo, r in sorted(ck.items()):
            if r.get("verdict") != "MINED" or repo in attempts:
                continue
            repo_dir = os.path.join(corpus, safe_name(repo))
            if not os.path.exists(repo_dir):
                continue
            if not os.path.exists(os.path.join(repo_dir, "_UPSTREAM_LICENSE")):
                targets.append(repo)
            elif (r.get("spdx") == "Apache-2.0"
                  and not os.path.exists(os.path.join(repo_dir, "_UPSTREAM_NOTICE"))):
                targets.append(repo)  # puede que upstream tenga NOTICE y 03 no lo copiara
        print(f"[attribution] repos a reparar: {len(targets)} (intentos previos: {len(attempts)})")

        fixed, still_missing, clone_fail = [], [], []
        os.makedirs(ws, exist_ok=True)
        t0 = time.time()
        for repo in targets:
            if args.max_runtime and (time.time() - t0) > args.max_runtime:
                print(f"[attribution] --max-runtime: {len(attempts)} intentos registrados. Reanudable.")
                break
            dest = os.path.join(ws, safe_name(repo))
            if os.path.exists(dest):
                shutil.rmtree(dest)
            env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
            try:
                subprocess.run(["git", "clone", "--depth", "1", "--single-branch", "--quiet",
                                gh_url(repo), dest], capture_output=True, text=True,
                               timeout=240, env=env, check=True)
            except subprocess.CalledProcessError as e:
                clone_fail.append((repo, sanitize((e.stderr or "")[-120:])))
                attempts[repo] = "clone_fail"
                continue
            except subprocess.TimeoutExpired:
                clone_fail.append((repo, "CLONE_TIMEOUT"))
                attempts[repo] = "clone_fail"
                continue
            copied = copy_attribution(dest, os.path.join(corpus, safe_name(repo)))
            if copied["license"]:
                fixed.append(repo)
                attempts[repo] = "fixed"
            else:
                still_missing.append(repo)
                attempts[repo] = "no_lic"
            shutil.rmtree(dest, ignore_errors=True)
            if len(attempts) % 10 == 0:
                json.dump(attempts, open(att_path, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(attempts, open(att_path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[attribution] reparados (LICENSE copiado): {len(fixed)}")
        print(f"[attribution] sin archivo de licencia en la raíz (revisión manual): {len(still_missing)}")
        if still_missing:
            print("   → " + ", ".join(still_missing[:20]))
        if clone_fail:
            print(f"[attribution] fallos de clonado: {len(clone_fail)}")
            for repo, err in clone_fail[:10]:
                print(f"   {repo}: {err}")


if __name__ == "__main__":
    main()
