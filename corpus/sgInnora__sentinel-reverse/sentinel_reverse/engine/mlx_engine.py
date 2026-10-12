# -*- coding: utf-8 -*-
"""
MLX Reverse Engineering Engine
===============================

Local AI-powered binary reverse analysis engine built on Apple's MLX framework.
Leverages MPS GPU acceleration for zero-cost, privacy-preserving
AI-driven decompilation and reverse engineering.

References:
- LLM4Decompile (Microsoft) - LLM decompilation architecture
- DeGPT - GPT-driven decompiler
- MLX (Apple) - Apple Silicon native ML framework
- mlx-lm (Apple) - MLX LLM inference library

Hardware Requirements:
- Apple Silicon (M1/M2/M3/M4) + Unified Memory >= 32GB
- Metal 3 GPU recommended
"""

import os
import json
import time
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisTask(str, Enum):
    """Reverse analysis task types."""
    DECOMPILE = "decompile"
    FUNCTION_NAME = "function_name"
    VULNERABILITY = "vulnerability"
    ALGORITHM_DETECT = "algorithm_detect"
    OBFUSCATION_RESTORE = "obfuscation_restore"
    TYPE_INFERENCE = "type_inference"
    CONTROL_FLOW = "control_flow"
    DATA_FLOW = "data_flow"


@dataclass
class ReverseResult:
    """Reverse analysis result."""
    task: AnalysisTask
    confidence: float
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    inference_time_ms: float = 0.0
    token_count: int = 0
    round_num: int = 1


@dataclass
class FunctionContext:
    """Function context for iterative analysis."""
    address: int
    name: str
    assembly: str
    size: int
    call_refs: List[int] = field(default_factory=list)
    data_refs: List[int] = field(default_factory=list)
    decompiled: Optional[str] = None
    predicted_name: Optional[str] = None
    complexity: int = 0
    arch: str = "x86_64"


# Task-specific prompt templates
# Inspired by LLM4Decompile prompt engineering strategy
REVERSE_PROMPTS = {
    AnalysisTask.DECOMPILE: """You are an expert binary reverse engineer specializing in decompilation.
Given the following {arch} assembly code from function at address {address}:

```asm
{assembly}
```

{context}

Decompile this assembly into clean, readable C/C++ source code.
Rules:
1. Infer meaningful variable names from register usage patterns
2. Restore control flow structures (if/else, while, for, switch)
3. Identify standard library calls and use proper function signatures
4. Add brief comments for complex logic
5. Output ONLY the C/C++ code, no explanations

```c
""",

    AnalysisTask.FUNCTION_NAME: """You are a binary analysis expert specializing in function identification.
Given the following {arch} assembly code:

```asm
{assembly}
```

Call references: {call_refs}
Data references: {data_refs}

Predict the most likely function name and purpose.
Output JSON:
{{"name": "predicted_function_name", "purpose": "brief description", "category": "crypto|network|file_io|memory|string|math|init|cleanup|handler|unknown", "confidence": 0.0-1.0}}
""",

    AnalysisTask.VULNERABILITY: """You are a senior vulnerability researcher.
Analyze the following {arch} assembly/decompiled code for security vulnerabilities:

```
{assembly}
```

{context}

Identify ALL potential vulnerabilities. For each, provide:
- Vulnerability type (CWE ID)
- Severity (Critical/High/Medium/Low)
- Location (instruction offset or line)
- Exploitation difficulty
- Recommended fix

Output JSON array:
[{{"cwe": "CWE-xxx", "severity": "High", "location": "0x...", "description": "...", "exploit_difficulty": "Easy|Medium|Hard", "fix": "..."}}]
""",

    AnalysisTask.ALGORITHM_DETECT: """You are a cryptography and algorithm expert.
Analyze the following {arch} assembly code to identify implemented algorithms:

```asm
{assembly}
```

Identify:
1. Cryptographic algorithms (AES, RSA, SHA, MD5, RC4, etc.)
2. Compression algorithms (zlib, lz4, lzma, etc.)
3. Encoding schemes (Base64, XOR, custom)
4. Standard data structures and algorithms

Output JSON:
[{{"algorithm": "name", "type": "crypto|compression|encoding|data_structure", "confidence": 0.0-1.0, "evidence": "brief explanation", "key_constants": ["0x..."]}}]
""",

    AnalysisTask.OBFUSCATION_RESTORE: """You are an expert in code deobfuscation and malware analysis.
The following {arch} assembly appears to be obfuscated:

```asm
{assembly}
```

{context}

Identify obfuscation techniques used and restore the original logic:
1. Control flow flattening -> restore original structure
2. Dead code insertion -> identify and remove
3. String encryption -> decrypt if possible
4. API hashing -> resolve hash to API name
5. Opaque predicates -> simplify

Output the deobfuscated logic as pseudocode with annotations.
""",

    AnalysisTask.TYPE_INFERENCE: """You are a type system expert analyzing binary code.
Given the following {arch} assembly with register/memory access patterns:

```asm
{assembly}
```

Infer types for all variables and parameters:
1. Function signature (return type, parameter types)
2. Local variable types
3. Struct/class field layouts
4. Pointer types and levels of indirection

Output JSON:
{{"signature": "return_type func(param1_type, ...)", "locals": {{"var_name": "type"}}, "structs": [{{"name": "...", "fields": [{{"offset": 0, "type": "...", "name": "..."}}]}}]}}
""",
}


class MLXReverseEngine:
    """
    MLX Local Reverse Analysis Engine

    Leverages Apple Silicon unified memory architecture and Metal GPU
    acceleration to run large language models locally for binary
    reverse engineering.

    Features:
    - Zero API cost (fully local inference)
    - Data privacy (binaries never leave the device)
    - MPS GPU acceleration
    - 6 reverse analysis task types
    - LRU semantic cache to reduce redundant inference
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        cache_size: int = 1000,
    ):
        self.model_path = model_path or self._find_default_model()
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._model = None
        self._tokenizer = None
        self._loaded = False

        # LRU semantic cache (assembly_hash -> result)
        self._cache: Dict[str, ReverseResult] = {}
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_inferences = 0
        self._total_tokens = 0

    @staticmethod
    def _find_default_model() -> str:
        """Search common paths for a local MLX model."""
        search_paths = [
            "~/models",
            "~/mlx-models",
            "~/.cache/huggingface/hub",
            "/opt/models",
        ]
        for base in search_paths:
            base = os.path.expanduser(base)
            if not os.path.isdir(base):
                continue
            for entry in os.listdir(base):
                model_dir = os.path.join(base, entry)
                if os.path.isdir(model_dir):
                    has_weights = any(
                        f.endswith(".safetensors")
                        for f in os.listdir(model_dir)
                    )
                    has_config = os.path.exists(
                        os.path.join(model_dir, "config.json")
                    )
                    if has_weights and has_config:
                        return model_dir
        return os.path.expanduser("~/models/default-mlx-model")

    @property
    def is_available(self) -> bool:
        """Check if MLX environment is available."""
        try:
            import mlx.core as mx
            return mx.default_device().type == "gpu"
        except ImportError:
            return False

    def load_model(self) -> bool:
        """Load MLX model into GPU memory."""
        if self._loaded:
            return True

        try:
            from mlx_lm import load
            logger.info(f"Loading MLX model: {self.model_path}")
            start = time.time()
            self._model, self._tokenizer = load(self.model_path)
            elapsed = time.time() - start
            self._loaded = True
            logger.info(f"MLX model loaded in {elapsed:.1f}s, GPU memory allocated")
            return True
        except Exception as e:
            logger.error(f"Failed to load MLX model: {e}")
            return False

    def unload_model(self):
        """Release model memory, explicitly clean GPU resources."""
        self._model = None
        self._tokenizer = None
        self._loaded = False
        try:
            import mlx.core as mx
            mx.clear_memory_cache()
        except Exception:
            pass
        import gc
        gc.collect()
        logger.info("MLX model unloaded, GPU memory released")

    def analyze(
        self,
        func_ctx: FunctionContext,
        task: AnalysisTask = AnalysisTask.DECOMPILE,
        extra_context: str = "",
    ) -> ReverseResult:
        """
        Execute a single reverse analysis.

        Args:
            func_ctx: Function context (assembly code, address, refs, etc.)
            task: Analysis task type
            extra_context: Additional context (e.g., previous round results)

        Returns:
            ReverseResult
        """
        # Check cache
        cache_key = self._make_cache_key(func_ctx, task, extra_context)
        if cache_key in self._cache:
            self._cache_hits += 1
            cached = self._cache[cache_key]
            logger.debug(f"Cache hit for {func_ctx.address:#x} task={task.value}")
            return cached

        self._cache_misses += 1

        if not self._loaded:
            if not self.load_model():
                return ReverseResult(
                    task=task, confidence=0.0,
                    output="ERROR: MLX model not available",
                    metadata={"error": "model_not_loaded"},
                )

        # Build prompt
        prompt = self._build_prompt(func_ctx, task, extra_context)

        # Execute inference
        start = time.time()
        output_text, token_count = self._generate(prompt)
        elapsed_ms = (time.time() - start) * 1000

        self._total_inferences += 1
        self._total_tokens += token_count

        # Build result
        result = ReverseResult(
            task=task,
            confidence=self._estimate_confidence(output_text, task),
            output=self._clean_output(output_text, task),
            metadata={
                "address": func_ctx.address,
                "arch": func_ctx.arch,
                "model": Path(self.model_path).name,
            },
            inference_time_ms=elapsed_ms,
            token_count=token_count,
        )

        # Update cache
        self._update_cache(cache_key, result)

        logger.info(
            f"MLX analysis: addr={func_ctx.address:#x} task={task.value} "
            f"confidence={result.confidence:.2f} time={elapsed_ms:.0f}ms "
            f"tokens={token_count}"
        )
        return result

    def batch_analyze(
        self,
        functions: List[FunctionContext],
        task: AnalysisTask = AnalysisTask.DECOMPILE,
    ) -> List[ReverseResult]:
        """Batch analyze multiple functions."""
        results = []
        for func in functions:
            result = self.analyze(func, task)
            results.append(result)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(total_requests, 1)
        return {
            "model": Path(self.model_path).name,
            "loaded": self._loaded,
            "total_inferences": self._total_inferences,
            "total_tokens": self._total_tokens,
            "cache_size": len(self._cache),
            "cache_hit_rate": round(hit_rate, 3),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
        }

    # ---- Internal methods ----

    def _build_prompt(
        self, func_ctx: FunctionContext, task: AnalysisTask, extra_context: str
    ) -> str:
        """Build task prompt."""
        template = REVERSE_PROMPTS.get(task, REVERSE_PROMPTS[AnalysisTask.DECOMPILE])

        context_str = ""
        if extra_context:
            context_str = f"Previous analysis context:\n{extra_context}\n"
        if func_ctx.decompiled:
            context_str += f"Previous decompilation attempt:\n```c\n{func_ctx.decompiled}\n```\n"
        if func_ctx.predicted_name:
            context_str += f"Predicted function name: {func_ctx.predicted_name}\n"

        prompt_body = template.format(
            arch=func_ctx.arch,
            address=f"{func_ctx.address:#x}",
            assembly=func_ctx.assembly[:8000],
            context=context_str,
            call_refs=func_ctx.call_refs[:20],
            data_refs=func_ctx.data_refs[:20],
        )

        # Chat format (compatible with most instruction-tuned models)
        return (
            f"<|im_start|>system\n"
            f"You are an expert binary reverse engineer with 20 years of experience. "
            f"You specialize in x86, ARM, and MIPS architectures. "
            f"Always provide precise, production-quality output.<|im_end|>\n"
            f"<|im_start|>user\n{prompt_body}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def _generate(self, prompt: str) -> Tuple[str, int]:
        """
        Execute MLX inference.

        Uses stream_generate for precise parameter control.
        Note: mlx_lm generate_step() accepts `sampler`, not `temp`.
        """
        import traceback
        import mlx.core as mx
        from mlx_lm.generate import stream_generate
        from mlx_lm.sample_utils import make_sampler
        from mlx_lm.tokenizer_utils import TokenizerWrapper

        sampler = make_sampler(temp=self.temperature)

        try:
            text = ""
            gen_tokens = 0
            for response in stream_generate(
                self._model,
                self._tokenizer,
                prompt,
                max_tokens=self.max_tokens,
                sampler=sampler,
            ):
                text += response.text
                gen_tokens = response.generation_tokens

            token_count = gen_tokens if gen_tokens > 0 else int(len(text.split()) * 1.3)
            return text, token_count

        except TypeError as e:
            tb = traceback.format_exc()
            logger.error(f"MLX generate TypeError: {e}\n{tb}")

            # Fallback: direct generate_step call
            logger.info("Falling back to direct generate_step call...")
            try:
                from mlx_lm.generate import generate_step

                tokenizer = self._tokenizer
                if not isinstance(tokenizer, TokenizerWrapper):
                    tokenizer = TokenizerWrapper(tokenizer)

                add_special = tokenizer.bos_token is None or not prompt.startswith(
                    tokenizer.bos_token or ""
                )
                prompt_tokens = mx.array(
                    tokenizer.encode(prompt, add_special_tokens=add_special)
                )
                detokenizer = tokenizer.detokenizer

                text = ""
                for n, (token, _logprobs) in enumerate(
                    generate_step(
                        prompt_tokens,
                        self._model,
                        max_tokens=self.max_tokens,
                        sampler=sampler,
                    )
                ):
                    if token.item() in tokenizer.eos_token_ids:
                        break
                    detokenizer.add_token(token.item())
                    if (n + 1) >= self.max_tokens:
                        break

                detokenizer.finalize()
                text = str(detokenizer)
                return text, n + 1

            except Exception as e2:
                logger.error(f"Fallback generate_step also failed: {e2}\n{traceback.format_exc()}")
                raise

        except Exception as e:
            logger.error(f"MLX generate failed: {e}\n{traceback.format_exc()}")
            raise

    def _estimate_confidence(self, output: str, task: AnalysisTask) -> float:
        """Heuristic confidence estimation."""
        if not output or len(output.strip()) < 10:
            return 0.0

        confidence = 0.5

        if task in (
            AnalysisTask.FUNCTION_NAME,
            AnalysisTask.VULNERABILITY,
            AnalysisTask.ALGORITHM_DETECT,
            AnalysisTask.TYPE_INFERENCE,
        ):
            try:
                json.loads(output.strip())
                confidence += 0.3
            except json.JSONDecodeError:
                confidence -= 0.2

        if task == AnalysisTask.DECOMPILE:
            code_indicators = ["{", "}", "return", "(", ")", ";"]
            matched = sum(1 for ind in code_indicators if ind in output)
            confidence += min(matched * 0.05, 0.3)

        if 50 < len(output) < 10000:
            confidence += 0.1
        elif len(output) < 20:
            confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _clean_output(self, output: str, task: AnalysisTask) -> str:
        """Clean model output."""
        text = output.strip()
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()

        if task in (
            AnalysisTask.FUNCTION_NAME,
            AnalysisTask.VULNERABILITY,
            AnalysisTask.ALGORITHM_DETECT,
            AnalysisTask.TYPE_INFERENCE,
        ):
            start = text.find("{") if "{" in text else text.find("[")
            end = text.rfind("}") + 1 if "}" in text else text.rfind("]") + 1
            if start != -1 and end > start:
                text = text[start:end]

        return text

    def _make_cache_key(
        self, func_ctx: FunctionContext, task: AnalysisTask, extra_context: str
    ) -> str:
        """Generate cache key."""
        content = f"{func_ctx.address}:{task.value}:{func_ctx.assembly[:500]}:{extra_context[:200]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _update_cache(self, key: str, result: ReverseResult):
        """Update LRU cache."""
        if len(self._cache) >= self._cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = result
