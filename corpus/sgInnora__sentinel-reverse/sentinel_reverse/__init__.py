"""
sentinel-reverse — AI-Powered Autonomous Binary Reverse Engineering
====================================================================

The native AI reverse engineering engine extracted from Innora-Sentinel,
an enterprise security analysis platform by Innora AI (https://innora.ai).

This package provides:
- Local LLM inference via Apple MLX framework (zero API cost, full privacy)
- MPS GPU-accelerated binary code embeddings and similarity search
- Multi-round iterative analysis with confidence-driven stopping
- Multi-model voting for improved accuracy
- Checkpoint/resume for long-running analyses

Quick Start:
    $ pip install sentinel-reverse
    $ sentinel-reverse /path/to/binary -m exhaustive

Learn more: https://github.com/sgInnora/sentinel-reverse
"""

__version__ = "1.0.0"
__author__ = "Innora AI"
__license__ = "MIT"
__url__ = "https://github.com/sgInnora/sentinel-reverse"

from sentinel_reverse.engine.mlx_engine import (
    MLXReverseEngine,
    FunctionContext,
    AnalysisTask,
    ReverseResult,
)
from sentinel_reverse.engine.iterative_analyzer import (
    IterativeAnalyzer,
    IterativeResult,
    StopReason,
)
from sentinel_reverse.engine.model_voter import ModelVoter, VotingResult
from sentinel_reverse.engine.mps_accelerator import (
    MPSAccelerator,
    EmbeddingResult,
    SimilarityMatch,
)

__all__ = [
    "MLXReverseEngine",
    "FunctionContext",
    "AnalysisTask",
    "ReverseResult",
    "IterativeAnalyzer",
    "IterativeResult",
    "StopReason",
    "ModelVoter",
    "VotingResult",
    "MPSAccelerator",
    "EmbeddingResult",
    "SimilarityMatch",
]
