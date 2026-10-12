# -*- coding: utf-8 -*-
"""
Multi-Model Voting System for Binary Analysis
===============================================

Multi-model parallel decompilation voting system combining local MLX
and cloud API inference.

Core Mechanisms:
- Multi-model parallel inference (local MLX + cloud APIs)
- 2/3 consistency voting decisions
- Confidence-weighted fusion
- Cost-aware routing (prefer local models)

References:
- DeGPT (ai4code) - Multi-model strategy
- BinaryAI (Tencent) - Function-level similarity matching
- Anthropic Building Effective Agents - Evaluator-Optimizer Workflow
"""

import os
import json
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)


class VoteStrategy(str, Enum):
    """Voting strategy."""
    MAJORITY = "majority"
    WEIGHTED = "weighted_confidence"
    BEST_OF = "best_confidence"


@dataclass
class ModelResult:
    """Single model result."""
    model_name: str
    provider: str  # "mlx", "anthropic", "openai", "google"
    output: str
    confidence: float
    elapsed_ms: float
    cost_usd: float = 0.0
    error: Optional[str] = None


@dataclass
class VotingResult:
    """Voting result."""
    consensus_output: str
    consensus_confidence: float
    agreement_rate: float
    total_models: int
    agreeing_models: int
    strategy_used: VoteStrategy
    individual_results: List[ModelResult] = field(default_factory=list)
    total_elapsed_ms: float = 0.0
    total_cost_usd: float = 0.0


class ModelVoter:
    """
    Multi-Model Voting System

    Supports local MLX + cloud API hybrid inference with voting
    mechanisms to improve reverse analysis accuracy.

    Model Roles:
    - MLX (local): Primary inference, zero cost, data privacy
    - Cloud API 1: Logic reasoning enhancement
    - Cloud API 2: Code generation optimization
    - Cloud API 3: Context understanding, long function analysis

    Usage:
        voter = ModelVoter(mlx_engine=engine)
        result = await voter.vote(func_ctx, task="decompile")
    """

    def __init__(
        self,
        mlx_engine=None,
        enable_cloud: bool = False,
        vote_strategy: VoteStrategy = VoteStrategy.WEIGHTED,
        agreement_threshold: int = 2,
        timeout_seconds: float = 60.0,
    ):
        self.mlx_engine = mlx_engine
        self.enable_cloud = enable_cloud
        self.vote_strategy = vote_strategy
        self.agreement_threshold = agreement_threshold
        self.timeout = timeout_seconds

        self._cloud_clients = {}
        self._total_votes = 0
        self._agreement_history: List[float] = []

    async def vote(
        self,
        prompt: str,
        task_type: str = "decompile",
        models: Optional[List[str]] = None,
    ) -> VotingResult:
        """
        Execute multi-model voting.

        Args:
            prompt: Analysis prompt
            task_type: Task type
            models: Specific model list (auto-select if None)

        Returns:
            VotingResult
        """
        start_time = time.time()

        active_models = models or self._select_models(task_type)

        tasks = []
        for model_name in active_models:
            tasks.append(self._query_model(model_name, prompt, task_type))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: List[ModelResult] = []
        for model_name, result in zip(active_models, results):
            if isinstance(result, Exception):
                logger.warning(f"Model {model_name} failed: {result}")
                valid_results.append(ModelResult(
                    model_name=model_name, provider="error",
                    output="", confidence=0.0, elapsed_ms=0.0,
                    error=str(result),
                ))
            else:
                valid_results.append(result)

        voting_result = self._execute_vote(valid_results)
        voting_result.total_elapsed_ms = (time.time() - start_time) * 1000
        voting_result.total_cost_usd = sum(r.cost_usd for r in valid_results)

        self._total_votes += 1
        self._agreement_history.append(voting_result.agreement_rate)

        logger.info(
            f"Vote complete: agreement={voting_result.agreement_rate:.2f} "
            f"models={voting_result.total_models} "
            f"strategy={voting_result.strategy_used.value} "
            f"time={voting_result.total_elapsed_ms:.0f}ms "
            f"cost=${voting_result.total_cost_usd:.4f}"
        )
        return voting_result

    def get_stats(self) -> Dict[str, Any]:
        """Return voting statistics."""
        avg_agreement = (
            sum(self._agreement_history) / len(self._agreement_history)
            if self._agreement_history else 0.0
        )
        return {
            "total_votes": self._total_votes,
            "average_agreement_rate": round(avg_agreement, 3),
            "cloud_enabled": self.enable_cloud,
            "vote_strategy": self.vote_strategy.value,
        }

    # ---- Internal methods ----

    def _select_models(self, task_type: str) -> List[str]:
        """Select models based on task type."""
        models = ["mlx_local"]

        if self.enable_cloud:
            if task_type in ("decompile", "obfuscation"):
                models.extend(["cloud_reasoning", "cloud_codegen"])
            elif task_type == "vulnerability":
                models.extend(["cloud_reasoning", "cloud_context"])
            else:
                models.append("cloud_reasoning")

        return models

    async def _query_model(
        self, model_name: str, prompt: str, task_type: str
    ) -> ModelResult:
        """Query a single model."""
        start = time.time()

        try:
            if model_name == "mlx_local":
                return await self._query_mlx(prompt, start)
            elif model_name.startswith("cloud_"):
                return await self._query_cloud(model_name, prompt, start)
            else:
                raise ValueError(f"Unknown model: {model_name}")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ModelResult(
                model_name=model_name, provider="error",
                output="", confidence=0.0,
                elapsed_ms=elapsed, error=str(e),
            )

    async def _query_mlx(self, prompt: str, start: float) -> ModelResult:
        """Query local MLX model."""
        if not self.mlx_engine:
            raise RuntimeError("MLX engine not initialized")

        from sentinel_reverse.engine.mlx_engine import (
            FunctionContext, AnalysisTask,
        )
        func_ctx = FunctionContext(
            address=0, name="vote_target", assembly=prompt, size=0,
        )
        result = self.mlx_engine.analyze(func_ctx, AnalysisTask.DECOMPILE)
        elapsed = (time.time() - start) * 1000

        return ModelResult(
            model_name="mlx-local",
            provider="mlx",
            output=result.output,
            confidence=result.confidence,
            elapsed_ms=elapsed,
            cost_usd=0.0,
        )

    async def _query_cloud(self, model_name: str, prompt: str, start: float) -> ModelResult:
        """
        Query a cloud API model.

        Override this method to integrate your preferred cloud LLM providers.
        Example providers: Anthropic Claude, OpenAI GPT, Google Gemini, etc.
        """
        raise NotImplementedError(
            f"Cloud model '{model_name}' not configured. "
            f"Override _query_cloud() or set ANTHROPIC_API_KEY / OPENAI_API_KEY "
            f"environment variables and implement the cloud query logic."
        )

    def _execute_vote(self, results: List[ModelResult]) -> VotingResult:
        """Execute voting decision."""
        valid = [r for r in results if r.error is None and r.output.strip()]

        if not valid:
            return VotingResult(
                consensus_output="",
                consensus_confidence=0.0,
                agreement_rate=0.0,
                total_models=len(results),
                agreeing_models=0,
                strategy_used=self.vote_strategy,
                individual_results=results,
            )

        if self.vote_strategy == VoteStrategy.BEST_OF:
            best = max(valid, key=lambda r: r.confidence)
            return VotingResult(
                consensus_output=best.output,
                consensus_confidence=best.confidence,
                agreement_rate=1.0 / len(valid),
                total_models=len(results),
                agreeing_models=1,
                strategy_used=self.vote_strategy,
                individual_results=results,
            )

        if self.vote_strategy == VoteStrategy.WEIGHTED:
            return self._weighted_vote(valid, results)

        return self._majority_vote(valid, results)

    def _weighted_vote(
        self, valid: List[ModelResult], all_results: List[ModelResult]
    ) -> VotingResult:
        """Confidence-weighted voting."""
        sorted_results = sorted(valid, key=lambda r: r.confidence, reverse=True)
        best = sorted_results[0]

        agreeing = 1
        for r in sorted_results[1:]:
            if self._outputs_similar(best.output, r.output):
                agreeing += 1

        total_weight = sum(r.confidence for r in valid)
        weighted_confidence = sum(
            r.confidence * r.confidence for r in valid
        ) / max(total_weight, 0.01)

        return VotingResult(
            consensus_output=best.output,
            consensus_confidence=min(weighted_confidence, 1.0),
            agreement_rate=agreeing / len(valid),
            total_models=len(all_results),
            agreeing_models=agreeing,
            strategy_used=VoteStrategy.WEIGHTED,
            individual_results=all_results,
        )

    def _majority_vote(
        self, valid: List[ModelResult], all_results: List[ModelResult]
    ) -> VotingResult:
        """Majority voting."""
        groups: List[List[ModelResult]] = []
        for r in valid:
            placed = False
            for group in groups:
                if self._outputs_similar(r.output, group[0].output):
                    group.append(r)
                    placed = True
                    break
            if not placed:
                groups.append([r])

        largest_group = max(groups, key=len)
        best = max(largest_group, key=lambda r: r.confidence)

        return VotingResult(
            consensus_output=best.output,
            consensus_confidence=best.confidence,
            agreement_rate=len(largest_group) / len(valid),
            total_models=len(all_results),
            agreeing_models=len(largest_group),
            strategy_used=VoteStrategy.MAJORITY,
            individual_results=all_results,
        )

    def _outputs_similar(self, a: str, b: str, threshold: float = 0.6) -> bool:
        """Check if two outputs are similar (simplified Jaccard similarity)."""
        if not a or not b:
            return False
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return False
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return (intersection / union) >= threshold
