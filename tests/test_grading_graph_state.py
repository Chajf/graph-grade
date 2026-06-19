import operator
from typing import get_args, get_origin, get_type_hints

from app.graphs.state import GradingGraphState, SectionGradingPayload


def test_grading_graph_state_collects_section_grades_with_add_reducer() -> None:
    hints = get_type_hints(GradingGraphState, include_extras=True)
    metadata = _reducer_metadata(hints["section_grades"])

    assert metadata == (operator.add,)


def test_section_grading_payload_collects_section_grades_with_add_reducer() -> None:
    hints = get_type_hints(SectionGradingPayload, include_extras=True)
    metadata = _reducer_metadata(hints["section_grades"])

    assert metadata == (operator.add,)


def _reducer_metadata(annotation):
    if get_origin(annotation).__name__ == "NotRequired":
        annotation = get_args(annotation)[0]
    return get_args(annotation)[1:]
