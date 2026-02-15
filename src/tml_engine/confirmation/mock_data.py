"""Mock data for testing the confirmation TUI.

Generates a realistic Declaration based on a logistics operations manager
at a freight brokerage — a domain where tacit expertise is high-value.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tml_engine.models.identity import (
    ExtractionSource,
    HumanIdentity,
)
from tml_engine.models.primitives import (
    Archetype,
    Binding,
    Capability,
    Connector,
    DecisionFactor,
    Domain,
    ExceptionRule,
    Policy,
    ProvenanceEntry,
    Scope,
    SkillReference,
    View,
)

_NOW = datetime.now(UTC)

MOCK_IDENTITY = HumanIdentity(
    email="michael@conversion.com",
    display_name="Michael Chen",
    title="VP of Operations",
    department="Operations",
)

_SOURCE = ExtractionSource(
    source_type="web",
    source_identifier="https://conversion.com",
    extracted_at=_NOW,
)


def build_mock_scope() -> Scope:
    return Scope(
        id="scope-ops-001",
        name="Conversion Operations",
        description=(
            "The operational domain for Conversion's logistics brokerage, "
            "covering carrier evaluation, load matching, risk assessment, "
            "and client relationship management."
        ),
        owner_identity=MOCK_IDENTITY,
        source=_SOURCE,
    )


def build_mock_archetype() -> Archetype:
    return Archetype(
        id="arch-001",
        scope_id="scope-ops-001",
        identity=MOCK_IDENTITY,
        role_name="VP of Operations",
        role_description=(
            "Oversees all operational functions of the freight brokerage. "
            "Responsible for carrier relationships, load optimization, risk management, "
            "and ensuring service quality across all client accounts."
        ),
        primary_responsibilities=[
            "Evaluate and onboard new carriers",
            "Manage carrier performance and compliance",
            "Optimize load-to-carrier matching for margin and reliability",
            "Assess and mitigate operational risk on high-value shipments",
            "Maintain client satisfaction and escalation resolution",
        ],
        decision_authority=[
            "Approve or reject carrier partnerships",
            "Set pricing tiers for carrier lanes",
            "Override automated load matching when conditions warrant",
            "Authorize exception handling on distressed loads",
        ],
        accountability_boundaries=[
            "Does not set company-wide financial policy",
            "Does not negotiate client contracts (sales team owns this)",
            "Does not manage technology platform development",
        ],
        source=_SOURCE,
    )


def build_mock_domains() -> list[Domain]:
    return [
        Domain(
            id="dom-carrier-eval",
            scope_id="scope-ops-001",
            name="Carrier Evaluation",
            description="Assessing carriers for safety, reliability, and suitability for the network.",
            outcome_definition="Every carrier in the network meets safety and performance standards.",
            accountable_archetype_id="arch-001",
            source=_SOURCE,
        ),
        Domain(
            id="dom-load-matching",
            scope_id="scope-ops-001",
            name="Load Matching",
            description="Matching available loads to carriers based on capability, lane, and margin.",
            outcome_definition="Loads are matched to the best available carrier within margin targets.",
            accountable_archetype_id="arch-001",
            source=_SOURCE,
        ),
        Domain(
            id="dom-risk-mgmt",
            scope_id="scope-ops-001",
            name="Risk Management",
            description="Identifying and mitigating operational risks on shipments.",
            outcome_definition="High-value and sensitive shipments are protected from foreseeable risks.",
            accountable_archetype_id="arch-001",
            source=_SOURCE,
        ),
    ]


def build_mock_capabilities() -> list[Capability]:
    return [
        Capability(
            id="cap-carrier-safety",
            scope_id="scope-ops-001",
            domain_id="dom-carrier-eval",
            name="Carrier Safety Assessment",
            description="Evaluate a carrier's safety record and determine fitness for the network.",
            outcome="A clear accept/reject/conditional decision on carrier safety fitness.",
            decision_factors=[
                DecisionFactor(
                    name="CSA BASIC Scores",
                    description="FMCSA Compliance, Safety, Accountability scores across all categories.",
                    weight="primary",
                ),
                DecisionFactor(
                    name="Insurance Coverage",
                    description="Minimum $1M liability, cargo insurance matching load values.",
                    weight="primary",
                ),
                DecisionFactor(
                    name="Fleet Age",
                    description="Average age of tractors and trailers in the carrier's fleet.",
                    weight="secondary",
                ),
                DecisionFactor(
                    name="Out-of-Service Rate",
                    description="Percentage of inspections resulting in out-of-service orders.",
                    weight="primary",
                ),
            ],
            heuristics=[
                "If CSA scores are all green, fast-track approval",
                "Any alert in Unsafe Driving or HOS Compliance is an automatic deep review",
                "Fleet age over 10 years triggers maintenance record request",
            ],
            anti_patterns=[
                "Approving a carrier based solely on low rate without checking safety",
                "Ignoring a single bad BASIC score because others are clean",
                "Skipping insurance verification for repeat carriers",
            ],
            exceptions=[
                ExceptionRule(
                    trigger="Carrier is the only option for a time-critical load in a remote lane",
                    override_description="May approve conditionally with enhanced monitoring and reduced load value cap",
                    reason="Service failure cost exceeds marginal safety risk when monitoring is active",
                ),
            ],
            skills=[
                SkillReference(
                    id="skill-fmcsa-lookup",
                    name="FMCSA Carrier Lookup",
                    description="Query FMCSA SAFER system for carrier safety data.",
                    skill_type="tool",
                    execution_surface="FMCSA SAFER Web",
                ),
                SkillReference(
                    id="skill-insurance-verify",
                    name="Insurance Verification",
                    description="Verify carrier insurance certificates and coverage limits.",
                    skill_type="process",
                ),
            ],
            source=_SOURCE,
        ),
        Capability(
            id="cap-load-optimization",
            scope_id="scope-ops-001",
            domain_id="dom-load-matching",
            name="Load-to-Carrier Optimization",
            description="Match available loads to the best carrier considering margin, reliability, and lane fit.",
            outcome="Each load is assigned to a carrier that maximizes the balance of margin and service quality.",
            decision_factors=[
                DecisionFactor(
                    name="Lane History",
                    description="Carrier's track record on this specific origin-destination pair.",
                    weight="primary",
                ),
                DecisionFactor(
                    name="Rate Competitiveness",
                    description="Carrier's rate relative to market and target margin.",
                    weight="primary",
                ),
                DecisionFactor(
                    name="On-Time Performance",
                    description="Historical on-time delivery percentage for this carrier.",
                    weight="secondary",
                ),
            ],
            heuristics=[
                "Preferred carriers with 95%+ on-time get first right of refusal",
                "Never chase lowest rate at the expense of a known-reliable carrier",
                "For new lanes, start with the carrier who has the closest lane match",
            ],
            anti_patterns=[
                "Always choosing the cheapest carrier regardless of reliability",
                "Ignoring carrier capacity constraints on high-volume days",
            ],
            exceptions=[
                ExceptionRule(
                    trigger="Client explicitly requests a specific carrier",
                    override_description="Honor the request if carrier meets safety minimums, regardless of optimization score",
                    reason="Client relationship and contractual obligations take precedence",
                ),
            ],
            skills=[
                SkillReference(
                    id="skill-tms-search",
                    name="TMS Carrier Search",
                    description="Search the TMS for available carriers by lane and equipment.",
                    skill_type="tool",
                    execution_surface="Transportation Management System",
                ),
            ],
            source=_SOURCE,
        ),
        Capability(
            id="cap-risk-assessment",
            scope_id="scope-ops-001",
            domain_id="dom-risk-mgmt",
            name="Shipment Risk Assessment",
            description="Evaluate operational risk factors for a specific shipment and determine mitigation strategy.",
            outcome="A risk score and mitigation plan for the shipment.",
            decision_factors=[
                DecisionFactor(
                    name="Load Value",
                    description="Dollar value of the freight being shipped.",
                    weight="primary",
                ),
                DecisionFactor(
                    name="Weather and Road Conditions",
                    description="Current and forecasted conditions along the route.",
                    weight="secondary",
                ),
                DecisionFactor(
                    name="Carrier Reliability Score",
                    description="Composite score based on historical performance with this carrier.",
                    weight="primary",
                ),
            ],
            heuristics=[
                "Loads over $500K always get manual review regardless of carrier score",
                "Winter routes through mountain passes get automatic weather monitoring",
                "New carriers on their first 5 loads get enhanced tracking",
            ],
            anti_patterns=[
                "Treating all loads as equal risk because they have insurance",
                "Skipping risk assessment on repeat lanes because nothing bad happened before",
            ],
            exceptions=[],
            skills=[
                SkillReference(
                    id="skill-weather-check",
                    name="Route Weather Check",
                    description="Check weather conditions along a shipment route.",
                    skill_type="tool",
                    execution_surface="Weather API",
                ),
            ],
            source=_SOURCE,
        ),
    ]


def build_mock_policies() -> list[Policy]:
    return [
        Policy(
            id="pol-safety-floor",
            scope_id="scope-ops-001",
            name="Carrier Safety Floor",
            description="No carrier with an active conditional or unsatisfactory FMCSA rating may be used.",
            rule="Reject any carrier whose FMCSA rating is Conditional or Unsatisfactory.",
            attaches_to=["cap-carrier-safety"],
            enforcement_level="hard",
            source=_SOURCE,
        ),
        Policy(
            id="pol-insurance-minimum",
            scope_id="scope-ops-001",
            name="Insurance Minimum",
            description="All carriers must carry at least $1M in liability and cargo coverage matching load value.",
            rule="Carrier liability insurance must be at least $1M. Cargo insurance must meet or exceed the declared load value.",
            attaches_to=["cap-carrier-safety", "cap-risk-assessment"],
            enforcement_level="hard",
            source=_SOURCE,
        ),
        Policy(
            id="pol-margin-target",
            scope_id="scope-ops-001",
            name="Margin Target",
            description="Load matching should target a minimum 12% gross margin.",
            rule="Target 12% gross margin on all loads. Below 8% requires VP approval.",
            attaches_to=["cap-load-optimization"],
            enforcement_level="soft",
            source=_SOURCE,
        ),
    ]


def build_mock_connectors() -> list[Connector]:
    return [
        Connector(
            id="conn-sales-loads",
            scope_id="scope-ops-001",
            name="Sales → Load Queue",
            reads_from="Sales Team Load Submissions",
            reads_from_type="external_system",
            governed_by_policy_ids=["pol-margin-target"],
            description="Incoming load requests from the sales team flow into the operations queue for matching.",
            source=_SOURCE,
        ),
        Connector(
            id="conn-fmcsa-data",
            scope_id="scope-ops-001",
            name="FMCSA → Carrier Evaluation",
            reads_from="FMCSA SAFER System",
            reads_from_type="external_system",
            governed_by_policy_ids=["pol-safety-floor"],
            description="Carrier safety data is pulled from the FMCSA SAFER system during evaluation.",
            source=_SOURCE,
        ),
    ]


def build_mock_bindings() -> list[Binding]:
    return [
        Binding(
            id="bind-dispatch",
            scope_id="scope-ops-001",
            name="Load Match → Dispatch",
            writes_to="Dispatch Team",
            writes_to_type="external_system",
            governed_by_policy_ids=["pol-margin-target"],
            description="Once a load is matched to a carrier, the dispatch team receives the assignment for execution.",
            source=_SOURCE,
        ),
        Binding(
            id="bind-client-update",
            scope_id="scope-ops-001",
            name="Risk Assessment → Client Update",
            writes_to="Client Account Manager",
            writes_to_type="external_system",
            governed_by_policy_ids=[],
            description="High-risk shipments trigger proactive client notifications with mitigation plans.",
            source=_SOURCE,
        ),
    ]


def build_mock_views() -> list[View]:
    return [
        View(
            id="view-confirmation",
            scope_id="scope-ops-001",
            name="Confirmation Surface",
            description="The primary view for confirming all extracted primitives.",
            capability_ids=["cap-carrier-safety", "cap-load-optimization", "cap-risk-assessment"],
            target_archetype_id="arch-001",
            projection_format="confirmation",
        ),
    ]


def build_mock_provenance() -> list[ProvenanceEntry]:
    return [
        ProvenanceEntry(
            id="prov-001",
            scope_id="scope-ops-001",
            primitive_id="scope-ops-001",
            primitive_type="scope",
            action="extracted",
            actor=MOCK_IDENTITY,
            timestamp=_NOW,
            details={"source": "web", "url": "https://conversion.com"},
        ),
    ]


def build_mock_declaration():
    """Build a complete mock Declaration with realistic logistics expertise data."""
    from tml_engine.models.declaration import Declaration

    return Declaration(
        id="decl-001",
        version="0.1.0",
        scope=build_mock_scope(),
        archetypes=[build_mock_archetype()],
        domains=build_mock_domains(),
        capabilities=build_mock_capabilities(),
        views=build_mock_views(),
        policies=build_mock_policies(),
        connectors=build_mock_connectors(),
        bindings=build_mock_bindings(),
        provenance=build_mock_provenance(),
        created_at=_NOW,
    )
