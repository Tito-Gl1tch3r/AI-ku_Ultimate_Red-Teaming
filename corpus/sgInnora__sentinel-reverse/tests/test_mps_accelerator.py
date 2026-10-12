# -*- coding: utf-8 -*-
"""Tests for MPS GPU accelerator."""

import pytest
from sentinel_reverse.engine.mps_accelerator import (
    MPSAccelerator,
    EmbeddingResult,
    SimilarityMatch,
    FunctionPrediction,
)


class TestMPSAccelerator:
    """Test MPS accelerator (works in CPU fallback mode too)."""

    def test_init(self):
        accel = MPSAccelerator(embedding_dim=128)
        assert accel.embedding_dim == 128

    def test_compute_embedding(self):
        accel = MPSAccelerator(embedding_dim=64)
        result = accel.compute_embedding("push rbp\nmov rbp, rsp\nret", address=0x1000)
        assert isinstance(result, EmbeddingResult)
        assert result.address == 0x1000
        assert result.dimension == 64

    def test_batch_compute_embeddings(self):
        accel = MPSAccelerator(embedding_dim=64)
        functions = [
            (0x1000, "push rbp\nmov rbp, rsp"),
            (0x2000, "mov eax, 1\nret"),
            (0x3000, "xor eax, eax\nret"),
        ]
        results = accel.batch_compute_embeddings(functions)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, EmbeddingResult)
            assert r.dimension == 64

    def test_predict_function_name(self):
        accel = MPSAccelerator(embedding_dim=64)
        emb = accel.compute_embedding("call malloc\nmov [rbx], rax", address=0x5000)
        pred = accel.predict_function_name(emb.embedding, address=0x5000)
        assert isinstance(pred, FunctionPrediction)
        assert pred.address == 0x5000
        assert pred.predicted_name != ""
        assert pred.category != ""
        assert 0.0 <= pred.confidence <= 1.0

    def test_get_stats(self):
        accel = MPSAccelerator()
        stats = accel.get_stats()
        assert "device" in stats
        assert "mps_available" in stats
        assert "torch_available" in stats
        assert "embedding_dim" in stats
        assert "total_embeddings" in stats

    def test_embedding_cache(self):
        accel = MPSAccelerator(embedding_dim=64, cache_embeddings=True)
        asm = "push rbp\nmov rbp, rsp\npop rbp\nret"
        r1 = accel.compute_embedding(asm, address=0x1000)
        r2 = accel.compute_embedding(asm, address=0x2000)
        # Second call should hit cache (elapsed_ms = 0)
        assert r2.elapsed_ms == 0.0

    def test_tokenize_assembly(self):
        accel = MPSAccelerator()
        tokens = accel._tokenize_assembly("push rbp\nmov rbp, rsp")
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert all(isinstance(t, int) for t in tokens)


class TestDataClasses:
    """Test result dataclasses."""

    def test_embedding_result(self):
        r = EmbeddingResult(
            address=0x1000, embedding=[0.1, 0.2, 0.3],
            dimension=3, elapsed_ms=1.5,
        )
        assert r.address == 0x1000
        assert r.dimension == 3

    def test_similarity_match(self):
        m = SimilarityMatch(
            source_address=0x1000, target_address=0x2000,
            similarity_score=0.95, match_type="exact",
        )
        assert m.similarity_score == 0.95
        assert m.match_type == "exact"

    def test_function_prediction(self):
        p = FunctionPrediction(
            address=0x3000, predicted_name="sub_encrypt_3000",
            category="crypto", confidence=0.8,
            alternatives=[("sub_decrypt_3000", 0.5)],
        )
        assert p.category == "crypto"
        assert len(p.alternatives) == 1
