from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.graphs.section_graph import create_section_graph
from app.graphs.state import GradingGraphOutput, GradingGraphState, SectionGraphState
from app.nodes.evidence_builder import evidence_builder
from app.nodes.final_synthesizer import final_synthesizer
from app.nodes.notebook_loader import notebook_loader
from app.nodes.notebook_parser import notebook_parser
from app.nodes.result_persister import result_persister
from app.nodes.section_splitter import section_splitter
from app.nodes.submission_loader import submission_loader


def create_grading_graph() -> Any:
    graph = StateGraph(GradingGraphState, output_schema=GradingGraphOutput)
    section_graph = create_section_graph()

    graph.add_node("submission_loader", submission_loader)
    graph.add_node("notebook_loader", notebook_loader)
    graph.add_node("notebook_parser", notebook_parser)
    graph.add_node("section_splitter", section_splitter)
    graph.add_node("evidence_builder", evidence_builder)
    graph.add_node("section_grading", section_graph)
    graph.add_node("final_synthesizer", final_synthesizer)
    graph.add_node("result_persister", result_persister)

    graph.add_edge(START, "submission_loader")
    graph.add_edge("submission_loader", "notebook_loader")
    graph.add_edge("notebook_loader", "notebook_parser")
    graph.add_edge("notebook_parser", "section_splitter")
    graph.add_edge("section_splitter", "evidence_builder")
    graph.add_conditional_edges("evidence_builder", fan_out_sections)
    graph.add_edge("section_grading", "final_synthesizer")
    graph.add_edge("final_synthesizer", "result_persister")
    graph.add_edge("result_persister", END)

    return graph.compile()


def fan_out_sections(state: GradingGraphState) -> list[Send] | str:
    sections = state.get("sections", [])
    if not sections:
        return "final_synthesizer"

    part_specs = {part.part_id: part for part in state["lab_spec"].parts}
    sends: list[Send] = []
    for section in sections:
        payload: SectionGraphState = {
            "lab_id": state["lab_spec"].lab_id,
            "part_spec": part_specs[section.part_id],
            "section": section,
            "evidence_index": state["evidence_index"],
        }
        if "api_response_judge" in state:
            payload["api_response_judge"] = state["api_response_judge"]
        if "code_judge" in state:
            payload["code_judge"] = state["code_judge"]
        if "markdown_judge" in state:
            payload["markdown_judge"] = state["markdown_judge"]
        sends.append(Send("section_grading", payload))

    return sends
