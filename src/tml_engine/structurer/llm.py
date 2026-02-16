"""LLM structurer — converts RawExtractionResult to TML primitive instances via Claude.

The structurer is the ONLY component that converts raw content to TML primitives.
It uses Claude with structured output to map unstructured content to the nine-primitive grid.
"""

from __future__ import annotations

import json
import re
import uuid

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from tml_engine.extractors.base import RawExtractionResult
from tml_engine.models.identity import ExtractionSource, HumanIdentity
from tml_engine.models.primitives import (
    Archetype,
    Binding,
    Capability,
    Connector,
    DecisionFactor,
    Domain,
    ExceptionRule,
    Policy,
    SkillReference,
)

_SYSTEM_PROMPT = """You are a TML (The Missing Layer) structuring engine. Your job is to analyze
raw extracted content and identify instances of TML primitives.

TML defines exactly nine primitives in a closed 3x3 grid:

          Context        Control        Interaction
Boundary  Scope          View           Connector
Commit    Domain         Archetype      Binding
Truth     Capability     Policy         Provenance

Your task: analyze the provided content and produce structured JSON output identifying
instances of these primitives. Focus especially on:

1. **Archetypes**: Roles, job titles, people described with specific responsibilities
2. **Domains**: Functional areas, accountability boundaries, outcome-oriented areas
3. **Capabilities**: Specific skills, decision logic, expertise, how-to knowledge
   - Include decision_factors (what matters in decisions)
   - Include heuristics (rules of thumb)
   - Include anti_patterns (common mistakes)
   - Include exceptions (when normal rules get overridden)
   - Include skills (tools, processes, methods used)
4. **Policies**: Rules, constraints, guardrails, compliance requirements
5. **Connectors**: Information inputs — where data/decisions flow IN from
6. **Bindings**: Information outputs — where data/decisions flow OUT to

For each primitive, assign a confidence level: "high", "medium", or "low".
Low-confidence items should be flagged for interview follow-up.

Output MUST be valid JSON matching the schema provided."""

_EXTRACTION_PROMPT = """Analyze the following content extracted from {source_type} ({source_id}).

Content blocks:
{content}

Based on this content, identify TML primitive instances. Return a JSON object with this structure:
{{
    "archetypes": [
        {{
            "role_name": "...",
            "role_description": "...",
            "primary_responsibilities": ["..."],
            "decision_authority": ["..."],
            "accountability_boundaries": ["..."],
            "confidence": "high|medium|low"
        }}
    ],
    "domains": [
        {{
            "name": "...",
            "description": "...",
            "outcome_definition": "...",
            "confidence": "high|medium|low"
        }}
    ],
    "capabilities": [
        {{
            "name": "...",
            "description": "...",
            "outcome": "...",
            "domain_name": "...",
            "decision_factors": [
                {{"name": "...", "description": "...", "weight": "primary|secondary|tiebreaker"}}
            ],
            "heuristics": ["..."],
            "anti_patterns": ["..."],
            "exceptions": [
                {{"trigger": "...", "override_description": "...", "reason": "..."}}
            ],
            "skills": [
                {{"name": "...", "description": "...", "skill_type": "agent_skill|workflow|tool|process|manual"}}
            ],
            "confidence": "high|medium|low"
        }}
    ],
    "policies": [
        {{
            "name": "...",
            "description": "...",
            "rule": "...",
            "enforcement_level": "hard|soft",
            "confidence": "high|medium|low"
        }}
    ],
    "connectors": [
        {{
            "name": "...",
            "reads_from": "...",
            "reads_from_type": "capability|domain|external_system",
            "description": "...",
            "confidence": "high|medium|low"
        }}
    ],
    "bindings": [
        {{
            "name": "...",
            "writes_to": "...",
            "writes_to_type": "capability|domain|external_system",
            "description": "...",
            "confidence": "high|medium|low"
        }}
    ]
}}

Only include primitives you can reasonably extract from the content.
If the content doesn't contain evidence for a primitive type, use an empty list.
Prefer fewer high-confidence extractions over many low-confidence ones."""


class PrimitiveWithConfidence(BaseModel):
    """Wraps a primitive ID with its extraction confidence level."""

    primitive_id: str
    confidence: str  # "high", "medium", "low"


class StructuredPrimitives(BaseModel):
    """The output of the LLM structuring pass — real Pydantic primitive instances."""

    scope_id: str
    archetypes: list[Archetype]
    domains: list[Domain]
    capabilities: list[Capability]
    policies: list[Policy]
    connectors: list[Connector]
    bindings: list[Binding]
    confidence_map: list[PrimitiveWithConfidence] = []


class LLMStructurer:
    """Converts RawExtractionResult to TML primitive instances via Claude.

    Uses the Anthropic Python SDK with structured output.
    """

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514") -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            kwargs: dict[str, str] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            self._client = AsyncAnthropic(**kwargs)
        return self._client

    async def structure(
        self,
        extraction: RawExtractionResult,
        scope_id: str,
        owner_identity: HumanIdentity | None = None,
    ) -> StructuredPrimitives:
        """Convert a RawExtractionResult into structured TML primitives.

        Returns a StructuredPrimitives object containing all discovered primitive
        instances with generated IDs and scope assignments.
        """
        content_text = self._format_content(extraction)

        prompt = _EXTRACTION_PROMPT.format(
            source_type=extraction.source_type,
            source_id=extraction.source_identifier,
            content=content_text,
        )

        client = self._get_client()
        response = await client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_json = self._extract_json(response.content[0].text)
        return self._build_primitives(raw_json, scope_id, extraction)

    def _format_content(self, extraction: RawExtractionResult) -> str:
        """Format content blocks for the LLM prompt."""
        parts: list[str] = []
        for block in extraction.content_blocks:
            header = f"[{block.content_type}] {block.context}"
            if block.url:
                header += f" ({block.url})"
            parts.append(f"--- {header} ---\n{block.content}")
        return "\n\n".join(parts)

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response text, handling code fences."""
        # Try to find JSON in code fences first
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Try the whole text as JSON
        return json.loads(text)

    def _build_primitives(
        self,
        raw: dict,
        scope_id: str,
        extraction: RawExtractionResult,
    ) -> StructuredPrimitives:
        """Convert raw LLM output into properly structured Pydantic primitive instances."""
        source = ExtractionSource(
            source_type=extraction.source_type,
            source_identifier=extraction.source_identifier,
            extracted_at=extraction.extracted_at,
        )
        # Placeholder identity for structurer-created archetypes
        placeholder_identity = HumanIdentity(
            email="unresolved@placeholder",
            display_name="Unresolved Identity",
        )

        def _id(prefix: str) -> str:
            return f"{prefix}-{uuid.uuid4().hex[:8]}"

        confidence_map: list[PrimitiveWithConfidence] = []

        def _track(primitive_id: str, raw_item: dict) -> None:
            confidence_map.append(
                PrimitiveWithConfidence(
                    primitive_id=primitive_id,
                    confidence=raw_item.get("confidence", "medium"),
                )
            )

        # Build archetypes
        archetypes: list[Archetype] = []
        for raw_arch in raw.get("archetypes", []):
            arch_id = _id("arch")
            arch = Archetype(
                id=arch_id,
                scope_id=scope_id,
                identity=placeholder_identity,
                role_name=raw_arch.get("role_name", ""),
                role_description=raw_arch.get("role_description", ""),
                primary_responsibilities=raw_arch.get("primary_responsibilities", []),
                decision_authority=raw_arch.get("decision_authority", []),
                accountability_boundaries=raw_arch.get("accountability_boundaries", []),
                source=source,
            )
            archetypes.append(arch)
            _track(arch_id, raw_arch)

        # Build domains, tracking name-to-id mapping
        domains: list[Domain] = []
        domain_name_to_id: dict[str, str] = {}
        for raw_dom in raw.get("domains", []):
            dom_id = _id("dom")
            name = raw_dom.get("name", "")
            domain_name_to_id[name] = dom_id
            dom = Domain(
                id=dom_id,
                scope_id=scope_id,
                name=name,
                description=raw_dom.get("description", ""),
                outcome_definition=raw_dom.get("outcome_definition", ""),
                accountable_archetype_id=archetypes[0].id if archetypes else "",
                source=source,
            )
            domains.append(dom)
            _track(dom_id, raw_dom)

        # Build capabilities
        capabilities: list[Capability] = []
        for raw_cap in raw.get("capabilities", []):
            cap_id = _id("cap")
            domain_name = raw_cap.get("domain_name", "")
            domain_id = domain_name_to_id.get(domain_name, domains[0].id if domains else "")

            skills = [
                SkillReference(
                    id=_id("skill"),
                    name=rs.get("name", ""),
                    description=rs.get("description", ""),
                    skill_type=rs.get("skill_type", "process"),
                )
                for rs in raw_cap.get("skills", [])
            ]
            exceptions = [
                ExceptionRule(
                    trigger=rex.get("trigger", ""),
                    override_description=rex.get("override_description", ""),
                    reason=rex.get("reason", ""),
                )
                for rex in raw_cap.get("exceptions", [])
            ]
            decision_factors = [
                DecisionFactor(
                    name=rdf.get("name", ""),
                    description=rdf.get("description", ""),
                    weight=rdf.get("weight"),
                )
                for rdf in raw_cap.get("decision_factors", [])
            ]

            cap = Capability(
                id=cap_id,
                scope_id=scope_id,
                domain_id=domain_id,
                name=raw_cap.get("name", ""),
                description=raw_cap.get("description", ""),
                outcome=raw_cap.get("outcome", ""),
                decision_factors=decision_factors,
                heuristics=raw_cap.get("heuristics", []),
                anti_patterns=raw_cap.get("anti_patterns", []),
                exceptions=exceptions,
                skills=skills,
                source=source,
            )
            capabilities.append(cap)
            _track(cap_id, raw_cap)

        # Build policies
        policies: list[Policy] = []
        for raw_pol in raw.get("policies", []):
            pol_id = _id("pol")
            pol = Policy(
                id=pol_id,
                scope_id=scope_id,
                name=raw_pol.get("name", ""),
                description=raw_pol.get("description", ""),
                rule=raw_pol.get("rule", ""),
                attaches_to=[],  # Linked during confirmation
                enforcement_level=raw_pol.get("enforcement_level", "soft"),
                source=source,
            )
            policies.append(pol)
            _track(pol_id, raw_pol)

        # Build connectors
        connectors: list[Connector] = []
        for raw_conn in raw.get("connectors", []):
            conn_id = _id("conn")
            conn = Connector(
                id=conn_id,
                scope_id=scope_id,
                name=raw_conn.get("name", ""),
                reads_from=raw_conn.get("reads_from", ""),
                reads_from_type=raw_conn.get("reads_from_type", "external_system"),
                governed_by_policy_ids=[],
                description=raw_conn.get("description", ""),
                source=source,
            )
            connectors.append(conn)
            _track(conn_id, raw_conn)

        # Build bindings
        bindings: list[Binding] = []
        for raw_bind in raw.get("bindings", []):
            bind_id = _id("bind")
            bind = Binding(
                id=bind_id,
                scope_id=scope_id,
                name=raw_bind.get("name", ""),
                writes_to=raw_bind.get("writes_to", ""),
                writes_to_type=raw_bind.get("writes_to_type", "external_system"),
                governed_by_policy_ids=[],
                description=raw_bind.get("description", ""),
                source=source,
            )
            bindings.append(bind)
            _track(bind_id, raw_bind)

        return StructuredPrimitives(
            scope_id=scope_id,
            archetypes=archetypes,
            domains=domains,
            capabilities=capabilities,
            policies=policies,
            connectors=connectors,
            bindings=bindings,
            confidence_map=confidence_map,
        )
