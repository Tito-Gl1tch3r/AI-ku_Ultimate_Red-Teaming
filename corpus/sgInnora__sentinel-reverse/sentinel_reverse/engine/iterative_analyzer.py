# -*- coding: utf-8 -*-
"""
Iterative Binary Analyzer
===========================

Multi-round iterative reverse analysis framework.

Implements GPU-driven iterative binary analysis where each round's output
feeds into the next round as context, progressively deepening the
understanding of binary code.

References:
- ICSE 2025: "Iterative Program Analysis with LLMs"
- ACM CCS 2024: "LLM-Enhanced Deobfuscation" (91.2% accuracy)
- Anthropic: Context Engineering for AI Agents
- LangGraph: Durable Execution + Checkpointing

Iteration Strategy:
- Round 1: Structure discovery (disassembly, function detection)
- Round 2: Semantic analysis (variable naming, type inference)
- Round 3: Cross-function analysis (call graph, data flow, vuln chains)
- Round N: Adaptive deepening (confidence-driven stopping)
"""

import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from sentinel_reverse.engine.mlx_engine import (
    MLXReverseEngine,
    AnalysisTask,
    FunctionContext,
    ReverseResult,
)

logger = logging.getLogger(__name__)


class StopReason(str, Enum):
    """Iteration stop reasons."""
    CONFIDENCE_REACHED = "confidence_threshold_reached"
    MAX_ROUNDS = "max_rounds_exhausted"
    NO_IMPROVEMENT = "no_confidence_improvement"
    USER_ABORT = "user_abort"
    ERROR = "analysis_error"


@dataclass
class IterationRound:
    """Single iteration round record."""
    round_num: int
    task: AnalysisTask
    result: ReverseResult
    cumulative_confidence: float
    delta_confidence: float
    elapsed_ms: float


@dataclass
class IterativeResult:
    """Iterative analysis final result."""
    final_output: str
    final_confidence: float
    total_rounds: int
    stop_reason: StopReason
    rounds: List[IterationRound] = field(default_factory=list)
    function_context: Optional[FunctionContext] = None
    total_time_ms: float = 0.0
    total_tokens: int = 0

    @property
    def improvement_rate(self) -> float:
        """Confidence improvement rate relative to first round."""
        if not self.rounds:
            return 0.0
        first = self.rounds[0].cumulative_confidence
        if first <= 0:
            return 0.0
        return (self.final_confidence - first) / first


# Iteration strategies: task sequences per round
ITERATION_STRATEGIES = {
    "full_reverse": [
        # Round 1: basic structure discovery
        [AnalysisTask.FUNCTION_NAME, AnalysisTask.ALGORITHM_DETECT],
        # Round 2: deep decompilation (using Round 1 function names + algo info)
        [AnalysisTask.DECOMPILE, AnalysisTask.TYPE_INFERENCE],
        # Round 3: security analysis (using decompiled results)
        [AnalysisTask.VULNERABILITY],
        # Round 4+: refinement (deobfuscation, data flow, etc.)
        [AnalysisTask.OBFUSCATION_RESTORE],
    ],
    "quick_decompile": [
        [AnalysisTask.DECOMPILE],
        [AnalysisTask.FUNCTION_NAME, AnalysisTask.DECOMPILE],
    ],
    "security_audit": [
        [AnalysisTask.DECOMPILE, AnalysisTask.ALGORITHM_DETECT],
        [AnalysisTask.VULNERABILITY],
        [AnalysisTask.OBFUSCATION_RESTORE, AnalysisTask.VULNERABILITY],
    ],
    "algorithm_recovery": [
        [AnalysisTask.ALGORITHM_DETECT],
        [AnalysisTask.DECOMPILE],
        [AnalysisTask.OBFUSCATION_RESTORE],
    ],
}


class IterativeAnalyzer:
    """
    Multi-round iterative reverse analyzer.

    Core capabilities:
    1. GPU-driven iterative analysis - MPS/MLX acceleration per round
    2. Context accumulation - each round's result feeds the next
    3. Confidence-driven stopping - automatically decides when to stop
    4. Multi-strategy support - full_reverse/quick_decompile/security_audit
    5. Checkpoint recovery - supports interruption and resumption

    Usage:
        engine = MLXReverseEngine()
        analyzer = IterativeAnalyzer(engine)
        result = await analyzer.analyze(func_ctx, strategy="full_reverse")
    """

    def __init__(
        self,
        engine: MLXReverseEngine,
        confidence_threshold: float = 0.85,
        max_rounds: int = 10,
        min_improvement: float = 0.02,
        on_round_complete: Optional[Callable] = None,
    ):
        """
        Args:
            engine: MLX inference engine
            confidence_threshold: Stop threshold (stop when reached)
            max_rounds: Maximum iteration rounds (prevents infinite loops)
            min_improvement: Minimum improvement threshold (stop if below)
            on_round_complete: Callback after each round (for real-time notifications)
        """
        self.engine = engine
        self.confidence_threshold = confidence_threshold
        self.max_rounds = max_rounds
        self.min_improvement = min_improvement
        self.on_round_complete = on_round_complete

        self._total_analyses = 0
        self._avg_rounds = 0.0

    async def analyze(
        self,
        func_ctx: FunctionContext,
        strategy: str = "full_reverse",
        start_round: int = 0,
    ) -> IterativeResult:
        """
        Execute multi-round iterative analysis.

        Args:
            func_ctx: Function context
            strategy: Iteration strategy name
            start_round: Starting round (for resumption)

        Returns:
            IterativeResult
        """
        tasks_per_round = ITERATION_STRATEGIES.get(
            strategy, ITERATION_STRATEGIES["full_reverse"]
        )

        rounds: List[IterationRound] = []
        accumulated_context = ""
        prev_confidence = 0.0
        total_start = time.time()
        stop_reason = StopReason.MAX_ROUNDS

        for round_num in range(start_round, self.max_rounds):
            round_start = time.time()

            task_index = min(round_num, len(tasks_per_round) - 1)
            current_tasks = tasks_per_round[task_index]

            # Execute all tasks in this round
            round_results = []
            for task in current_tasks:
                result = self.engine.analyze(
                    func_ctx, task=task, extra_context=accumulated_context
                )
                round_results.append(result)
                self._update_context(func_ctx, result)

            # Calculate round confidence (weighted average)
            round_confidence = self._aggregate_confidence(round_results)
            delta = round_confidence - prev_confidence

            # Accumulate context (core: each round's result feeds the next)
            accumulated_context = self._build_accumulated_context(
                rounds, round_results
            )

            round_elapsed = (time.time() - round_start) * 1000
            iteration_round = IterationRound(
                round_num=round_num + 1,
                task=current_tasks[0],
                result=round_results[0],
                cumulative_confidence=round_confidence,
                delta_confidence=delta,
                elapsed_ms=round_elapsed,
            )
            rounds.append(iteration_round)

            logger.info(
                f"Round {round_num + 1}: confidence={round_confidence:.3f} "
                f"delta={delta:+.3f} time={round_elapsed:.0f}ms "
                f"tasks={[t.value for t in current_tasks]}"
            )

            if self.on_round_complete:
                try:
                    self.on_round_complete(iteration_round)
                except Exception as e:
                    logger.warning(f"Round callback error: {e}")

            # Stopping conditions
            if round_confidence >= self.confidence_threshold:
                stop_reason = StopReason.CONFIDENCE_REACHED
                logger.info(
                    f"Stopping: confidence {round_confidence:.3f} >= "
                    f"threshold {self.confidence_threshold}"
                )
                break

            if round_num > 0 and abs(delta) < self.min_improvement:
                stop_reason = StopReason.NO_IMPROVEMENT
                logger.info(
                    f"Stopping: improvement {delta:.4f} < "
                    f"minimum {self.min_improvement}"
                )
                break

            prev_confidence = round_confidence

        total_time = (time.time() - total_start) * 1000
        total_tokens = sum(r.result.token_count for r in rounds)

        final_output = self._get_best_output(rounds)
        final_confidence = rounds[-1].cumulative_confidence if rounds else 0.0

        self._total_analyses += 1
        self._avg_rounds = (
            (self._avg_rounds * (self._total_analyses - 1) + len(rounds))
            / self._total_analyses
        )

        result = IterativeResult(
            final_output=final_output,
            final_confidence=final_confidence,
            total_rounds=len(rounds),
            stop_reason=stop_reason,
            rounds=rounds,
            function_context=func_ctx,
            total_time_ms=total_time,
            total_tokens=total_tokens,
        )

        logger.info(
            f"Iterative analysis complete: rounds={len(rounds)} "
            f"confidence={final_confidence:.3f} "
            f"stop={stop_reason.value} time={total_time:.0f}ms"
        )
        return result

    async def analyze_binary(
        self,
        functions: List[FunctionContext],
        strategy: str = "full_reverse",
        max_concurrent: int = 1,
    ) -> List[IterativeResult]:
        """Analyze all functions in a binary."""
        results = []
        for func in functions:
            result = await self.analyze(func, strategy=strategy)
            results.append(result)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Return analysis statistics."""
        return {
            "total_analyses": self._total_analyses,
            "average_rounds": round(self._avg_rounds, 2),
            "confidence_threshold": self.confidence_threshold,
            "max_rounds": self.max_rounds,
            "engine_stats": self.engine.get_stats(),
        }

    # ---- Internal methods ----

    def _update_context(self, func_ctx: FunctionContext, result: ReverseResult):
        """Update function context based on analysis result."""
        if result.task == AnalysisTask.DECOMPILE and result.confidence > 0.5:
            func_ctx.decompiled = result.output

        if result.task == AnalysisTask.FUNCTION_NAME and result.confidence > 0.5:
            try:
                data = _safe_json_parse(result.output)
                if isinstance(data, dict) and "name" in data:
                    func_ctx.predicted_name = data["name"]
            except Exception:
                pass

    def _aggregate_confidence(self, results: List[ReverseResult]) -> float:
        """Aggregate confidence from multiple results with task-based weighting."""
        if not results:
            return 0.0
        weights = {
            AnalysisTask.DECOMPILE: 2.0,
            AnalysisTask.VULNERABILITY: 1.8,
            AnalysisTask.FUNCTION_NAME: 1.0,
            AnalysisTask.ALGORITHM_DETECT: 1.2,
            AnalysisTask.OBFUSCATION_RESTORE: 1.5,
            AnalysisTask.TYPE_INFERENCE: 1.0,
        }
        total_weight = sum(weights.get(r.task, 1.0) for r in results)
        weighted_sum = sum(
            r.confidence * weights.get(r.task, 1.0) for r in results
        )
        return weighted_sum / max(total_weight, 1.0)

    def _build_accumulated_context(
        self,
        previous_rounds: List[IterationRound],
        current_results: List[ReverseResult],
    ) -> str:
        """Build accumulated context for next round input."""
        parts = []

        recent_rounds = previous_rounds[-3:]
        for r in recent_rounds:
            if r.result.confidence > 0.4:
                parts.append(
                    f"[Round {r.round_num} - {r.task.value}] "
                    f"(confidence: {r.cumulative_confidence:.2f}):\n"
                    f"{r.result.output[:1000]}\n"
                )

        for result in current_results:
            if result.confidence > 0.3:
                parts.append(
                    f"[Current - {result.task.value}] "
                    f"(confidence: {result.confidence:.2f}):\n"
                    f"{result.output[:1500]}\n"
                )

        return "\n---\n".join(parts)[-6000:]

    def _get_best_output(self, rounds: List[IterationRound]) -> str:
        """Get best output (prefer decompilation results)."""
        for r in reversed(rounds):
            if r.task == AnalysisTask.DECOMPILE and r.result.confidence > 0.5:
                return r.result.output

        if rounds:
            best = max(rounds, key=lambda r: r.cumulative_confidence)
            return best.result.output

        return ""


def _safe_json_parse(text: str) -> Any:
    """Safe JSON parsing."""
    import json
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())
