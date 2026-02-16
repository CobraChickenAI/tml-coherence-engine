"""Tests for the LLM structurer.

Tests the JSON parsing, content formatting, and primitive building logic
without requiring an actual Claude API key.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tml_engine.extractors.base import ContentBlock, RawExtractionResult
from tml_engine.structurer.llm import LLMStructurer, StructuredPrimitives


def _make_extraction() -> RawExtractionResult:
    return RawExtractionResult(
        source_type="web",
        source_identifier="https://example.com",
        content_blocks=[
            ContentBlock(
                content="We provide logistics optimization services.",
                content_type="page",
                context="About Us",
                url="https://example.com/about",
            ),
            ContentBlock(
                content="Our team evaluates carriers based on safety records.",
                content_type="page",
                context="Services",
                url="https://example.com/services",
            ),
        ],
        metadata={"pages_crawled": 2},
        extracted_at=datetime.now(UTC),
    )


def _make_raw_llm_output() -> dict:
    return {
        "archetypes": [
            {
                "role_name": "Operations Manager",
                "role_description": "Manages logistics operations",
                "primary_responsibilities": ["Carrier evaluation", "Load matching"],
                "decision_authority": ["Approve carriers"],
                "accountability_boundaries": ["Does not set pricing"],
                "confidence": "high",
            }
        ],
        "domains": [
            {
                "name": "Carrier Management",
                "description": "Managing carrier relationships",
                "outcome_definition": "Reliable carrier network",
                "confidence": "high",
            }
        ],
        "capabilities": [
            {
                "name": "Carrier Safety Assessment",
                "description": "Evaluate carrier safety",
                "outcome": "Accept/reject decision",
                "domain_name": "Carrier Management",
                "decision_factors": [
                    {"name": "Safety Score", "description": "FMCSA score", "weight": "primary"}
                ],
                "heuristics": ["Green scores = fast track"],
                "anti_patterns": ["Approving on rate alone"],
                "exceptions": [
                    {
                        "trigger": "Emergency load",
                        "override_description": "Conditional approval",
                        "reason": "Service failure risk",
                    }
                ],
                "skills": [
                    {
                        "name": "FMCSA Lookup",
                        "description": "Query FMCSA SAFER",
                        "skill_type": "tool",
                    }
                ],
                "confidence": "high",
            }
        ],
        "policies": [
            {
                "name": "Safety Floor",
                "description": "Minimum safety requirements",
                "rule": "No carriers with unsatisfactory ratings",
                "enforcement_level": "hard",
                "confidence": "high",
            }
        ],
        "connectors": [
            {
                "name": "FMCSA Data",
                "reads_from": "FMCSA SAFER",
                "reads_from_type": "external_system",
                "description": "Safety data input",
                "confidence": "medium",
            }
        ],
        "bindings": [
            {
                "name": "Dispatch Output",
                "writes_to": "Dispatch Team",
                "writes_to_type": "external_system",
                "description": "Carrier assignments",
                "confidence": "medium",
            }
        ],
    }


class TestLLMStructurer:
    def test_format_content(self) -> None:
        structurer = LLMStructurer()
        extraction = _make_extraction()
        text = structurer._format_content(extraction)
        assert "About Us" in text
        assert "Services" in text
        assert "logistics optimization" in text
        assert "https://example.com/about" in text

    def test_extract_json_raw(self) -> None:
        structurer = LLMStructurer()
        raw = '{"archetypes": [], "domains": []}'
        result = structurer._extract_json(raw)
        assert result == {"archetypes": [], "domains": []}

    def test_extract_json_code_fence(self) -> None:
        structurer = LLMStructurer()
        raw = 'Here is the result:\n```json\n{"archetypes": []}\n```\nDone.'
        result = structurer._extract_json(raw)
        assert result == {"archetypes": []}

    def test_extract_json_code_fence_no_lang(self) -> None:
        structurer = LLMStructurer()
        raw = '```\n{"domains": [{"name": "test"}]}\n```'
        result = structurer._extract_json(raw)
        assert result["domains"][0]["name"] == "test"

    def test_build_primitives(self) -> None:
        structurer = LLMStructurer()
        extraction = _make_extraction()
        raw = _make_raw_llm_output()

        result = structurer._build_primitives(raw, "scope-001", extraction)

        assert isinstance(result, StructuredPrimitives)
        assert result.scope_id == "scope-001"

        # Archetypes — now Pydantic models, not dicts
        assert len(result.archetypes) == 1
        arch = result.archetypes[0]
        assert arch.role_name == "Operations Manager"
        assert arch.scope_id == "scope-001"
        assert arch.id.startswith("arch-")
        assert arch.source is not None

        # Domains
        assert len(result.domains) == 1
        dom = result.domains[0]
        assert dom.name == "Carrier Management"
        assert dom.scope_id == "scope-001"
        assert dom.id.startswith("dom-")

        # Capabilities
        assert len(result.capabilities) == 1
        cap = result.capabilities[0]
        assert cap.name == "Carrier Safety Assessment"
        assert cap.domain_id == dom.id  # Linked to domain
        assert len(cap.decision_factors) == 1
        assert len(cap.heuristics) == 1
        assert len(cap.anti_patterns) == 1
        assert len(cap.exceptions) == 1
        assert len(cap.skills) == 1

        # Policies
        assert len(result.policies) == 1
        pol = result.policies[0]
        assert pol.name == "Safety Floor"
        assert pol.enforcement_level == "hard"

        # Connectors
        assert len(result.connectors) == 1
        conn = result.connectors[0]
        assert conn.reads_from == "FMCSA SAFER"

        # Bindings
        assert len(result.bindings) == 1
        bind = result.bindings[0]
        assert bind.writes_to == "Dispatch Team"

        # Confidence tracking
        assert len(result.confidence_map) > 0
        arch_conf = next(c for c in result.confidence_map if c.primitive_id == arch.id)
        assert arch_conf.confidence == "high"

    def test_build_primitives_empty(self) -> None:
        structurer = LLMStructurer()
        extraction = _make_extraction()
        raw = {
            "archetypes": [],
            "domains": [],
            "capabilities": [],
            "policies": [],
            "connectors": [],
            "bindings": [],
        }

        result = structurer._build_primitives(raw, "scope-001", extraction)
        assert len(result.archetypes) == 0
        assert len(result.domains) == 0
        assert len(result.capabilities) == 0

    def test_build_primitives_missing_keys(self) -> None:
        structurer = LLMStructurer()
        extraction = _make_extraction()
        raw = {}  # No keys at all

        result = structurer._build_primitives(raw, "scope-001", extraction)
        assert len(result.archetypes) == 0
        assert len(result.domains) == 0

    def test_structured_primitives_model(self) -> None:
        """Test StructuredPrimitives can be created with empty lists."""
        sp = StructuredPrimitives(
            scope_id="scope-001",
            archetypes=[],
            domains=[],
            capabilities=[],
            policies=[],
            connectors=[],
            bindings=[],
        )
        assert sp.scope_id == "scope-001"
        assert len(sp.archetypes) == 0
        data = sp.model_dump()
        assert data["scope_id"] == "scope-001"

    def test_structured_primitives_with_confidence_map(self) -> None:
        from tml_engine.structurer.llm import PrimitiveWithConfidence

        sp = StructuredPrimitives(
            scope_id="scope-001",
            archetypes=[],
            domains=[],
            capabilities=[],
            policies=[],
            connectors=[],
            bindings=[],
            confidence_map=[
                PrimitiveWithConfidence(primitive_id="arch-001", confidence="high"),
            ],
        )
        assert len(sp.confidence_map) == 1
        assert sp.confidence_map[0].primitive_id == "arch-001"
