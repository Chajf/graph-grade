from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.graphs.grading_graph import create_grading_graph
from app.graphs.state import GradingGraphState, LaboratoryGraphState
from app.nodes.group_summary_writer import group_summary_writer
from app.nodes.lab_spec_loader import lab_spec_loader
from app.nodes.lab_spec_validator import lab_spec_validator
from app.nodes.submission_resolution_collector import submission_resolution_collector
from app.nodes.submission_lister import submission_lister


def create_laboratory_graph() -> Any:
    graph = StateGraph(LaboratoryGraphState)
    grading_graph = create_grading_graph()

    graph.add_node("lab_spec_loader", lab_spec_loader)
    graph.add_node("lab_spec_validator", lab_spec_validator)
    graph.add_node("submission_lister", submission_lister)
    graph.add_node("submission_resolution_collector", submission_resolution_collector)
    graph.add_node("student_grading", grading_graph)
    graph.add_node("group_summary_writer", group_summary_writer)

    graph.add_edge(START, "lab_spec_loader")
    graph.add_edge("lab_spec_loader", "lab_spec_validator")
    graph.add_edge("lab_spec_validator", "submission_lister")
    graph.add_edge("submission_lister", "submission_resolution_collector")
    graph.add_conditional_edges("submission_resolution_collector", fan_out_students)
    graph.add_edge("student_grading", "group_summary_writer")
    graph.add_edge("group_summary_writer", END)

    return graph.compile()


def fan_out_students(state: LaboratoryGraphState) -> list[Send] | str:
    submissions = [submission for submission in state.get("submissions", []) if submission.resolved]
    if not submissions:
        return "group_summary_writer"

    sends: list[Send] = []
    for submission in submissions:
        payload: GradingGraphState = {
            "lab_spec": state["lab_spec"],
            "submission": submission,
            "output_root": state["output_root"],
        }
        if "code_judge" in state:
            payload["code_judge"] = state["code_judge"]
        if "markdown_judge" in state:
            payload["markdown_judge"] = state["markdown_judge"]
        sends.append(Send("student_grading", payload))

    return sends
