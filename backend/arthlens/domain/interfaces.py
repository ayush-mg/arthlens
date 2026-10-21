"""
Core Abstract Interfaces for ArthLens.

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 5.1, 5.2).
Phase: P1-2 (Domain Classes, Enums, and Interfaces).

Follows GoF patterns identified in Section 5.2:
- Adapter: DataProvider
- Strategy: DemandAllocator, SimulationModel
- Composite & Visitor: RuleNode, RuleVisitor
- Specification: VerificationSpecification
- Template Method + Command: Tool
- State: RunState
- Repository: Repository
- Gateway / Client: ILLMClient
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Union

if TYPE_CHECKING:
    from pydantic import BaseModel


class DataProvider(ABC):
    """
    Abstract adapter target for external and local data sources (Adapter pattern).

    Handbook Reference: Section 5.1.
    Concrete implementations wrap OGD (data.gov.in), RBI DBIE, SHRUG, and OSM,
    insulating core engines with local test fixtures and cached snapshots.
    """

    @abstractmethod
    def fetch(self, query: "ProviderQuery") -> "Dataset":
        """
        Fetch data matching the query specification.

        Args:
            query: ProviderQuery containing dataset identifier, geo/temporal filters.

        Returns:
            Dataset: Normalized dataset instance with provenance metadata.
        """
        raise NotImplementedError


class DemandAllocator(ABC):
    """
    Abstract strategy for spatial demand allocation (Strategy pattern).

    Handbook Reference: Section 5.1, 6.3.
    Implementations (NearestFacilityAllocator, HuffAllocator) satisfy identical
    conservation and contract properties.
    """

    @abstractmethod
    def allocate(self, zones, facilities, params) -> "Allocation":
        """
        Allocate demand from zones to facilities.

        Args:
            zones: Demand zones with populations and baseline demands.
            facilities: Competing and candidate commercial facilities.
            params: Model parameters (e.g., distance decay exponent lambda).

        Returns:
            Allocation: Allocation matrix and facility demand totals.
        """
        raise NotImplementedError


class SimulationModel(ABC):
    """
    Abstract strategy for financial and risk simulations (Strategy pattern).

    Handbook Reference: Section 5.1, 6.4, 6.6.
    Every implementation honours Liskov substitution for reproducibility,
    conservation, and output typing.
    """

    @abstractmethod
    def run(self, scenario: "Scenario", seed: int) -> "RunResult":
        """
        Execute simulation run for a scenario with a random seed.

        Args:
            scenario: Business scenario parameters and input ledger quantities.
            seed: Integer random seed for bit-identical reproducibility (no default).

        Returns:
            RunResult: Simulation outputs (e.g., cash flow, risk quantiles).
        """
        raise NotImplementedError


class RuleNode(ABC):
    """
    Abstract composite node for policy rule ASTs (Composite pattern).

    Handbook Reference: Section 5.1, 6.8.
    Nodes form an expression tree of boolean / Kleene logic (AndNode, OrNode,
    NotNode, LeafPredicate).
    """

    @abstractmethod
    def accept(self, visitor: "RuleVisitor"):
        """
        Accept a RuleVisitor to traverse or evaluate the rule tree.

        Args:
            visitor: Concrete RuleVisitor instance.
        """
        raise NotImplementedError


class RuleVisitor(ABC):
    """
    Abstract visitor operating over a RuleNode tree (Visitor pattern).

    Handbook Reference: Section 5.1, 6.8.
    Subclasses: EligibilityEvaluator (Kleene three-valued logic),
    PolicyDiff, FinancialImpactExtractor.
    Note: Base class declares no abstract methods per Handbook 5.1 skeleton;
    concrete visitors implement node-specific visit methods (e.g., visit_leaf).
    """
    pass


class VerificationSpecification(ABC):
    """
    Abstract specification for evidence gating (Specification pattern).

    Handbook Reference: Section 4.5, 5.1.
    Nine independent specifications (V1-V9) compose into an AndSpecification
    chain inside the LedgerVerifier to gate published claims.
    """

    @abstractmethod
    def check(self, claim, ledger) -> "SpecResult":
        """
        Verify claim against the epistemic ledger state.

        Args:
            claim: Candidate report claim, scenario output, or quantity.
            ledger: Active Epistemic Ledger instance.

        Returns:
            SpecResult: Pass/fail status, offending quantity ID, and human-readable reason.
        """
        raise NotImplementedError


class Tool(ABC):
    """
    Abstract command with a template method skeleton (Command + Template Method pattern).

    Handbook Reference: Section 5.1, 8.5.
    Subclasses cannot bypass preconditions or postconditions; the template method
    enforces: validate_input -> check_preconditions -> run_core -> verify_postconditions.
    """

    def execute(self, raw_input):
        """
        Template method orchestrating uniform tool execution.

        Args:
            raw_input: Unvalidated input dictionary or parameters.

        Returns:
            Any: Validated and verified tool outputs registered in the ledger.
        """
        inp = self.validate_input(raw_input)
        self.check_preconditions(inp)
        out = self.run_core(inp)
        self.verify_postconditions(out)  # registers outputs in the ledger
        return out

    @abstractmethod
    def validate_input(self, raw_input):
        """Validate raw input parameters against the tool's schema."""
        raise NotImplementedError

    @abstractmethod
    def check_preconditions(self, inp):
        """Verify preconditions required before executing the core tool logic."""
        raise NotImplementedError

    @abstractmethod
    def run_core(self, inp):
        """Execute the primary deterministic computation or query."""
        raise NotImplementedError

    @abstractmethod
    def verify_postconditions(self, out):
        """Verify postconditions and register output quantities into the ledger."""
        raise NotImplementedError


class ILLMClient(ABC):
    """
    Abstract client interface for LLM access with structured outputs (Adapter/Gateway).

    Handbook Reference: Section 5.1, 8.6.
    Insulates core application from third-party provider SDKs.
    Implementations include real provider routers, FakeLLMClient, and ReplayLLMClient.
    """

    @abstractmethod
    def generate_structured(self, prompt, schema, task_type) -> "BaseModel":
        """
        Generate structured JSON adhering to the provided schema.

        Args:
            prompt: Text prompt with untrusted data blocks safely delimited.
            schema: Pydantic model class or JSON schema defining expected output.
            task_type: Classification string (e.g. goal_interpretation, planning).

        Returns:
            BaseModel: Structured validated instance adhering to schema.
        """
        raise NotImplementedError


class RunState(ABC):
    """
    Abstract state in the agent run lifecycle (State pattern).

    Handbook Reference: Section 5.1, 8.2.
    Subclasses govern valid transitions between the 13 defined agent states.
    Illegal transitions raise domain exceptions.
    """

    @abstractmethod
    def handle(self, run: "AgentRun", event) -> "RunState":
        """
        Handle an incoming event within the current state context.

        Args:
            run: Active AgentRun instance.
            event: Event object triggering the transition.

        Returns:
            RunState: Next valid RunState.
        """
        raise NotImplementedError


class Repository(ABC):
    """
    Abstract persistence repository for domain aggregates (Repository pattern).

    Handbook Reference: Section 5.1, 9.1.
    Provides persistence abstraction (one per aggregate root) enabling
    in-memory fakes for offline unit/contract tests and SQLAlchemy implementations for Postgres.
    Note: Skeletons in Handbook 5.1 declare no abstract methods (pass); specific
    crud/retrieval methods are introduced per aggregate in P1-5.
    """
    pass
