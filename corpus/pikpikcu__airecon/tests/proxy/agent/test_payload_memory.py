"""Tests for Payload Memory."""


class TestPayloadMemory:
    def test_module_imports(self):
        from airecon.proxy.agent import payload_memory
        assert payload_memory is not None

    def test_engine_class_exists(self):
        from airecon.proxy.agent.payload_memory import PayloadMemoryEngine
        assert PayloadMemoryEngine is not None

    def test_prioritize_payloads_promotes_successful_history(self):
        from airecon.proxy.agent.payload_memory import PayloadMemoryEngine

        engine = PayloadMemoryEngine()
        engine.record_attempt(
            payload="known-good",
            vuln_type="xss",
            target="example.com",
            param="q",
            success=True,
            confidence=0.9,
            status_code=200,
            tech_stack=["nginx"],
        )

        ordered = engine.prioritize_payloads(
            ["baseline-a", "known-good", "baseline-b"],
            vuln_type="xss",
            target="example.com",
            tech="nginx",
        )

        assert ordered[0] == "known-good"
        assert ordered.count("known-good") == 1

    def test_prioritize_payloads_can_reuse_successful_custom_payloads(self):
        from airecon.proxy.agent.payload_memory import PayloadMemoryEngine

        engine = PayloadMemoryEngine()
        engine.record_attempt(
            payload="custom-bypass",
            vuln_type="sql_injection",
            target="example.com",
            param="id",
            success=True,
            confidence=0.95,
            status_code=200,
        )

        ordered = engine.prioritize_payloads(
            ["' OR 1=1--"],
            vuln_type="sql_injection",
            target="example.com",
        )

        assert ordered[0] == "custom-bypass"
        assert "' OR 1=1--" in ordered
