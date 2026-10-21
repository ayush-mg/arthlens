"""
Contract-test suite for domain enums and core abstract interfaces.

Authoritative Specification: ArthLens Build Handbook v1.0 (Parts 4, 5.1, 5.2).
Task: P1-2 (Domain Classes, Enums, and Interfaces).
Acceptance Criterion: "Contract-test skeletons exist."
"""

import inspect
import pytest

from backend.arthlens.domain.enums import (
    EvidenceFloor,
    EvidenceLevel,
    Kind,
    ResolutionLevel,
    ResolutionTier,
)
from backend.arthlens.domain.interfaces import (
    DataProvider,
    DemandAllocator,
    ILLMClient,
    Repository,
    RuleNode,
    RuleVisitor,
    RunState,
    SimulationModel,
    Tool,
    VerificationSpecification,
)


# ==============================================================================
# 1. ENUM CONTRACT TESTS
# ==============================================================================

@pytest.mark.contract
class TestKindEnumContract:
    """Verify Kind enum members, values, and string serialization (Handbook 4.1, 5.1)."""

    def test_kind_contains_exact_seven_members(self):
        """Kind must declare exactly the seven core MVP values from Handbook Section 4.1."""
        expected_members = {
            "OBSERVED",
            "POLICY_RULE",
            "USER_ASSUMED",
            "ESTIMATED",
            "SCENARIO",
            "CALCULATED",
            "SIMULATED",
        }
        actual_members = {member.name for member in Kind}
        assert actual_members == expected_members, (
            f"Kind members drift. Expected: {expected_members}, got: {actual_members}"
        )

    def test_kind_serialized_values(self):
        """Kind string values must equal their uppercase member names."""
        for member in Kind:
            assert member.value == member.name
            assert str(member) == f"Kind.{member.name}" or str(member.value) == member.name


@pytest.mark.contract
class TestEvidenceLevelContract:
    """Verify EvidenceLevel ranking and aliases (Handbook 4.2)."""

    def test_evidence_level_values(self):
        """
        Base classes ranked by strength (Handbook 4.2):
        OBSERVED = POLICY_RULE (4) > USER_ASSUMED (3) > ESTIMATED (2) > SCENARIO (1).
        """
        assert EvidenceLevel.SCENARIO == 1
        assert EvidenceLevel.ESTIMATED == 2
        assert EvidenceLevel.USER_ASSUMED == 3
        assert EvidenceLevel.POLICY_RULE == 4
        assert EvidenceLevel.OBSERVED == 4

    def test_evidence_level_ordering(self):
        """Verify strict inequality ordering for evidence floor combination."""
        assert EvidenceLevel.SCENARIO < EvidenceLevel.ESTIMATED
        assert EvidenceLevel.ESTIMATED < EvidenceLevel.USER_ASSUMED
        assert EvidenceLevel.USER_ASSUMED < EvidenceLevel.POLICY_RULE
        assert EvidenceLevel.POLICY_RULE == EvidenceLevel.OBSERVED

    def test_evidence_floor_alias(self):
        """EvidenceFloor must be an exact alias of EvidenceLevel."""
        assert EvidenceFloor is EvidenceLevel


@pytest.mark.contract
class TestResolutionTierContract:
    """Verify ResolutionTier levels and aliases (Handbook 4.3)."""

    def test_resolution_tier_values(self):
        """
        Coarse to fine order (Handbook 4.3):
        NATION(0) < STATE(1) < DISTRICT(2) < SUBDISTRICT(3) < VILLAGE_URBAN(4) < POINT(5).
        """
        assert ResolutionTier.NATION == 0
        assert ResolutionTier.STATE == 1
        assert ResolutionTier.DISTRICT == 2
        assert ResolutionTier.SUBDISTRICT == 3
        assert ResolutionTier.VILLAGE_URBAN == 4
        assert ResolutionTier.POINT == 5

    def test_resolution_tier_ordering(self):
        """Verify coarseness/fineness comparison semantics."""
        assert ResolutionTier.NATION < ResolutionTier.STATE
        assert ResolutionTier.STATE < ResolutionTier.DISTRICT
        assert ResolutionTier.DISTRICT < ResolutionTier.SUBDISTRICT
        assert ResolutionTier.SUBDISTRICT < ResolutionTier.VILLAGE_URBAN
        assert ResolutionTier.VILLAGE_URBAN < ResolutionTier.POINT

    def test_resolution_level_alias(self):
        """ResolutionLevel must be an exact alias of ResolutionTier."""
        assert ResolutionLevel is ResolutionTier


# ==============================================================================
# 2. ABSTRACT INTERFACE CONTRACT TESTS
# ==============================================================================

@pytest.mark.contract
class TestDataProviderInterfaceContract:
    """Contract tests for DataProvider adapter target (Handbook 5.1)."""

    def test_cannot_instantiate_abstract(self):
        """DataProvider cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DataProvider()

    def test_abstract_methods_defined(self):
        """fetch must be an abstract method."""
        assert "fetch" in DataProvider.__abstractmethods__

    def test_fetch_signature_and_annotations(self):
        """fetch signature must accept (self, query: 'ProviderQuery') -> 'Dataset'."""
        sig = inspect.signature(DataProvider.fetch)
        params = list(sig.parameters.keys())
        assert params == ["self", "query"]
        assert sig.parameters["query"].annotation in ("ProviderQuery", "'ProviderQuery'")
        assert sig.return_annotation in ("Dataset", "'Dataset'")

    def test_concrete_implementation_substitutability(self):
        """A concrete provider implementing fetch can be instantiated."""
        class StubProvider(DataProvider):
            def fetch(self, query):
                return {"stub": "data"}

        provider = StubProvider()
        assert provider.fetch("query_spec") == {"stub": "data"}


@pytest.mark.contract
class TestDemandAllocatorInterfaceContract:
    """Contract tests for DemandAllocator strategy (Handbook 5.1, 6.3)."""

    def test_cannot_instantiate_abstract(self):
        """DemandAllocator cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DemandAllocator()

    def test_abstract_methods_defined(self):
        """allocate must be an abstract method."""
        assert "allocate" in DemandAllocator.__abstractmethods__

    def test_allocate_signature_and_annotations(self):
        """allocate signature must accept (self, zones, facilities, params) -> 'Allocation'."""
        sig = inspect.signature(DemandAllocator.allocate)
        params = list(sig.parameters.keys())
        assert params == ["self", "zones", "facilities", "params"]
        assert sig.return_annotation in ("Allocation", "'Allocation'")

    def test_concrete_implementation_substitutability(self):
        """A concrete allocator implementing allocate can be instantiated."""
        class StubAllocator(DemandAllocator):
            def allocate(self, zones, facilities, params):
                return {"allocated": True}

        allocator = StubAllocator()
        assert allocator.allocate([], [], {}) == {"allocated": True}


@pytest.mark.contract
class TestSimulationModelInterfaceContract:
    """Contract tests for SimulationModel strategy (Handbook 5.1, 6.4, 6.6)."""

    def test_cannot_instantiate_abstract(self):
        """SimulationModel cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SimulationModel()

    def test_abstract_methods_defined(self):
        """run must be an abstract method."""
        assert "run" in SimulationModel.__abstractmethods__

    def test_run_signature_and_annotations(self):
        """run signature must accept (self, scenario: 'Scenario', seed: int) -> 'RunResult' with no default seed."""
        sig = inspect.signature(SimulationModel.run)
        params = list(sig.parameters.keys())
        assert params == ["self", "scenario", "seed"]
        assert sig.parameters["scenario"].annotation in ("Scenario", "'Scenario'")
        assert sig.parameters["seed"].annotation is int
        assert sig.parameters["seed"].default is inspect.Parameter.empty, "seed must not have a default value"
        assert sig.return_annotation in ("RunResult", "'RunResult'")

    def test_concrete_implementation_substitutability(self):
        """A concrete simulation model implementing run can be instantiated."""
        class StubSimulation(SimulationModel):
            def run(self, scenario, seed):
                return {"seed": seed, "result": "run"}

        model = StubSimulation()
        assert model.run(None, 42) == {"seed": 42, "result": "run"}



@pytest.mark.contract
class TestRuleNodeAndVisitorInterfaceContract:
    """Contract tests for RuleNode Composite and RuleVisitor Visitor (Handbook 5.1, 6.8)."""

    def test_cannot_instantiate_rule_node_abstract(self):
        """RuleNode cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            RuleNode()

    def test_rule_node_abstract_methods(self):
        """accept must be an abstract method of RuleNode."""
        assert "accept" in RuleNode.__abstractmethods__

    def test_accept_signature_and_annotations(self):
        """accept signature must accept (self, visitor: 'RuleVisitor')."""
        sig = inspect.signature(RuleNode.accept)
        params = list(sig.parameters.keys())
        assert params == ["self", "visitor"]
        assert sig.parameters["visitor"].annotation in ("RuleVisitor", "'RuleVisitor'")

    def test_rule_visitor_has_no_abstract_methods(self):
        """RuleVisitor base class declares no abstract methods per Handbook 5.1 skeleton."""
        abstract_methods = getattr(RuleVisitor, "__abstractmethods__", frozenset())
        assert len(abstract_methods) == 0, f"RuleVisitor should have no abstract methods, found: {abstract_methods}"

    def test_rule_visitor_subclassing_and_dispatch(self):
        """RuleNode and RuleVisitor coordinate via double dispatch."""
        class ConcreteVisitor(RuleVisitor):
            def visit_leaf(self, leaf):
                return f"visited_{leaf.name}"

        class ConcreteLeaf(RuleNode):
            def __init__(self, name):
                self.name = name

            def accept(self, visitor):
                return visitor.visit_leaf(self)

        node = ConcreteLeaf("test_rule")
        visitor = ConcreteVisitor()
        assert node.accept(visitor) == "visited_test_rule"


@pytest.mark.contract
class TestVerificationSpecificationInterfaceContract:
    """Contract tests for VerificationSpecification (Handbook 4.5, 5.1)."""

    def test_cannot_instantiate_abstract(self):
        """VerificationSpecification cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            VerificationSpecification()

    def test_abstract_methods_defined(self):
        """check must be an abstract method."""
        assert "check" in VerificationSpecification.__abstractmethods__

    def test_check_signature_and_annotations(self):
        """check signature must accept (self, claim, ledger) -> 'SpecResult'."""
        sig = inspect.signature(VerificationSpecification.check)
        params = list(sig.parameters.keys())
        assert params == ["self", "claim", "ledger"]
        assert sig.return_annotation in ("SpecResult", "'SpecResult'")

    def test_concrete_implementation_substitutability(self):
        """A concrete specification implementing check can be instantiated."""
        class StubSpec(VerificationSpecification):
            def check(self, claim, ledger):
                return {"passed": True, "claim": claim}

        spec = StubSpec()
        assert spec.check("c1", None) == {"passed": True, "claim": "c1"}


@pytest.mark.contract
class TestToolTemplateMethodContract:
    """Contract tests for Tool Template Method + Command pattern (Handbook 5.1, 8.5)."""

    def test_cannot_instantiate_abstract(self):
        """Tool cannot be directly instantiated without implementing the 4 phases."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Tool()

    def test_tool_abstract_methods(self):
        """The four execution phases must all be abstract methods."""
        expected = {"validate_input", "check_preconditions", "run_core", "verify_postconditions"}
        assert expected.issubset(Tool.__abstractmethods__)

    def test_execute_method_order_of_execution(self):
        """
        execute() must orchestrate the four phases in exact order:
        validate_input -> check_preconditions -> run_core -> verify_postconditions.
        """
        call_log = []

        class ConcreteTool(Tool):
            def validate_input(self, raw_input):
                call_log.append("validate_input")
                return {"valid": raw_input}

            def check_preconditions(self, inp):
                call_log.append("check_preconditions")

            def run_core(self, inp):
                call_log.append("run_core")
                return {"result": 100}

            def verify_postconditions(self, out):
                call_log.append("verify_postconditions")

        tool = ConcreteTool()
        result = tool.execute("raw")

        assert call_log == [
            "validate_input",
            "check_preconditions",
            "run_core",
            "verify_postconditions",
        ], f"Incorrect phase order: {call_log}"
        assert result == {"result": 100}

    def test_execute_aborts_on_precondition_failure(self):
        """If check_preconditions fails, run_core and verify_postconditions must not execute."""
        call_log = []

        class FailingPreconditionTool(Tool):
            def validate_input(self, raw_input):
                call_log.append("validate_input")
                return raw_input

            def check_preconditions(self, inp):
                call_log.append("check_preconditions")
                raise ValueError("Precondition failed: missing data")

            def run_core(self, inp):
                call_log.append("run_core")
                return "output"

            def verify_postconditions(self, out):
                call_log.append("verify_postconditions")

        tool = FailingPreconditionTool()
        with pytest.raises(ValueError, match="Precondition failed"):
            tool.execute("input")

        assert call_log == ["validate_input", "check_preconditions"]


@pytest.mark.contract
class TestILLMClientInterfaceContract:
    """Contract tests for ILLMClient adapter (Handbook 5.1, 8.6)."""

    def test_cannot_instantiate_abstract(self):
        """ILLMClient cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ILLMClient()

    def test_abstract_methods_defined(self):
        """generate_structured must be an abstract method."""
        assert "generate_structured" in ILLMClient.__abstractmethods__

    def test_generate_structured_signature_and_annotations(self):
        """generate_structured signature must accept (self, prompt, schema, task_type) -> 'BaseModel'."""
        sig = inspect.signature(ILLMClient.generate_structured)
        params = list(sig.parameters.keys())
        assert params == ["self", "prompt", "schema", "task_type"]
        assert sig.return_annotation in ("BaseModel", "'BaseModel'")

    def test_concrete_implementation_substitutability(self):
        """A concrete LLM client implementing generate_structured can be instantiated."""
        class FakeClient(ILLMClient):
            def generate_structured(self, prompt, schema, task_type):
                return {"structured": True, "prompt": prompt}

        client = FakeClient()
        assert client.generate_structured("hello", None, "test") == {
            "structured": True,
            "prompt": "hello",
        }


@pytest.mark.contract
class TestRunStateInterfaceContract:
    """Contract tests for RunState State pattern (Handbook 5.1, 8.2)."""

    def test_cannot_instantiate_abstract(self):
        """RunState cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            RunState()

    def test_abstract_methods_defined(self):
        """handle must be an abstract method."""
        assert "handle" in RunState.__abstractmethods__

    def test_handle_signature_and_annotations(self):
        """handle signature must accept (self, run: 'AgentRun', event) -> 'RunState'."""
        sig = inspect.signature(RunState.handle)
        params = list(sig.parameters.keys())
        assert params == ["self", "run", "event"]
        assert sig.parameters["run"].annotation in ("AgentRun", "'AgentRun'")
        assert sig.return_annotation in ("RunState", "'RunState'")

    def test_concrete_implementation_substitutability(self):
        """A concrete RunState implementing handle can be instantiated."""
        class CreatedState(RunState):
            def handle(self, run, event):
                return self

        state = CreatedState()
        assert state.handle(None, "event") is state


@pytest.mark.contract
class TestRepositoryInterfaceContract:
    """Contract tests for Repository interface (Handbook 5.1, 9.1)."""

    def test_repository_is_abstract_base_class(self):
        """Repository must inherit from ABC."""
        assert issubclass(Repository, object)

    def test_repository_has_no_abstract_methods(self):
        """Repository base class declares no abstract methods per Handbook 5.1 skeleton."""
        abstract_methods = getattr(Repository, "__abstractmethods__", frozenset())
        assert len(abstract_methods) == 0, f"Repository should have no abstract methods in 5.1 skeleton, found: {abstract_methods}"

    def test_concrete_subclass_extensibility(self):
        """Concrete repositories can inherit from Repository."""
        class InfluxInMemoryRepository(Repository):
            def __init__(self):
                self._store = {}

            def get(self, id_):
                return self._store.get(id_)
        repo = InfluxInMemoryRepository()
        assert repo.get("id1") is None
