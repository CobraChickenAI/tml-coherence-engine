"""Adaptive interview extractor — Claude-powered five-phase expertise extraction.

The interview is the primary extraction method. It's adaptive: it knows what
has already been extracted from other sources and focuses on gaps, ambiguities,
and tacit knowledge that couldn't be captured from documentation.

Phases:
1. Context Setting (establishing Scope)
2. Archetype Discovery (who they are in the system)
3. Domain Mapping (accountability boundaries)
4. Capability Deep Dive (per Domain — the expertise)
5. Policy + Flow Discovery (constraints and interactions)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel

from tml_engine.extractors.base import BaseExtractor, ContentBlock, RawExtractionResult

_INTERVIEW_SYSTEM_PROMPT = """You are conducting an expertise extraction interview. Your goal is to
understand how this person thinks, decides, and acts in their role.

You are NOT gathering information for a report. You are building a
structured representation of their decision-making architecture using
TML primitives: Archetype (who they are), Domain (where they hold
accountability), Capability (what they can do and how they decide),
Policy (what constrains them), and the Connectors/Bindings that show
how their work flows to and from other people.

{prior_context}

Interview style:
- Ask one question at a time
- Use their language, not framework terminology
- Follow interesting threads — don't stick rigidly to the script
- If they mention something unexpected, explore it
- Mirror back what you think you heard and ask them to confirm
- Be conversational and genuine, not clinical
- When you have enough for the current phase, signal readiness to move on

After gathering sufficient information for each phase, output a structured
JSON summary of what you've learned. Prefix JSON with [PHASE_COMPLETE] on its own line.

Current phase: {phase}
Phase instructions: {phase_instructions}"""


class InterviewPhase(StrEnum):
    CONTEXT = "context"
    ARCHETYPE = "archetype"
    DOMAINS = "domains"
    CAPABILITIES = "capabilities"
    POLICIES_FLOWS = "policies_flows"
    COMPLETE = "complete"


_PHASE_INSTRUCTIONS = {
    InterviewPhase.CONTEXT: (
        "Establish the scope of this person's work. Ask about their organization, "
        "their team, what area they work in. Produce a Scope description."
    ),
    InterviewPhase.ARCHETYPE: (
        "Discover who they are in the system. Ask them to describe their role "
        "in their own words. What do people come to them for? Where does their "
        "responsibility end? Produce an Archetype with role_name, role_description, "
        "primary_responsibilities, decision_authority, and accountability_boundaries."
    ),
    InterviewPhase.DOMAINS: (
        "Map their accountability areas. Walk through a typical week. What decisions "
        "do they make? Group these into domains. For each domain, define the outcome "
        "that represents success. Produce a list of Domains."
    ),
    InterviewPhase.CAPABILITIES: (
        "Deep dive into each domain's capabilities. For each major thing they do, ask: "
        "What do you consider when making this decision? What are your rules of thumb? "
        "What does a bad version look like? When do you throw out the normal playbook? "
        "What tools or processes do you use? Produce Capabilities with decision_factors, "
        "heuristics, anti_patterns, exceptions, and skills."
    ),
    InterviewPhase.POLICIES_FLOWS: (
        "Discover constraints and information flows. What rules can they never break? "
        "Whose output do they depend on? Who depends on their decisions? "
        "Produce Policies, Connectors (inputs), and Bindings (outputs)."
    ),
}

_PHASE_ORDER = [
    InterviewPhase.CONTEXT,
    InterviewPhase.ARCHETYPE,
    InterviewPhase.DOMAINS,
    InterviewPhase.CAPABILITIES,
    InterviewPhase.POLICIES_FLOWS,
]


class InterviewState(BaseModel):
    """Serializable state for pause/resume."""
    session_id: str
    phase: InterviewPhase
    conversation_history: list[dict]  # {"role": "user"|"assistant", "content": "..."}
    discovered_primitives: dict  # Phase results accumulated
    identity_email: str


class InterviewEngine:
    """Runs an adaptive interview using Claude to extract TML primitives.

    The engine manages conversation state, phase transitions, and
    primitive extraction from interview responses.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            kwargs = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def new_session(self, identity_email: str) -> InterviewState:
        """Create a new interview session."""
        return InterviewState(
            session_id=f"interview-{uuid.uuid4().hex[:8]}",
            phase=InterviewPhase.CONTEXT,
            conversation_history=[],
            discovered_primitives={},
            identity_email=identity_email,
        )

    def get_opening_message(self, state: InterviewState, prior_extractions: list | None = None) -> str:
        """Get the opening message for the current phase."""
        if state.phase == InterviewPhase.CONTEXT:
            if prior_extractions:
                return (
                    "We've already extracted some information about your role "
                    "from prior sources. I'm going to walk through what we found "
                    "and ask you to fill in the gaps. But first — tell me about "
                    "your organization and the area you work in."
                )
            return (
                "I'd like to understand how you think about your work — "
                "specifically, what decisions you make and how you make them. "
                "Let's start with some context: what organization do you work for, "
                "and what area or team are you part of?"
            )
        elif state.phase == InterviewPhase.ARCHETYPE:
            return (
                "Now let's talk about your role specifically. "
                "How would you describe what you do in your own words? "
                "What do people come to you for that they can't get elsewhere?"
            )
        elif state.phase == InterviewPhase.DOMAINS:
            return (
                "Walk me through a typical week. What are the main areas "
                "where you make decisions or hold accountability?"
            )
        elif state.phase == InterviewPhase.CAPABILITIES:
            return (
                "Let's dig into the specifics. For the areas you just described, "
                "tell me about a recent decision you made. What did you consider? "
                "What factors mattered most?"
            )
        elif state.phase == InterviewPhase.POLICIES_FLOWS:
            return (
                "Almost done. Let's talk about constraints and dependencies. "
                "What rules can you never break, no matter what? "
                "And whose work do you depend on to do your job?"
            )
        return "Thank you — we've covered everything."

    def build_system_prompt(
        self,
        state: InterviewState,
        prior_extractions: list | None = None,
    ) -> str:
        """Build the system prompt for the current phase."""
        prior_context = ""
        if prior_extractions:
            prior_context = (
                "We have already extracted the following from prior sources:\n"
                + json.dumps(prior_extractions, indent=2)
                + "\n\nFocus on validating, correcting, and filling gaps."
            )

        if state.discovered_primitives:
            prior_context += (
                "\n\nPrior interview phases have discovered:\n"
                + json.dumps(state.discovered_primitives, indent=2)
            )

        return _INTERVIEW_SYSTEM_PROMPT.format(
            prior_context=prior_context,
            phase=state.phase.value,
            phase_instructions=_PHASE_INSTRUCTIONS.get(state.phase, ""),
        )

    async def send_message(
        self,
        state: InterviewState,
        user_message: str,
        prior_extractions: list | None = None,
    ) -> tuple[str, InterviewState]:
        """Send a message in the interview and get Claude's response.

        Returns (assistant_response, updated_state).
        """
        # Add user message to history
        state.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        system = self.build_system_prompt(state, prior_extractions)

        client = self._get_client()
        response = client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system,
            messages=state.conversation_history,
        )

        assistant_text = response.content[0].text

        # Check for phase completion signal
        if "[PHASE_COMPLETE]" in assistant_text:
            parts = assistant_text.split("[PHASE_COMPLETE]")
            response_text = parts[0].strip()
            phase_data = self._extract_phase_json(parts[1]) if len(parts) > 1 else {}

            # Store phase results
            state.discovered_primitives[state.phase.value] = phase_data

            # Advance phase
            state = self._advance_phase(state)

            # Add the response (without the JSON) to history
            state.conversation_history.append({
                "role": "assistant",
                "content": response_text,
            })

            return response_text, state
        else:
            state.conversation_history.append({
                "role": "assistant",
                "content": assistant_text,
            })
            return assistant_text, state

    def _advance_phase(self, state: InterviewState) -> InterviewState:
        """Move to the next interview phase."""
        current_idx = _PHASE_ORDER.index(state.phase) if state.phase in _PHASE_ORDER else -1
        if current_idx < len(_PHASE_ORDER) - 1:
            state.phase = _PHASE_ORDER[current_idx + 1]
        else:
            state.phase = InterviewPhase.COMPLETE
        return state

    def _extract_phase_json(self, text: str) -> dict:
        """Extract JSON data from phase completion output."""
        text = text.strip()
        try:
            import re
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return {"raw_text": text}

    def is_complete(self, state: InterviewState) -> bool:
        """Check if the interview is complete."""
        return state.phase == InterviewPhase.COMPLETE

    def to_extraction_result(self, state: InterviewState) -> RawExtractionResult:
        """Convert interview results to a RawExtractionResult for the structurer."""
        content_blocks: list[ContentBlock] = []

        for phase_name, phase_data in state.discovered_primitives.items():
            content_blocks.append(
                ContentBlock(
                    content=json.dumps(phase_data, indent=2),
                    content_type="response",
                    context=f"Interview phase: {phase_name}",
                    author=state.identity_email,
                )
            )

        # Also include the full conversation as a content block
        conversation_text = "\n\n".join(
            f"[{msg['role'].upper()}]: {msg['content']}"
            for msg in state.conversation_history
        )
        content_blocks.append(
            ContentBlock(
                content=conversation_text,
                content_type="response",
                context="Full interview transcript",
                author=state.identity_email,
            )
        )

        return RawExtractionResult(
            source_type="interview",
            source_identifier=state.session_id,
            content_blocks=content_blocks,
            metadata={
                "identity_email": state.identity_email,
                "phases_completed": list(state.discovered_primitives.keys()),
                "total_messages": len(state.conversation_history),
            },
            extracted_at=datetime.now(UTC),
        )


class InterviewExtractor(BaseExtractor):
    """Extractor interface adapter for the interview engine.

    Note: The interview is inherently interactive and cannot run through
    the standard extract() interface without user interaction. This adapter
    provides the interface for when an interview session is already complete.
    """

    def __init__(self, engine: InterviewEngine | None = None) -> None:
        self._engine = engine or InterviewEngine()

    async def extract(self, config: dict) -> RawExtractionResult:
        """Extract from a completed interview session.

        config must contain 'state' (InterviewState) for completed sessions.
        """
        state_data = config.get("state")
        if state_data is None:
            raise ValueError("config must contain 'state' with completed InterviewState")

        if isinstance(state_data, InterviewState):
            state = state_data
        else:
            state = InterviewState.model_validate(state_data)

        return self._engine.to_extraction_result(state)

    async def list_available(self) -> list[dict]:
        """Not applicable for interviews."""
        return []
