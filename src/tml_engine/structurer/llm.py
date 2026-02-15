"""LLM structurer — converts RawExtractionResult to TML primitive instances via Claude.

The structurer is the ONLY component that converts raw content to TML primitives.
It uses Claude with structured output to map unstructured content to the nine-primitive grid.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from tml_engine.extractors.base import RawExtractionResult
from tml_engine.models.identity import ExtractionSource, HumanIdentity

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


class StructuredPrimitives(BaseModel):
    """The output of the LLM structuring pass."""

    scope_id: str
    archetypes: list[dict]
    domains: list[dict]
    capabilities: list[dict]
    policies: list[dict]
    connectors: list[dict]
    bindings: list[dict]


class LLMStructurer:
    """Converts RawExtractionResult to TML primitive instances via Claude.

    Uses the Anthropic Python SDK with structured output.
    """

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514") -> None:
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
        response = client.messages.create(
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
        import re
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
        """Convert raw LLM output into properly structured primitives with IDs."""
        source = ExtractionSource(
            source_type=extraction.source_type,
            source_identifier=extraction.source_identifier,
            extracted_at=extraction.extracted_at,
        )

        def _id(prefix: str) -> str:
            return f"{prefix}-{uuid.uuid4().hex[:8]}"

        # Build archetypes
        archetypes = []
        for raw_arch in raw.get("archetypes", []):
            archetypes.append({
                "id": _id("arch"),
                "scope_id": scope_id,
                "role_name": raw_arch.get("role_name", ""),
                "role_description": raw_arch.get("role_description", ""),
                "primary_responsibilities": raw_arch.get("primary_responsibilities", []),
                "decision_authority": raw_arch.get("decision_authority", []),
                "accountability_boundaries": raw_arch.get("accountability_boundaries", []),
                "confidence": raw_arch.get("confidence", "medium"),
                "source": source.model_dump(mode="json"),
            })

        # Build domains, tracking name-to-id mapping
        domains = []
        domain_name_to_id: dict[str, str] = {}
        for raw_dom in raw.get("domains", []):
            dom_id = _id("dom")
            name = raw_dom.get("name", "")
            domain_name_to_id[name] = dom_id
            domains.append({
                "id": dom_id,
                "scope_id": scope_id,
                "name": name,
                "description": raw_dom.get("description", ""),
                "outcome_definition": raw_dom.get("outcome_definition", ""),
                "accountable_archetype_id": archetypes[0]["id"] if archetypes else "",
                "confidence": raw_dom.get("confidence", "medium"),
                "source": source.model_dump(mode="json"),
            })

        # Build capabilities
        capabilities = []
        for raw_cap in raw.get("capabilities", []):
            domain_name = raw_cap.get("domain_name", "")
            domain_id = domain_name_to_id.get(domain_name, domains[0]["id"] if domains else "")

            skills = []
            for raw_skill in raw_cap.get("skills", []):
                skills.append({
                    "id": _id("skill"),
                    "name": raw_skill.get("name", ""),
                    "description": raw_skill.get("description", ""),
                    "skill_type": raw_skill.get("skill_type", "process"),
                })

            exceptions = []
            for raw_exc in raw_cap.get("exceptions", []):
                exceptions.append({
                    "trigger": raw_exc.get("trigger", ""),
                    "override_description": raw_exc.get("override_description", ""),
                    "reason": raw_exc.get("reason", ""),
                })

            decision_factors = []
            for raw_df in raw_cap.get("decision_factors", []):
                decision_factors.append({
                    "name": raw_df.get("name", ""),
                    "description": raw_df.get("description", ""),
                    "weight": raw_df.get("weight"),
                })

            capabilities.append({
                "id": _id("cap"),
                "scope_id": scope_id,
                "domain_id": domain_id,
                "name": raw_cap.get("name", ""),
                "description": raw_cap.get("description", ""),
                "outcome": raw_cap.get("outcome", ""),
                "decision_factors": decision_factors,
                "heuristics": raw_cap.get("heuristics", []),
                "anti_patterns": raw_cap.get("anti_patterns", []),
                "exceptions": exceptions,
                "skills": skills,
                "confidence": raw_cap.get("confidence", "medium"),
                "source": source.model_dump(mode="json"),
            })

        # Build policies
        policies = []
        for raw_pol in raw.get("policies", []):
            policies.append({
                "id": _id("pol"),
                "scope_id": scope_id,
                "name": raw_pol.get("name", ""),
                "description": raw_pol.get("description", ""),
                "rule": raw_pol.get("rule", ""),
                "attaches_to": [],  # To be linked during confirmation
                "enforcement_level": raw_pol.get("enforcement_level", "soft"),
                "confidence": raw_pol.get("confidence", "medium"),
                "source": source.model_dump(mode="json"),
            })

        # Build connectors
        connectors = []
        for raw_conn in raw.get("connectors", []):
            connectors.append({
                "id": _id("conn"),
                "scope_id": scope_id,
                "name": raw_conn.get("name", ""),
                "reads_from": raw_conn.get("reads_from", ""),
                "reads_from_type": raw_conn.get("reads_from_type", "external_system"),
                "governed_by_policy_ids": [],
                "description": raw_conn.get("description", ""),
                "confidence": raw_conn.get("confidence", "medium"),
                "source": source.model_dump(mode="json"),
            })

        # Build bindings
        bindings = []
        for raw_bind in raw.get("bindings", []):
            bindings.append({
                "id": _id("bind"),
                "scope_id": scope_id,
                "name": raw_bind.get("name", ""),
                "writes_to": raw_bind.get("writes_to", ""),
                "writes_to_type": raw_bind.get("writes_to_type", "external_system"),
                "governed_by_policy_ids": [],
                "description": raw_bind.get("description", ""),
                "confidence": raw_bind.get("confidence", "medium"),
                "source": source.model_dump(mode="json"),
            })

        return StructuredPrimitives(
            scope_id=scope_id,
            archetypes=archetypes,
            domains=domains,
            capabilities=capabilities,
            policies=policies,
            connectors=connectors,
            bindings=bindings,
        )
