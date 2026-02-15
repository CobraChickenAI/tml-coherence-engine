"""Tests for mock data generation and assertion generation functions."""

from __future__ import annotations

from tml_engine.confirmation.mock_data import (
    build_mock_archetype,
    build_mock_bindings,
    build_mock_capabilities,
    build_mock_connectors,
    build_mock_declaration,
    build_mock_domains,
    build_mock_policies,
    build_mock_provenance,
    build_mock_scope,
    build_mock_views,
)
from tml_engine.confirmation.screens.archetype import _archetype_assertions
from tml_engine.confirmation.screens.capabilities import _capability_assertions
from tml_engine.confirmation.screens.domains import _domain_assertions
from tml_engine.confirmation.screens.edges import _exception_assertions
from tml_engine.confirmation.screens.flows import _flow_assertions
from tml_engine.confirmation.screens.policies import _policy_assertions
from tml_engine.confirmation.screens.skills import _skill_assertions


class TestMockData:
    def test_build_scope(self) -> None:
        scope = build_mock_scope()
        assert scope.id == "scope-ops-001"
        assert scope.owner_identity.email == "michael@conversion.com"

    def test_build_archetype(self) -> None:
        arch = build_mock_archetype()
        assert arch.role_name == "VP of Operations"
        assert len(arch.primary_responsibilities) == 5
        assert len(arch.decision_authority) == 4
        assert len(arch.accountability_boundaries) == 3

    def test_build_domains(self) -> None:
        domains = build_mock_domains()
        assert len(domains) == 3
        assert domains[0].name == "Carrier Evaluation"

    def test_build_capabilities(self) -> None:
        caps = build_mock_capabilities()
        assert len(caps) == 3
        # First capability has 4 decision factors, 3 heuristics, 3 anti-patterns
        assert len(caps[0].decision_factors) == 4
        assert len(caps[0].heuristics) == 3
        assert len(caps[0].anti_patterns) == 3
        assert len(caps[0].exceptions) == 1
        assert len(caps[0].skills) == 2

    def test_build_policies(self) -> None:
        policies = build_mock_policies()
        assert len(policies) == 3
        assert policies[0].enforcement_level == "hard"
        assert policies[2].enforcement_level == "soft"

    def test_build_connectors(self) -> None:
        connectors = build_mock_connectors()
        assert len(connectors) == 2

    def test_build_bindings(self) -> None:
        bindings = build_mock_bindings()
        assert len(bindings) == 2

    def test_build_views(self) -> None:
        views = build_mock_views()
        assert len(views) == 1
        assert views[0].projection_format == "confirmation"

    def test_build_provenance(self) -> None:
        prov = build_mock_provenance()
        assert len(prov) == 1
        assert prov[0].action == "extracted"

    def test_build_declaration(self) -> None:
        decl = build_mock_declaration()
        assert decl.id == "decl-001"
        assert len(decl.archetypes) == 1
        assert len(decl.domains) == 3
        assert len(decl.capabilities) == 3
        assert decl.compute_completion() == 0.0  # Nothing confirmed yet

    def test_declaration_serialization_round_trip(self) -> None:
        decl = build_mock_declaration()
        json_str = decl.model_dump_json()
        from tml_engine.models.declaration import Declaration

        restored = Declaration.model_validate_json(json_str)
        assert restored.id == decl.id
        assert len(restored.capabilities) == len(decl.capabilities)


class TestAssertionGeneration:
    def test_archetype_assertions(self) -> None:
        arch = build_mock_archetype()
        assertions = _archetype_assertions(arch)
        # 1 role + 5 responsibilities + 4 authorities + 3 boundaries = 13
        assert len(assertions) == 13
        assert "VP of Operations" in assertions[0]["text"]
        assert assertions[0]["field"] == "role"

    def test_domain_assertions(self) -> None:
        domains = build_mock_domains()
        assertions = _domain_assertions(domains)
        assert len(assertions) == 3
        assert "Carrier Evaluation" in assertions[0]["text"]
        assert "Success looks like:" in assertions[0]["text"]

    def test_capability_assertions(self) -> None:
        caps = build_mock_capabilities()
        assertions = _capability_assertions(caps)
        # Cap 1: 1 desc + 4 factors + 3 heuristics + 3 anti = 11
        # Cap 2: 1 desc + 3 factors + 3 heuristics + 2 anti = 9
        # Cap 3: 1 desc + 3 factors + 3 heuristics + 2 anti = 9
        assert len(assertions) == 29

    def test_skill_assertions(self) -> None:
        caps = build_mock_capabilities()
        assertions = _skill_assertions(caps)
        # Cap 1: 2 skills, Cap 2: 1 skill, Cap 3: 1 skill = 4
        assert len(assertions) == 4
        assert "FMCSA Carrier Lookup" in assertions[0]["text"]

    def test_policy_assertions(self) -> None:
        policies = build_mock_policies()
        assertions = _policy_assertions(policies)
        assert len(assertions) == 3
        assert "never be broken" in assertions[0]["text"]  # hard enforcement
        assert "overridden" in assertions[2]["text"]  # soft enforcement

    def test_exception_assertions(self) -> None:
        caps = build_mock_capabilities()
        assertions = _exception_assertions(caps)
        # Cap 1: 1 exception, Cap 2: 1 exception, Cap 3: 0 exceptions = 2
        assert len(assertions) == 2
        assert "Exception in" in assertions[0]["text"]

    def test_flow_assertions(self) -> None:
        connectors = build_mock_connectors()
        bindings = build_mock_bindings()
        assertions = _flow_assertions(connectors, bindings)
        assert len(assertions) == 4  # 2 connectors + 2 bindings
        assert "Input flow:" in assertions[0]["text"]
        assert "Output flow:" in assertions[2]["text"]


class TestWidgetImports:
    def test_assertion_widget_import(self) -> None:
        from tml_engine.confirmation.widgets.assertion import AssertionWidget
        assert AssertionWidget is not None

    def test_response_widget_import(self) -> None:
        from tml_engine.confirmation.widgets.response import ResponseWidget
        assert ResponseWidget is not None

    def test_editor_widget_import(self) -> None:
        from tml_engine.confirmation.widgets.editor import InlineEditorWidget
        assert InlineEditorWidget is not None

    def test_progress_widget_import(self) -> None:
        from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
        assert ProgressSpineWidget is not None


class TestScreenImports:
    def test_all_screens_import(self) -> None:
        from tml_engine.confirmation.screens import (
            ArchetypeScreen,
            CapabilitiesScreen,
            DomainsScreen,
            EdgesScreen,
            FlowsScreen,
            PoliciesScreen,
            SkillsScreen,
            SummaryScreen,
            WelcomeScreen,
        )
        assert all([
            WelcomeScreen, ArchetypeScreen, DomainsScreen,
            CapabilitiesScreen, SkillsScreen, PoliciesScreen,
            EdgesScreen, FlowsScreen, SummaryScreen,
        ])


class TestAppImport:
    def test_coherence_app_import(self) -> None:
        from tml_engine.confirmation.app import CoherenceApp
        assert CoherenceApp is not None

    def test_run_confirmation_import(self) -> None:
        from tml_engine.confirmation.app import run_confirmation
        assert callable(run_confirmation)
