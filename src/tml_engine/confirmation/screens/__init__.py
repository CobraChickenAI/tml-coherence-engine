"""Confirmation screens — each screen is a View projection."""

from tml_engine.confirmation.screens.archetype import ArchetypeScreen
from tml_engine.confirmation.screens.capabilities import CapabilitiesScreen
from tml_engine.confirmation.screens.domains import DomainsScreen
from tml_engine.confirmation.screens.edges import EdgesScreen
from tml_engine.confirmation.screens.flows import FlowsScreen
from tml_engine.confirmation.screens.policies import PoliciesScreen
from tml_engine.confirmation.screens.skills import SkillsScreen
from tml_engine.confirmation.screens.summary import SummaryScreen
from tml_engine.confirmation.screens.welcome import WelcomeScreen

__all__ = [
    "ArchetypeScreen",
    "CapabilitiesScreen",
    "DomainsScreen",
    "EdgesScreen",
    "FlowsScreen",
    "PoliciesScreen",
    "SkillsScreen",
    "SummaryScreen",
    "WelcomeScreen",
]
