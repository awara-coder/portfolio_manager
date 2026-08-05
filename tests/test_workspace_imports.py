from __future__ import annotations

import importlib

import pytest

WORKSPACE_MODULES = (
    "portfolio_manager.analytics",
    "portfolio_manager.application",
    "portfolio_manager.apps.api",
    "portfolio_manager.apps.mcp",
    "portfolio_manager.apps.worker",
    "portfolio_manager.assistant",
    "portfolio_manager.connectors",
    "portfolio_manager.domain",
    "portfolio_manager.jobs",
    "portfolio_manager.observability",
    "portfolio_manager.persistence",
    "portfolio_manager.reporting",
)


@pytest.mark.parametrize("module_name", WORKSPACE_MODULES)
def test_workspace_module_is_importable(module_name: str) -> None:
    assert importlib.import_module(module_name)
