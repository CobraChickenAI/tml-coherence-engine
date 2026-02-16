"""Tests for the adaptive interview extractor.

Tests the interview engine state management, phase transitions,
and extraction result generation without requiring a Claude API key.
"""

from __future__ import annotations

import pytest

from tml_engine.extractors.interview import (
    _PHASE_INSTRUCTIONS,
    _PHASE_ORDER,
    InterviewEngine,
    InterviewExtractor,
    InterviewPhase,
    InterviewState,
)


class TestInterviewPhase:
    def test_phase_values(self) -> None:
        assert InterviewPhase.CONTEXT == "context"
        assert InterviewPhase.ARCHETYPE == "archetype"
        assert InterviewPhase.DOMAINS == "domains"
        assert InterviewPhase.CAPABILITIES == "capabilities"
        assert InterviewPhase.POLICIES_FLOWS == "policies_flows"
        assert InterviewPhase.COMPLETE == "complete"

    def test_phase_order(self) -> None:
        assert len(_PHASE_ORDER) == 5
        assert _PHASE_ORDER[0] == InterviewPhase.CONTEXT
        assert _PHASE_ORDER[-1] == InterviewPhase.POLICIES_FLOWS

    def test_all_phases_have_instructions(self) -> None:
        for phase in _PHASE_ORDER:
            assert phase in _PHASE_INSTRUCTIONS
            assert len(_PHASE_INSTRUCTIONS[phase]) > 0


class TestInterviewState:
    def test_create_state(self) -> None:
        state = InterviewState(
            session_id="test-001",
            phase=InterviewPhase.CONTEXT,
            conversation_history=[],
            discovered_primitives={},
            identity_email="test@example.com",
        )
        assert state.session_id == "test-001"
        assert state.phase == InterviewPhase.CONTEXT
        assert state.identity_email == "test@example.com"

    def test_state_serialization(self) -> None:
        state = InterviewState(
            session_id="test-001",
            phase=InterviewPhase.ARCHETYPE,
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
            discovered_primitives={"context": {"scope": "test org"}},
            identity_email="test@example.com",
        )
        data = state.model_dump()
        restored = InterviewState.model_validate(data)
        assert restored.session_id == state.session_id
        assert restored.phase == state.phase
        assert len(restored.conversation_history) == 2

    def test_state_json_round_trip(self) -> None:
        state = InterviewState(
            session_id="test-002",
            phase=InterviewPhase.DOMAINS,
            conversation_history=[],
            discovered_primitives={},
            identity_email="user@test.com",
        )
        json_str = state.model_dump_json()
        restored = InterviewState.model_validate_json(json_str)
        assert restored.session_id == "test-002"
        assert restored.phase == InterviewPhase.DOMAINS


class TestInterviewEngine:
    def test_new_session(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        assert state.session_id.startswith("interview-")
        assert state.phase == InterviewPhase.CONTEXT
        assert state.identity_email == "test@example.com"
        assert len(state.conversation_history) == 0
        assert len(state.discovered_primitives) == 0

    def test_opening_message_context(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        msg = engine.get_opening_message(state)
        assert "organization" in msg.lower() or "work" in msg.lower()

    def test_opening_message_with_prior(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        msg = engine.get_opening_message(state, prior_extractions=[{"type": "web"}])
        assert "already extracted" in msg.lower()

    def test_opening_messages_all_phases(self) -> None:
        engine = InterviewEngine()
        for phase in _PHASE_ORDER:
            state = InterviewState(
                session_id="test",
                phase=phase,
                conversation_history=[],
                discovered_primitives={},
                identity_email="test@example.com",
            )
            msg = engine.get_opening_message(state)
            assert len(msg) > 0

    def test_build_system_prompt(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        prompt = engine.build_system_prompt(state)
        assert "expertise extraction interview" in prompt
        assert "context" in prompt

    def test_build_system_prompt_with_prior(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        prompt = engine.build_system_prompt(state, prior_extractions=[{"domains": ["Engineering"]}])
        assert "already extracted" in prompt
        assert "Engineering" in prompt

    def test_build_system_prompt_with_discovered(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        state.discovered_primitives = {"context": {"scope": "Test Org"}}
        prompt = engine.build_system_prompt(state)
        assert "Test Org" in prompt

    def test_advance_phase(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")

        assert state.phase == InterviewPhase.CONTEXT
        state = engine._advance_phase(state)
        assert state.phase == InterviewPhase.ARCHETYPE
        state = engine._advance_phase(state)
        assert state.phase == InterviewPhase.DOMAINS
        state = engine._advance_phase(state)
        assert state.phase == InterviewPhase.CAPABILITIES
        state = engine._advance_phase(state)
        assert state.phase == InterviewPhase.POLICIES_FLOWS
        state = engine._advance_phase(state)
        assert state.phase == InterviewPhase.COMPLETE

    def test_is_complete(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        assert engine.is_complete(state) is False

        state.phase = InterviewPhase.COMPLETE
        assert engine.is_complete(state) is True

    def test_extract_phase_json(self) -> None:
        engine = InterviewEngine()
        result = engine._extract_phase_json('{"scope": "test"}')
        assert result["scope"] == "test"

    def test_extract_phase_json_code_fence(self) -> None:
        engine = InterviewEngine()
        result = engine._extract_phase_json('```json\n{"scope": "test"}\n```')
        assert result["scope"] == "test"

    def test_extract_phase_json_invalid(self) -> None:
        engine = InterviewEngine()
        result = engine._extract_phase_json("not json at all")
        assert "raw_text" in result

    def test_to_extraction_result(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        state.conversation_history = [
            {"role": "user", "content": "I work at Test Corp"},
            {"role": "assistant", "content": "Tell me more"},
        ]
        state.discovered_primitives = {
            "context": {"scope": "Test Corp Engineering"},
        }

        result = engine.to_extraction_result(state)
        assert result.source_type == "interview"
        assert result.source_identifier == state.session_id
        assert len(result.content_blocks) == 2  # 1 phase + 1 transcript
        assert result.metadata["identity_email"] == "test@example.com"
        assert result.metadata["total_messages"] == 2

    def test_to_extraction_result_empty(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        result = engine.to_extraction_result(state)
        assert result.source_type == "interview"
        assert len(result.content_blocks) == 1  # Just the empty transcript


class TestInterviewExtractor:
    @pytest.mark.asyncio
    async def test_extract_requires_state(self) -> None:
        extractor = InterviewExtractor()
        with pytest.raises(ValueError, match="state"):
            await extractor.extract({})

    @pytest.mark.asyncio
    async def test_extract_from_state(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        state.discovered_primitives = {"context": {"scope": "Test"}}
        state.conversation_history = [{"role": "user", "content": "test"}]

        extractor = InterviewExtractor(engine)
        result = await extractor.extract({"state": state})
        assert result.source_type == "interview"
        assert len(result.content_blocks) >= 1

    @pytest.mark.asyncio
    async def test_extract_from_serialized_state(self) -> None:
        engine = InterviewEngine()
        state = engine.new_session("test@example.com")
        state_data = state.model_dump()

        extractor = InterviewExtractor(engine)
        result = await extractor.extract({"state": state_data})
        assert result.source_type == "interview"

    @pytest.mark.asyncio
    async def test_list_available(self) -> None:
        extractor = InterviewExtractor()
        result = await extractor.list_available()
        assert result == []
