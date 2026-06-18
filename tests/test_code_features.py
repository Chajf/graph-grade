from app.services.code_features import extract_code_features


def test_extract_code_features_from_valid_python() -> None:
    features = extract_code_features(
        """
import json
import pandas as pd
from langchain.agents import create_agent
from .helpers import tool

class LabAgent:
    def run(self):
        return self.client.invoke()

async def build_agent():
    agent = create_agent()
    print(agent)
"""
    )

    assert features.functions == ["run", "build_agent"]
    assert features.classes == ["LabAgent"]
    assert features.imports == ["json", "pandas"]
    assert features.from_imports == ["langchain.agents.create_agent", ".helpers.tool"]
    assert features.calls == ["self.client.invoke", "create_agent", "print"]
    assert features.syntax_error is None


def test_extract_code_features_uses_fallback_for_invalid_python() -> None:
    features = extract_code_features(
        """
class BrokenAgent
def build_agent(
async def async_agent(
"""
    )

    assert features.functions == ["build_agent", "async_agent"]
    assert features.classes == ["BrokenAgent"]
    assert features.imports == []
    assert features.from_imports == []
    assert features.calls == []
    assert features.syntax_error is not None


def test_extract_code_features_deduplicates_in_discovery_order() -> None:
    features = extract_code_features(
        """
def repeated():
    pass

def repeated():
    pass

repeated()
repeated()
"""
    )

    assert features.functions == ["repeated"]
    assert features.calls == ["repeated"]
