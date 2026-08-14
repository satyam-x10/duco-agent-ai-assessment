"""
Workflow definitions and state transition DAG for the DuCO-Agent Coordination of Benefits system.
"""

from .cob_orchestrator_workflow import (
    DUAL_COVERAGE_WORKFLOW_SPEC,
    WorkflowStepSpec,
    WorkflowTransition,
    DualCoverageWorkflowGraph,
    get_dual_coverage_workflow,
)
from .state_graph import (
    WorkflowNode,
    WorkflowEdge,
    WorkflowDAG,
    WorkflowExecutionPlan,
    build_coordination_dag,
)

__all__ = [
    "DUAL_COVERAGE_WORKFLOW_SPEC",
    "WorkflowStepSpec",
    "WorkflowTransition",
    "DualCoverageWorkflowGraph",
    "get_dual_coverage_workflow",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowDAG",
    "WorkflowExecutionPlan",
    "build_coordination_dag",
]
