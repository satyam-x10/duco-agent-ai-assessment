"""
State transition Directed Acyclic Graph (DAG) and validation checkpoint model for DUCO multi-agent execution.
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field


@dataclass
class WorkflowEdge:
    source: str
    target: str
    condition: Optional[str] = None
    is_conditional: bool = False
    is_backtracking: bool = False


@dataclass
class WorkflowNode:
    name: str
    incoming_edges: List[WorkflowEdge] = field(default_factory=list)
    outgoing_edges: List[WorkflowEdge] = field(default_factory=list)


@dataclass
class WorkflowExecutionPlan:
    nodes_order: List[str]
    conditional_branches: Dict[str, List[str]]
    approval_gates: List[str]


class WorkflowDAG:
    """DAG structure representing agent dependency flows and backtracking cycles in DuCO-Agent."""

    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []

    def add_node(self, name: str) -> WorkflowNode:
        if name not in self.nodes:
            self.nodes[name] = WorkflowNode(name=name)
        return self.nodes[name]

    def add_edge(self, source: str, target: str, condition: Optional[str] = None, is_conditional: bool = False, is_backtracking: bool = False) -> None:
        src_node = self.add_node(source)
        tgt_node = self.add_node(target)
        edge = WorkflowEdge(source=source, target=target, condition=condition, is_conditional=is_conditional, is_backtracking=is_backtracking)
        self.edges.append(edge)
        src_node.outgoing_edges.append(edge)
        tgt_node.incoming_edges.append(edge)

    def get_forward_dependencies(self, node_name: str) -> List[str]:
        node = self.nodes.get(node_name)
        if not node:
            return []
        return [e.target for e in node.outgoing_edges if not e.is_backtracking]

    def get_backtrack_targets(self, node_name: str) -> List[str]:
        node = self.nodes.get(node_name)
        if not node:
            return []
        return [e.target for e in node.outgoing_edges if e.is_backtracking]


def build_coordination_dag() -> WorkflowDAG:
    """Builds the canonical coordination DAG for the 7 DuCO-Agent specialists."""
    dag = WorkflowDAG()
    
    # Forward pipeline edges
    dag.add_edge("IntakeAgent", "DocIntelAgent")
    dag.add_edge("DocIntelAgent", "MedicalCodingAgent")
    dag.add_edge("MedicalCodingAgent", "InsuranceAgent")
    dag.add_edge("InsuranceAgent", "COBAgent", condition="dual_coverage", is_conditional=True)
    dag.add_edge("InsuranceAgent", "FinanceAgent", condition="single_coverage_bypass", is_conditional=True)
    dag.add_edge("COBAgent", "FinanceAgent")
    dag.add_edge("FinanceAgent", "ReviewerAgent")
    
    # Backtracking / Retry cycles
    dag.add_edge("DocIntelAgent", "DocIntelAgent", condition="low_confidence_high_fidelity_retry", is_backtracking=True)
    dag.add_edge("MedicalCodingAgent", "DocIntelAgent", condition="empty_diagnosis_retry", is_backtracking=True)
    dag.add_edge("ReviewerAgent", "MedicalCodingAgent", condition="inconsistency_correction", is_backtracking=True)

    return dag
