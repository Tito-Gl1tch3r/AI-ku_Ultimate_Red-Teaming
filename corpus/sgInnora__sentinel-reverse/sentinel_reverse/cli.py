#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sentinel-reverse: Autonomous AI-Powered Binary Reverse Engineering CLI
=======================================================================

Automatically detects binary format, loads MLX + MPS GPU,
and performs iterative reverse analysis on target binaries.

Usage:
    sentinel-reverse /path/to/binary
    sentinel-reverse /path/to/binary --mode exhaustive
    sentinel-reverse /path/to/binary --resume
    sentinel-reverse --list-models
"""

import gc
import os
import sys
import json
import time
import struct
import asyncio
import logging
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from sentinel_reverse.engine.mlx_engine import (
    MLXReverseEngine,
    FunctionContext,
    AnalysisTask,
    ReverseResult,
)
from sentinel_reverse.engine.mps_accelerator import MPSAccelerator
from sentinel_reverse.engine.iterative_analyzer import IterativeAnalyzer

__version__ = "1.0.0"

# ============================================================
# Binary Format Detection
# ============================================================
BINARY_FORMATS = {
    b"\x7fELF": "ELF",
    b"MZ": "PE",
    b"\xfe\xed\xfa\xce": "Mach-O (32-bit)",
    b"\xfe\xed\xfa\xcf": "Mach-O (64-bit)",
    b"\xce\xfa\xed\xfe": "Mach-O (32-bit LE)",
    b"\xcf\xfa\xed\xfe": "Mach-O (64-bit LE)",
    b"\xca\xfe\xba\xbe": "Mach-O (Universal)",
    b"PK": "ZIP/APK/JAR",
    b"dex\n": "DEX",
}


def detect_binary_format(filepath: str) -> dict:
    """Detect binary file format from magic bytes."""
    with open(filepath, "rb") as f:
        header = f.read(16)
        f.seek(0, 2)
        file_size = f.tell()

    fmt = "Unknown"
    for magic, name in BINARY_FORMATS.items():
        if header[: len(magic)] == magic:
            fmt = name
            break

    # APK detection
    is_apk = False
    if fmt == "ZIP/APK/JAR":
        ext = Path(filepath).suffix.lower()
        if ext == ".apk":
            is_apk = True
            fmt = "APK (Android)"
        elif ext in (".jar", ".aar"):
            fmt = f"JAR ({ext})"

    # PE sub-classification
    is_dotnet = False
    if fmt == "PE" and len(header) >= 4:
        with open(filepath, "rb") as f:
            f.seek(0x3C)
            pe_off_bytes = f.read(4)
            if len(pe_off_bytes) == 4:
                pe_off = struct.unpack("<I", pe_off_bytes)[0]
                f.seek(pe_off)
                pe_sig = f.read(4)
                if pe_sig == b"PE\x00\x00":
                    f.seek(pe_off + 4 + 20)
                    oh_magic = f.read(2)
                    if oh_magic == b"\x0b\x02":
                        fmt = "PE32+ (64-bit)"
                    elif oh_magic == b"\x0b\x01":
                        fmt = "PE32 (32-bit)"

    # Architecture inference
    arch = "unknown"
    if "64-bit" in fmt or "PE32+" in fmt:
        arch = "x86_64"
    elif "32-bit" in fmt or "PE32" in fmt:
        arch = "x86"
    elif "Mach-O" in fmt:
        arch = "arm64" if "64" in fmt else "arm"
    elif fmt == "ELF":
        if len(header) > 4 and header[4] == 2:
            arch = "x86_64"
        else:
            arch = "x86"

    return {
        "format": fmt,
        "arch": arch,
        "size": file_size,
        "size_mb": round(file_size / 1024 / 1024, 2),
        "is_apk": is_apk,
        "is_dotnet": is_dotnet,
        "extension": Path(filepath).suffix.lower(),
        "filename": Path(filepath).name,
    }


# ============================================================
# Analysis Mode Definitions
# ============================================================
ANALYSIS_MODES = {
    "quick": {
        "description": "Quick scan - decompile + function naming only",
        "confidence_threshold": 0.70,
        "max_rounds": 2,
        "max_functions": 50,
        "temperature": 0.1,
        "max_tokens": 2048,
    },
    "standard": {
        "description": "Standard analysis - decompile + vulnerability + algorithm detection",
        "confidence_threshold": 0.80,
        "max_rounds": 5,
        "max_functions": 200,
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "exhaustive": {
        "description": "Exhaustive analysis - full GPU-driven iterative reverse engineering",
        "confidence_threshold": 0.92,
        "max_rounds": 15,
        "max_functions": 9999,
        "temperature": 0.15,
        "max_tokens": 8192,
    },
    "security": {
        "description": "Security audit - focused on vulnerabilities and crypto algorithms",
        "confidence_threshold": 0.85,
        "max_rounds": 8,
        "max_functions": 500,
        "temperature": 0.2,
        "max_tokens": 4096,
    },
}

# ============================================================
# Model Discovery
# ============================================================
DEFAULT_MODEL_SEARCH_PATHS = [
    "~/models",
    "~/mlx-models",
    "~/.cache/huggingface/hub",
    "/opt/models",
]


def discover_models() -> list:
    """Search for locally available MLX models."""
    models = []
    for base in DEFAULT_MODEL_SEARCH_PATHS:
        base = os.path.expanduser(base)
        if not os.path.isdir(base):
            continue
        for entry in os.listdir(base):
            model_dir = os.path.join(base, entry)
            if os.path.isdir(model_dir):
                has_weights = any(
                    f.endswith(".safetensors") or f == "weights"
                    for f in os.listdir(model_dir)
                )
                has_config = os.path.exists(
                    os.path.join(model_dir, "config.json")
                )
                if has_weights and has_config:
                    try:
                        with open(
                            os.path.join(model_dir, "config.json")
                        ) as f:
                            cfg = json.load(f)
                        size_gb = sum(
                            os.path.getsize(os.path.join(model_dir, f))
                            for f in os.listdir(model_dir)
                            if f.endswith(".safetensors")
                        ) / (1024**3)
                        models.append(
                            {
                                "path": model_dir,
                                "name": entry,
                                "type": cfg.get("model_type", "unknown"),
                                "vocab_size": cfg.get("vocab_size", 0),
                                "hidden_size": cfg.get("hidden_size", 0),
                                "size_gb": round(size_gb, 1),
                            }
                        )
                    except Exception:
                        models.append(
                            {
                                "path": model_dir,
                                "name": entry,
                                "type": "unknown",
                                "size_gb": 0,
                            }
                        )
    return models


# ============================================================
# GPU Memory Management
# ============================================================
def release_mps_memory():
    """Release PyTorch MPS GPU memory."""
    try:
        import torch

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            torch.mps.synchronize()
    except Exception:
        pass
    gc.collect()


def release_mlx_memory():
    """Release MLX GPU memory."""
    try:
        import mlx.core as mx

        mx.clear_memory_cache()
    except Exception:
        pass
    gc.collect()


# ============================================================
# Checkpoint Manager
# ============================================================
class CheckpointManager:
    """Analysis checkpoint manager for interruption recovery."""

    def __init__(self, output_dir: str, target_name: str):
        self.checkpoint_file = os.path.join(
            output_dir, f".checkpoint_{target_name}.json"
        )

    def save(self, phase: int, data: dict):
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        payload = {
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

    def load(self) -> Optional[dict]:
        if not os.path.exists(self.checkpoint_file):
            return None
        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def clear(self):
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)

    @property
    def exists(self) -> bool:
        return os.path.exists(self.checkpoint_file)


# ============================================================
# r2pipe Binary Extraction
# ============================================================
def extract_binary_info(binary_path: str, logger) -> dict:
    """Extract binary information using radare2."""
    import r2pipe

    logger.info(f"[Phase 1] r2pipe analysis: {binary_path}")
    r2 = r2pipe.open(binary_path, flags=["-2"])

    info = {}
    info["binary_info"] = r2.cmdj("iIj") or {}
    info["sections"] = r2.cmdj("iSj") or []
    info["imports"] = r2.cmdj("iij") or []
    info["exports"] = r2.cmdj("iEj") or []
    info["entry_points"] = r2.cmdj("iej") or []

    logger.info(
        f"  Sections: {len(info['sections'])}, "
        f"Imports: {len(info['imports'])}"
    )

    # Function analysis
    r2_analysis = "aaa" if os.path.getsize(binary_path) < 10_000_000 else "aa"
    logger.info(f"  Function analysis ({r2_analysis})...")
    r2.cmd(r2_analysis)
    functions_raw = r2.cmdj("aflj") or []
    logger.info(f"  Discovered {len(functions_raw)} functions")

    functions = []
    for func in functions_raw:
        fname = func.get("name", f"fcn_{len(functions)}")
        faddr = func.get("offset", 0)
        fsize = func.get("size", 0)
        if fsize < 4 or fsize > 100000:
            continue

        disasm = r2.cmd(f"pdf @ {faddr}") or ""
        if not disasm.strip():
            disasm = r2.cmd(f"pd {min(fsize // 2, 200)} @ {faddr}") or ""

        functions.append(
            {
                "name": fname,
                "address": faddr,
                "size": fsize,
                "nargs": func.get("nargs", 0),
                "nbbs": func.get("nbbs", 0),
                "cc": func.get("cc", 0),
                "disasm": disasm[:12000],
            }
        )

    info["functions"] = functions
    logger.info(f"  Valid functions: {len(functions)}")

    strings_raw = r2.cmdj("izj") or []
    info["strings"] = [
        {
            "vaddr": s.get("vaddr", 0),
            "string": s.get("string", ""),
            "section": s.get("section", ""),
        }
        for s in strings_raw
        if len(s.get("string", "")) > 3
    ]
    logger.info(f"  Strings: {len(info['strings'])}")

    r2.quit()
    return info


# ============================================================
# .NET Bundle Extraction
# ============================================================
def extract_dotnet_bundle(binary_path: str, logger) -> dict:
    """Extract .NET Single-File Bundle from PE overlay."""
    logger.info("[Phase 2] .NET Bundle detection...")
    data = open(binary_path, "rb").read()
    size = len(data)
    bundle_info = {"is_dotnet_bundle": False, "files": [], "configs": {}}

    for scan_offset in range(size - 2000, max(size - 50000, 0), -1):
        if scan_offset + 12 > size:
            continue
        major, minor = struct.unpack(
            "<II", data[scan_offset : scan_offset + 8]
        )
        if major in (6, 7, 8, 9) and minor == 0:
            num_files = struct.unpack(
                "<i", data[scan_offset + 8 : scan_offset + 12]
            )[0]
            if 5 < num_files < 300:
                str_start = scan_offset + 12
                if str_start >= size:
                    continue
                str_len = data[str_start]
                if str_len > 100:
                    continue
                try:
                    bundle_id = data[
                        str_start + 1 : str_start + 1 + str_len
                    ].decode("utf-8")
                except Exception:
                    continue
                if not bundle_id.isprintable() or len(bundle_id) < 5:
                    continue

                logger.info(
                    f"  Bundle: v{major}.{minor}, "
                    f"{num_files} files, ID={bundle_id}"
                )
                bundle_info["is_dotnet_bundle"] = True
                bundle_info["version"] = f"{major}.{minor}"
                bundle_info["bundle_id"] = bundle_id
                bundle_info["num_files"] = num_files

                pos = str_start + 1 + str_len
                type_names = {
                    0: "Unknown",
                    1: "Assembly",
                    2: "NativeBinary",
                    3: "DepsJson",
                    4: "RuntimeConfigJson",
                    5: "Symbols",
                }
                for _ in range(num_files):
                    if pos + 25 > size:
                        break
                    f_offset, f_size, f_compressed = struct.unpack(
                        "<QQQ", data[pos : pos + 24]
                    )
                    f_type = data[pos + 24]
                    pos += 25
                    name_len = data[pos]
                    pos += 1
                    if name_len & 0x80:
                        name_len = (name_len & 0x7F) | (data[pos] << 7)
                        pos += 1
                    f_name = data[pos : pos + name_len].decode(
                        "utf-8", errors="replace"
                    )
                    pos += name_len
                    entry = {
                        "name": f_name,
                        "offset": f_offset,
                        "size": f_size,
                        "compressed_size": f_compressed,
                        "type": type_names.get(f_type, f"Type{f_type}"),
                    }
                    bundle_info["files"].append(entry)
                    if (
                        f_type in (3, 4)
                        and f_size < 500000
                        and f_compressed == 0
                    ):
                        try:
                            content = data[
                                f_offset : f_offset + f_size
                            ].decode("utf-8")
                            bundle_info["configs"][f_name] = json.loads(
                                content
                            )
                        except Exception:
                            pass
                break

    logger.info(f"  Embedded files: {len(bundle_info['files'])}")
    return bundle_info


# ============================================================
# Report Generation
# ============================================================
def generate_report(
    binary_path: str,
    binary_fmt: dict,
    binary_info: dict,
    bundle_info: dict,
    clusters: list,
    analysis_results: list,
    predictions: list,
    engine_stats: dict,
    accel_stats: dict,
    analyzer_stats: dict,
    mode_config: dict,
) -> str:
    """Generate Markdown reverse analysis report."""
    bi = binary_info.get("binary_info", {})
    lines = [
        f"# {binary_fmt['filename']} — AI Reverse Analysis Report",
        f"",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Target**: `{binary_path}`",
        f"**Format**: {binary_fmt['format']} ({binary_fmt['arch']})",
        f"**Size**: {binary_fmt['size_mb']} MB",
        f"**Mode**: {mode_config.get('description', 'standard')}",
        f"**Engine**: sentinel-reverse v{__version__} (MLX + MPS GPU)",
        f"",
        f"## 1. Binary Overview",
        f"",
        f"| Property | Value |",
        f"|----------|-------|",
        f"| Architecture | {bi.get('arch', binary_fmt['arch'])} {bi.get('bits', '')}bit |",
        f"| Format | {bi.get('bintype', binary_fmt['format'])} |",
        f"| OS | {bi.get('os', 'N/A')} ({bi.get('subsys', '')}) |",
        f"| Compiled | {bi.get('compiled', 'N/A')} |",
        f"| NX | {bi.get('nx', False)} | Canary | {bi.get('canary', False)} |",
        f"| Functions | {len(binary_info.get('functions', []))} |",
        f"| Imports | {len(binary_info.get('imports', []))} |",
        f"| Strings | {len(binary_info.get('strings', []))} |",
        f"",
    ]

    # Sections
    sections = binary_info.get("sections", [])
    if sections:
        lines += [
            "### 1.1 Sections",
            "",
            "| Name | Address | Size | Permissions |",
            "|------|---------|------|-------------|",
        ]
        for s in sections:
            lines.append(
                f"| {s.get('name', '')} | 0x{s.get('vaddr', 0):x} "
                f"| {s.get('vsize', 0):,} | {s.get('perm', '')} |"
            )
        lines.append("")

    # Imports
    imports = binary_info.get("imports", [])
    if imports:
        lines += ["### 1.2 Key Imports", ""]
        groups = {}
        for imp in imports:
            lib = imp.get("libname", "unknown")
            groups.setdefault(lib, []).append(imp.get("name", ""))
        for lib, names in sorted(groups.items()):
            lines.append(
                f"**{lib}** ({len(names)}): "
                f"`{'`, `'.join(names[:15])}`"
            )
        lines.append("")

    # .NET Bundle
    if bundle_info.get("is_dotnet_bundle"):
        lines += [
            "## 2. .NET Bundle",
            "",
            f"- Version: {bundle_info.get('version', 'N/A')}",
            f"- ID: {bundle_info.get('bundle_id', 'N/A')}",
            f"- Files: {bundle_info.get('num_files', 0)}",
            "",
        ]
        for cfg_name, cfg_content in bundle_info.get("configs", {}).items():
            lines += [
                f"### `{cfg_name}`",
                "```json",
                json.dumps(cfg_content, indent=2)[:3000],
                "```",
                "",
            ]

    # MPS Embeddings
    lines += [
        "## 3. MPS GPU Embedding Analysis",
        "",
        f"- Device: {accel_stats.get('device', 'N/A')}",
        f"- Embedding dimension: {accel_stats.get('embedding_dim', 0)}",
        f"- Total embeddings: {accel_stats.get('total_embeddings', 0)}",
        f"- Clusters: {len(clusters)}",
        "",
    ]

    # Function name predictions
    if predictions:
        lines += [
            "### 3.1 Function Name Predictions",
            "",
            "| Original | Predicted | Category | Confidence |",
            "|----------|-----------|----------|------------|",
        ]
        for p in predictions[:50]:
            lines.append(
                f"| `{p['original_name']}` | `{p['predicted_name']}` "
                f"| {p['category']} | {p['confidence']} |"
            )
        lines.append("")

    # AI Analysis Results
    lines += ["## 4. AI Iterative Reverse Analysis", ""]
    successful = [r for r in analysis_results if "error" not in r]
    sorted_results = sorted(
        successful, key=lambda x: x.get("final_confidence", 0), reverse=True
    )

    for i, r in enumerate(sorted_results):
        lines += [
            f"### 4.{i + 1} `{r['function']}` @ {r['address']}",
            "",
            f"- Strategy: {r.get('strategy', 'N/A')} | "
            f"Rounds: {r['total_rounds']} | "
            f"Confidence: {r['final_confidence']}",
            f"- Stop: {r['stop_reason']} | "
            f"Tokens: {r.get('total_tokens', 0)} | "
            f"Time: {r.get('elapsed_sec', 0)}s",
            "",
        ]
        if r.get("rounds_detail"):
            lines += [
                "| Round | Task | Confidence | Delta | Time(ms) |",
                "|-------|------|------------|-------|----------|",
            ]
            for rd in r["rounds_detail"]:
                lines.append(
                    f"| {rd['round']} | {rd['task']} | "
                    f"{rd['confidence']} | {rd['delta']:+.4f} | "
                    f"{rd['elapsed_ms']} |"
                )
            lines.append("")
        if r.get("final_output"):
            lines += ["```", r["final_output"][:6000], "```", ""]

    # Errors
    errors = [r for r in analysis_results if "error" in r]
    if errors:
        lines += [f"### Analysis Failures ({len(errors)})", ""]
        for e in errors:
            lines.append(
                f"- `{e['function']}` @ {e['address']}: {e['error']}"
            )
        lines.append("")

    # Key strings
    strings = binary_info.get("strings", [])
    keywords = [
        "http", "key", "token", "pass", "secret", "api", "config",
        "error", "file", "load", "init", "debug", "cert", "url",
        "encrypt", "crypt", "dll", "runtime", "dotnet",
    ]
    interesting = [
        s
        for s in strings
        if len(s["string"]) > 5
        and any(kw in s["string"].lower() for kw in keywords)
    ]
    if interesting:
        lines += [
            f"## 5. Key Strings ({len(interesting)}/{len(strings)})",
            "",
        ]
        for s in interesting[:100]:
            lines.append(f"- `0x{s['vaddr']:x}`: `{s['string'][:120]}`")
        lines.append("")

    # Summary statistics
    avg_conf = sum(r.get("final_confidence", 0) for r in successful) / max(
        len(successful), 1
    )
    total_tokens = sum(r.get("total_tokens", 0) for r in successful)
    total_time = sum(r.get("elapsed_sec", 0) for r in successful)
    lines += [
        "## 6. Summary Statistics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Functions analyzed | {len(successful)} |",
        f"| Functions failed | {len(errors)} |",
        f"| Average confidence | {avg_conf:.4f} |",
        f"| Total tokens | {total_tokens:,} |",
        f"| Total time | {total_time:.1f}s |",
        "",
    ]

    return "\n".join(lines)


# ============================================================
# Core Analysis Pipeline
# ============================================================
class SentinelReverseEngine:
    """Autonomous reverse analysis engine."""

    def __init__(
        self,
        target: str,
        model_path: str,
        output_dir: str,
        mode: str = "standard",
        resume: bool = False,
    ):
        self.target = os.path.abspath(target)
        self.model_path = model_path
        self.output_dir = output_dir
        self.mode = mode
        self.mode_config = ANALYSIS_MODES.get(mode, ANALYSIS_MODES["standard"])
        self.resume = resume

        target_name = Path(target).stem
        self.checkpoint = CheckpointManager(output_dir, target_name)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = os.path.join(
            output_dir, f"{target_name}_reverse_{ts}.md"
        )
        self.json_file = self.report_file.replace(".md", ".json")

        self.logger = logging.getLogger("sentinel-reverse")

    async def run(self):
        """Execute the complete 5-phase analysis pipeline."""
        mc = self.mode_config
        self.logger.info("=" * 70)
        self.logger.info("  sentinel-reverse — AI Binary Reverse Engineering")
        self.logger.info(f"  Mode: {self.mode} — {mc['description']}")
        self.logger.info("=" * 70)
        self.logger.info(f"Target: {self.target}")
        self.logger.info(f"Model: {self.model_path}")
        self.logger.info(f"Output: {self.output_dir}")
        self.logger.info("")

        os.makedirs(self.output_dir, exist_ok=True)

        # Format detection
        binary_fmt = detect_binary_format(self.target)
        self.logger.info(
            f"[Detect] format={binary_fmt['format']}, "
            f"arch={binary_fmt['arch']}, "
            f"size={binary_fmt['size_mb']}MB"
        )

        # Checkpoint recovery
        checkpoint_data = {}
        resume_phase = 0
        if self.resume and self.checkpoint.exists:
            cp = self.checkpoint.load()
            if cp:
                resume_phase = cp.get("phase", 0)
                checkpoint_data = cp.get("data", {})
                self.logger.info(
                    f"[Resume] Resuming from Phase {resume_phase} "
                    f"({cp.get('timestamp', '')})"
                )

        total_start = time.time()

        # ── Phase 1: r2 extraction ──
        if resume_phase >= 2 and "binary_info" in checkpoint_data:
            self.logger.info("[Phase 1] Restored from checkpoint")
            binary_info = checkpoint_data["binary_info"]
        else:
            binary_info = extract_binary_info(self.target, self.logger)
            self.checkpoint.save(1, {"binary_info": binary_info})

        # ── Phase 2: Format-specific extraction ──
        bundle_info = {"is_dotnet_bundle": False, "files": [], "configs": {}}
        if resume_phase >= 3 and "bundle_info" in checkpoint_data:
            self.logger.info("[Phase 2] Restored from checkpoint")
            bundle_info = checkpoint_data["bundle_info"]
        else:
            if binary_fmt["format"].startswith("PE"):
                bundle_info = extract_dotnet_bundle(self.target, self.logger)
            else:
                self.logger.info(
                    "[Phase 2] Non-PE format, skipping .NET detection"
                )
            self.checkpoint.save(
                2,
                {"binary_info": binary_info, "bundle_info": bundle_info},
            )

        # ── Phase 3: MPS GPU embedding ──
        functions = binary_info.get("functions", [])
        if resume_phase >= 4 and "embeddings_clusters" in checkpoint_data:
            self.logger.info("[Phase 3] Restored from checkpoint")
            clusters = checkpoint_data["embeddings_clusters"]
            predictions = checkpoint_data.get("predictions", [])
            accel_stats = checkpoint_data.get("accel_stats", {})
        else:
            self.logger.info(
                f"\n[Phase 3] MPS GPU embedding "
                f"({len(functions)} functions)..."
            )
            accelerator = MPSAccelerator(embedding_dim=256)
            stats = accelerator.get_stats()
            self.logger.info(
                f"  Device: {stats['device']}, MPS: {stats['mps_available']}"
            )

            embeddings_list = []
            clusters = []
            if functions:
                batch = [(f["address"], f["disasm"]) for f in functions]
                embeddings_list = accelerator.batch_compute_embeddings(batch)
                self.logger.info(
                    f"  Embeddings: {len(embeddings_list)} (dim=256)"
                )

                for idx, emb in enumerate(embeddings_list):
                    matches = accelerator.find_similar_functions(
                        emb.embedding, embeddings_list,
                        top_k=5, threshold=0.85,
                    )
                    matches = [
                        m for m in matches
                        if m.target_address != emb.address
                    ]
                    if matches:
                        clusters.append(
                            {
                                "source": functions[idx]["name"],
                                "source_addr": functions[idx]["address"],
                                "similar": [
                                    {
                                        "addr": m.target_address,
                                        "score": round(
                                            m.similarity_score, 4
                                        ),
                                    }
                                    for m in matches
                                ],
                            }
                        )
                self.logger.info(f"  Similarity clusters: {len(clusters)}")

            # Function name prediction (MPS phase)
            predictions = []
            unnamed = [
                (i, f, embeddings_list[i])
                for i, f in enumerate(functions)
                if embeddings_list
                and (
                    f["name"].startswith("fcn.")
                    or f["name"].startswith("sub_")
                )
            ]
            if unnamed:
                self.logger.info(
                    f"[Phase 3b] Predicting {len(unnamed)} function names..."
                )
                for idx, func, emb in unnamed:
                    pred = accelerator.predict_function_name(
                        emb.embedding, address=func["address"]
                    )
                    predictions.append(
                        {
                            "original_name": func["name"],
                            "address": f"0x{func['address']:x}",
                            "predicted_name": pred.predicted_name,
                            "category": pred.category,
                            "confidence": round(pred.confidence, 4),
                        }
                    )
                self.logger.info(f"  Predictions: {len(predictions)}")

            accel_stats = accelerator.get_stats()
            self.checkpoint.save(
                3,
                {
                    "binary_info": binary_info,
                    "bundle_info": bundle_info,
                    "embeddings_clusters": clusters,
                    "predictions": predictions,
                    "accel_stats": accel_stats,
                },
            )

            # Release MPS GPU before loading MLX
            self.logger.info("\n  [GPU] Releasing MPS -> preparing MLX...")
            del accelerator
            embeddings_list = None
            release_mps_memory()
            self.logger.info("  [GPU] MPS released")

        # ── Phase 4: MLX AI iterative analysis ──
        resume_func_idx = 0
        existing_results = []
        if resume_phase >= 4 and "analysis_results" in checkpoint_data:
            existing_results = checkpoint_data["analysis_results"]
            resume_func_idx = checkpoint_data.get("completed_functions", 0)

        max_funcs = min(len(functions), mc["max_functions"])
        if resume_func_idx >= max_funcs:
            self.logger.info(
                f"[Phase 4] All {max_funcs} functions completed"
            )
            analysis_results = existing_results
            engine_stats = checkpoint_data.get("engine_stats", {})
            analyzer_stats = checkpoint_data.get("analyzer_stats", {})
        else:
            self.logger.info("\n[Phase 4] Loading MLX model...")
            engine = MLXReverseEngine(
                model_path=self.model_path,
                max_tokens=mc["max_tokens"],
                temperature=mc["temperature"],
                cache_size=500,
            )
            engine.load_model()

            analyzer = IterativeAnalyzer(
                engine=engine,
                confidence_threshold=mc["confidence_threshold"],
                max_rounds=mc["max_rounds"],
                min_improvement=0.01,
            )

            self.logger.info(
                f"[Phase 4] Analyzing {max_funcs} functions "
                f"(from #{resume_func_idx + 1})"
            )
            self.logger.info(
                f"  threshold={mc['confidence_threshold']}, "
                f"max_rounds={mc['max_rounds']}"
            )

            analysis_results = list(existing_results)
            for idx, func in enumerate(functions[:max_funcs]):
                if idx < resume_func_idx:
                    continue

                func_start = time.time()
                fname = func["name"]
                faddr = func["address"]

                self.logger.info(
                    f"\n  [{idx + 1}/{max_funcs}] {fname} "
                    f"@ 0x{faddr:x} ({func['size']}B, {func['nbbs']}bb)"
                )

                func_ctx = FunctionContext(
                    address=faddr,
                    name=fname,
                    assembly=func["disasm"],
                    size=func["size"],
                    arch=binary_fmt.get("arch", "x86_64"),
                )

                # Strategy selection
                cc = func.get("cc", 0)
                if self.mode == "security":
                    strategy = "security_audit"
                elif (
                    self.mode == "exhaustive"
                    or cc > 15
                    or func["size"] > 500
                ):
                    strategy = "full_reverse"
                elif any(
                    kw in fname.lower()
                    for kw in (
                        "crypt", "encrypt", "hash", "aes", "rsa",
                    )
                ):
                    strategy = "security_audit"
                else:
                    strategy = "quick_decompile"

                try:
                    result = await analyzer.analyze(
                        func_ctx, strategy=strategy
                    )
                    elapsed = time.time() - func_start

                    entry = {
                        "function": fname,
                        "address": f"0x{faddr:x}",
                        "size": func["size"],
                        "blocks": func["nbbs"],
                        "cyclomatic_complexity": cc,
                        "strategy": strategy,
                        "total_rounds": result.total_rounds,
                        "stop_reason": result.stop_reason.value,
                        "final_confidence": round(
                            result.final_confidence, 4
                        ),
                        "final_output": result.final_output,
                        "improvement_rate": round(
                            result.improvement_rate, 4
                        ),
                        "total_tokens": result.total_tokens,
                        "elapsed_sec": round(elapsed, 2),
                        "rounds_detail": [
                            {
                                "round": r.round_num,
                                "task": r.task.value,
                                "confidence": round(
                                    r.cumulative_confidence, 4
                                ),
                                "delta": round(r.delta_confidence, 4),
                                "elapsed_ms": round(r.elapsed_ms, 1),
                            }
                            for r in result.rounds
                        ],
                    }
                    analysis_results.append(entry)
                    self.logger.info(
                        f"    => {result.total_rounds} rounds, "
                        f"confidence={result.final_confidence:.3f}, "
                        f"stop={result.stop_reason.value}, "
                        f"{elapsed:.1f}s"
                    )
                except Exception as e:
                    self.logger.error(f"    => Failed: {e}")
                    analysis_results.append(
                        {
                            "function": fname,
                            "address": f"0x{faddr:x}",
                            "error": str(e),
                        }
                    )

                # Incremental checkpoint
                self.checkpoint.save(
                    4,
                    {
                        "completed_functions": idx + 1,
                        "analysis_results": analysis_results,
                    },
                )

            engine_stats = engine.get_stats()
            analyzer_stats = analyzer.get_stats()

            # Release MLX
            self.logger.info("\n  [GPU] Unloading MLX model...")
            engine.unload_model()
            release_mlx_memory()

        # ── Phase 5: Report generation ──
        self.logger.info(f"\n[Phase 5] Generating report...")

        report = generate_report(
            self.target,
            binary_fmt,
            binary_info,
            bundle_info,
            clusters,
            analysis_results,
            predictions,
            engine_stats,
            accel_stats,
            analyzer_stats,
            self.mode_config,
        )
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report)
        self.logger.info(f"  Markdown: {self.report_file}")

        # JSON output
        raw = {
            "meta": {
                "tool": "sentinel-reverse",
                "version": __version__,
                "mode": self.mode,
                "target": self.target,
                "format": binary_fmt,
                "timestamp": datetime.now().isoformat(),
            },
            "binary_info_summary": {
                "info": binary_info.get("binary_info", {}),
                "sections": binary_info.get("sections", []),
                "imports_count": len(binary_info.get("imports", [])),
                "functions_count": len(functions),
                "strings_count": len(binary_info.get("strings", [])),
            },
            "bundle_info": bundle_info,
            "analysis_results": analysis_results,
            "predictions": predictions,
            "clusters_count": len(clusters),
            "engine_stats": engine_stats,
            "accelerator_stats": accel_stats,
            "analyzer_stats": analyzer_stats,
        }
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False, default=str)
        self.logger.info(f"  JSON: {self.json_file}")

        self.checkpoint.clear()

        total_elapsed = time.time() - total_start
        self.logger.info(f"\n{'=' * 70}")
        self.logger.info(
            f"  Done! Elapsed: {total_elapsed:.1f}s "
            f"({total_elapsed / 60:.1f}min)"
        )
        self.logger.info(f"  Report: {self.report_file}")
        self.logger.info(f"{'=' * 70}")

        return self.report_file


# ============================================================
# CLI Entry Point
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-reverse",
        description=(
            "sentinel-reverse — Autonomous AI-Powered "
            "Binary Reverse Engineering CLI"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sentinel-reverse /path/to/binary                   # Standard analysis
  sentinel-reverse /path/to/binary -m exhaustive     # Exhaustive mode
  sentinel-reverse /path/to/binary -m security       # Security audit
  sentinel-reverse /path/to/binary --resume          # Resume from checkpoint
  sentinel-reverse --detect /path/to/binary          # Detect format only
  sentinel-reverse --list-models                     # List available models

Analysis Modes:
  quick       Quick scan      (2 rounds,  threshold 0.70)
  standard    Standard        (5 rounds,  threshold 0.80)  [default]
  exhaustive  Exhaustive      (15 rounds, threshold 0.92)
  security    Security audit  (8 rounds,  threshold 0.85)
        """,
    )

    parser.add_argument("target", nargs="?", help="Target binary file path")
    parser.add_argument(
        "-m",
        "--mode",
        choices=list(ANALYSIS_MODES.keys()),
        default="standard",
        help="Analysis mode (default: standard)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="MLX model path (auto-discovers if not set)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output directory (default: ./reverse_results)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume analysis from last checkpoint",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Detect binary format only (no analysis)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List locally available MLX models",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=None,
        help="Override confidence threshold",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="Override maximum iteration rounds",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=None,
        help="Override maximum functions to analyze",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Errors only"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sentinel-reverse {__version__}",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Log level
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("sentinel-reverse")

    # List models
    if args.list_models:
        models = discover_models()
        if not models:
            print("No local MLX models found.")
            print(f"Search paths: {', '.join(DEFAULT_MODEL_SEARCH_PATHS)}")
            sys.exit(1)
        print(f"\nLocal MLX Models ({len(models)}):\n")
        for m in models:
            size_str = (
                f"{m.get('size_gb', 0):.1f}GB" if m.get("size_gb") else "N/A"
            )
            print(f"  {m['name']}")
            print(f"    Path: {m['path']}")
            print(f"    Type: {m.get('type', 'unknown')} | Size: {size_str}")
            print()
        sys.exit(0)

    # Format detection only
    if args.detect:
        if not args.target:
            parser.error("--detect requires a target file")
        fmt = detect_binary_format(args.target)
        print(json.dumps(fmt, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Analysis
    if not args.target:
        parser.error("Please specify a target binary file")

    if not os.path.isfile(args.target):
        logger.error(f"File not found: {args.target}")
        sys.exit(1)

    # Model path (auto-discover)
    model_path = args.model
    if not model_path:
        models = discover_models()
        if models:
            model_path = models[0]["path"]
            logger.info(f"Auto-selected model: {model_path}")
        else:
            logger.error(
                "No MLX model found. Use --model to specify a path, "
                "or --list-models to check available models."
            )
            sys.exit(1)
    elif not os.path.isdir(model_path):
        logger.error(f"Model not found: {model_path}")
        sys.exit(1)

    # Output directory
    output_dir = args.output or os.path.join(os.getcwd(), "reverse_results")

    # Override parameters
    mode = args.mode
    if args.confidence is not None:
        ANALYSIS_MODES[mode]["confidence_threshold"] = args.confidence
    if args.max_rounds is not None:
        ANALYSIS_MODES[mode]["max_rounds"] = args.max_rounds
    if args.max_functions is not None:
        ANALYSIS_MODES[mode]["max_functions"] = args.max_functions

    # Launch analysis
    engine = SentinelReverseEngine(
        target=args.target,
        model_path=model_path,
        output_dir=output_dir,
        mode=mode,
        resume=args.resume,
    )

    try:
        report_file = asyncio.run(engine.run())
        print(f"\nAnalysis complete: {report_file}")
    except KeyboardInterrupt:
        logger.info(
            "\nUser interrupt. Checkpoint saved. Use --resume to continue."
        )
        sys.exit(130)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        logger.error(traceback.format_exc())
        logger.info("Checkpoint saved. Use --resume to continue.")
        sys.exit(1)


if __name__ == "__main__":
    main()
