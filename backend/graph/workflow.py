"""LangGraph pipeline — linear stages, parallel work done inside stage nodes.

Topology:
  START → route_input
    ├─ (visitor_signal present) → identification_node → stage1_node
    └─ (company_input only)    → stage1_node
  stage1_node → stage2_node → playbook_node → summary_node → END
"""
from langgraph.graph import END, START, StateGraph

from backend.graph.nodes import (
    identification_node,
    playbook_node,
    route_input,
    stage1_node,
    stage2_node,
    summary_node,
)
from backend.graph.state import PipelineState


def build_workflow():
    """Construct and compile the LangGraph pipeline. Returns a CompiledStateGraph."""
    graph = StateGraph(PipelineState)

    graph.add_node("identification_node", identification_node)
    graph.add_node("stage1_node", stage1_node)
    graph.add_node("stage2_node", stage2_node)
    graph.add_node("playbook_node", playbook_node)
    graph.add_node("summary_node", summary_node)

    graph.add_conditional_edges(
        START,
        route_input,
        {
            "identification_node": "identification_node",
            "stage1_node": "stage1_node",
        },
    )
    graph.add_edge("identification_node", "stage1_node")
    graph.add_edge("stage1_node", "stage2_node")
    graph.add_edge("stage2_node", "playbook_node")
    graph.add_edge("playbook_node", "summary_node")
    graph.add_edge("summary_node", END)

    return graph.compile()


# Module-level compiled graph — imported by the controller.
# Build is deferred to first import to avoid failures during test collection.
compiled_workflow = build_workflow()
