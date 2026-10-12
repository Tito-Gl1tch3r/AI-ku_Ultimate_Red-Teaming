# -*- coding: utf-8 -*-
"""Tests for core engine components."""

import pytest
from unittest.mock import MagicMock, patch

from sentinel_reverse.engine.mlx_engine import (
    AnalysisTask,
    FunctionContext,
    ReverseResult,
    TASK_PROMPTS,
)
from sentinel_reverse.engine.model_voter import (
    ModelVoter,
    VoteStrategy,
    ModelResult,
    VotingResult,
)
from sentinel_reverse.engine.iterative_analyzer import (
    ITERATION_STRATEGIES,
    StopReason,
)


class TestAnalysisTask:
    """Test AnalysisTask enum."""

    def test_all_tasks_exist(self):
        assert AnalysisTask.DECOMPILE
        assert AnalysisTask.FUNCTION_NAME
        assert AnalysisTask.VULNERABILITY
        assert AnalysisTask.ALGORITHM_DETECT
        assert AnalysisTask.OBFUSCATION_RESTORE
        assert AnalysisTask.TYPE_INFERENCE

    def test_task_has_prompt(self):
        for task in AnalysisTask:
            assert task in TASK_PROMPTS, f"Missing prompt for {task}"


class TestFunctionContext:
    """Test FunctionContext dataclass."""

    def test_creation(self):
        ctx = FunctionContext(
            address=0x401000,
            name="main",
            assembly="push rbp\nmov rbp, rsp",
            size=100,
        )
        assert ctx.address == 0x401000
        assert ctx.name == "main"
        assert ctx.size == 100

    def test_optional_fields(self):
        ctx = FunctionContext(
            address=0, name="test", assembly="nop", size=1,
        )
        assert ctx.arch == ""
        assert ctx.decompiled == ""
        assert ctx.predicted_name == ""


class TestReverseResult:
    """Test ReverseResult dataclass."""

    def test_creation(self):
        result = ReverseResult(
            task=AnalysisTask.DECOMPILE,
            output="int main() { return 0; }",
            confidence=0.85,
            elapsed_ms=1500.0,
            token_count=200,
        )
        assert result.task == AnalysisTask.DECOMPILE
        assert result.confidence == 0.85
        assert result.token_count == 200


class TestModelVoter:
    """Test ModelVoter voting logic."""

    def test_init_defaults(self):
        voter = ModelVoter()
        assert voter.vote_strategy == VoteStrategy.WEIGHTED
        assert voter.enable_cloud is False

    def test_weighted_vote(self):
        voter = ModelVoter(vote_strategy=VoteStrategy.WEIGHTED)
        results = [
            ModelResult("m1", "mlx", "output A code", 0.9, 100.0),
            ModelResult("m2", "cloud", "output A code similar", 0.8, 200.0),
            ModelResult("m3", "cloud", "completely different", 0.5, 150.0),
        ]
        voting = voter._execute_vote(results)
        assert voting.consensus_output == "output A code"
        assert voting.total_models == 3

    def test_best_of_vote(self):
        voter = ModelVoter(vote_strategy=VoteStrategy.BEST_OF)
        results = [
            ModelResult("m1", "mlx", "low conf", 0.3, 100.0),
            ModelResult("m2", "cloud", "high conf", 0.95, 200.0),
        ]
        voting = voter._execute_vote(results)
        assert voting.consensus_output == "high conf"
        assert voting.consensus_confidence == 0.95

    def test_majority_vote(self):
        voter = ModelVoter(vote_strategy=VoteStrategy.MAJORITY)
        results = [
            ModelResult("m1", "mlx", "output A similar tokens", 0.8, 100.0),
            ModelResult("m2", "cloud", "output A similar tokens match", 0.7, 200.0),
            ModelResult("m3", "cloud", "completely different output", 0.6, 150.0),
        ]
        voting = voter._execute_vote(results)
        assert voting.strategy_used == VoteStrategy.MAJORITY

    def test_empty_results(self):
        voter = ModelVoter()
        results = [
            ModelResult("m1", "error", "", 0.0, 0.0, error="failed"),
        ]
        voting = voter._execute_vote(results)
        assert voting.consensus_output == ""
        assert voting.agreeing_models == 0

    def test_outputs_similar(self):
        voter = ModelVoter()
        assert voter._outputs_similar(
            "int main return zero",
            "int main return zero end",
        ) is True
        assert voter._outputs_similar("abc", "xyz def ghi") is False
        assert voter._outputs_similar("", "test") is False

    def test_stats(self):
        voter = ModelVoter()
        stats = voter.get_stats()
        assert "total_votes" in stats
        assert "vote_strategy" in stats


class TestIterationStrategies:
    """Test iteration strategy definitions."""

    def test_all_strategies_exist(self):
        assert "full_reverse" in ITERATION_STRATEGIES
        assert "quick_decompile" in ITERATION_STRATEGIES
        assert "security_audit" in ITERATION_STRATEGIES
        assert "algorithm_recovery" in ITERATION_STRATEGIES

    def test_strategies_have_tasks(self):
        for name, rounds in ITERATION_STRATEGIES.items():
            assert len(rounds) > 0, f"{name} has no rounds"
            for round_tasks in rounds:
                assert len(round_tasks) > 0, f"{name} has empty round"
                for task in round_tasks:
                    assert isinstance(task, AnalysisTask)

    def test_full_reverse_is_comprehensive(self):
        strategy = ITERATION_STRATEGIES["full_reverse"]
        assert len(strategy) >= 4
        # First round should include function naming
        tasks_flat = [t for round_tasks in strategy for t in round_tasks]
        assert AnalysisTask.FUNCTION_NAME in tasks_flat
        assert AnalysisTask.DECOMPILE in tasks_flat
        assert AnalysisTask.VULNERABILITY in tasks_flat

    def test_security_audit_has_vulnerability(self):
        strategy = ITERATION_STRATEGIES["security_audit"]
        tasks_flat = [t for round_tasks in strategy for t in round_tasks]
        assert AnalysisTask.VULNERABILITY in tasks_flat


class TestStopReason:
    """Test StopReason enum."""

    def test_all_reasons(self):
        assert StopReason.CONFIDENCE_REACHED
        assert StopReason.MAX_ROUNDS
        assert StopReason.NO_IMPROVEMENT
        assert StopReason.USER_ABORT
        assert StopReason.ERROR
