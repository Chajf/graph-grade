from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graphs.state import SectionGraphOutput, SectionGraphState
from app.nodes.code_grader import grade_code_requirements
from app.nodes.code_judge import judge_code_requirements
from app.nodes.markdown_grader import grade_markdown_requirements
from app.nodes.markdown_judge import judge_markdown_requirements
from app.nodes.results_grader import grade_result_requirements
from app.nodes.section_loader import section_loader
from app.nodes.section_synthesizer import synthesize_section_grade


def create_section_graph() -> Any:
    graph = StateGraph(SectionGraphState, output_schema=SectionGraphOutput)

    graph.add_node("section_loader", section_loader)
    graph.add_node("code_grader", grade_code_requirements)
    graph.add_node("code_judge", judge_code_requirements)
    graph.add_node("markdown_grader", grade_markdown_requirements)
    graph.add_node("markdown_judge", judge_markdown_requirements)
    graph.add_node("results_grader", grade_result_requirements)
    graph.add_node("section_synthesizer", synthesize_section_grade)

    graph.add_edge(START, "section_loader")
    graph.add_conditional_edges(
        "section_loader",
        route_to_grading_nodes,
    )
    graph.add_conditional_edges("code_grader", route_after_code_grader)
    graph.add_edge("code_judge", "section_synthesizer")
    graph.add_conditional_edges("markdown_grader", route_after_markdown_grader)
    graph.add_edge("markdown_judge", "section_synthesizer")
    graph.add_edge("results_grader", "section_synthesizer")
    graph.add_edge("section_synthesizer", END)

    return graph.compile()


def route_to_grading_nodes(state: SectionGraphState) -> list[str]:
    next_nodes: list[str] = []
    if _has_code_branch(state):
        next_nodes.append("code_grader")
    if _has_markdown_branch(state):
        next_nodes.append("markdown_grader")
    if _has_results_branch(state):
        next_nodes.append("results_grader")
    return next_nodes or ["section_synthesizer"]


def route_after_code_grader(state: SectionGraphState) -> str:
    return "code_judge" if state.get("code_judge") is not None else "section_synthesizer"


def route_after_markdown_grader(state: SectionGraphState) -> str:
    return (
        "markdown_judge"
        if state.get("markdown_judge") is not None
        else "section_synthesizer"
    )


def _has_code_branch(state: SectionGraphState) -> bool:
    part_spec = state["part_spec"]
    return part_spec.code_applicable and bool(part_spec.code_requirements)


def _has_markdown_branch(state: SectionGraphState) -> bool:
    part_spec = state["part_spec"]
    return part_spec.markdown_applicable and bool(part_spec.markdown_requirements)


def _has_results_branch(state: SectionGraphState) -> bool:
    part_spec = state["part_spec"]
    return part_spec.results_applicable and bool(part_spec.result_requirements)
