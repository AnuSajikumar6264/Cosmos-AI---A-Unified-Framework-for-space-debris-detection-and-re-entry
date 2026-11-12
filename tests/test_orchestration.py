"""Partial-run orchestration behavior with injected, dataset-free module adapters."""
from __future__ import annotations

import pytest

from cosmos.ai.contracts import Provenance
from cosmos.ai.orchestration import ModuleResult, ModuleSpec, OrchestrationError, Orchestrator


def _result(outputs):
    return ModuleResult(outputs, Provenance(as_of="2026-10-27", input_sources=("test",)))


def test_partial_run_skips_unselected_modules_and_runs_dependencies() -> None:
    calls: list[str] = []
    runner = Orchestrator([
        ModuleSpec("telemetry", lambda ctx: calls.append("telemetry") or _result({"health": "ok"}),
                   required_inputs=("telemetry_batch",)),
        ModuleSpec("orbit", lambda ctx: calls.append("orbit") or _result({"state": "ok"}),
                   required_inputs=("orbit_state",)),
        ModuleSpec(
            "lifetime",
            lambda ctx: calls.append("lifetime") or _result(
                {"prediction": ctx.outputs["orbit"]["state"]}
            ),
            depends_on=("orbit",),
        ),
    ])

    result = runner.run(
        {"telemetry_batch": object(), "orbit_state": object()},
        selected=("lifetime",),
    )

    assert calls == ["orbit", "lifetime"]
    assert result.modules["orbit"].status == "success"
    assert result.modules["lifetime"].outputs["prediction"] == "ok"
    assert result.modules["telemetry"].status == "not_requested"
    assert result.successful


def test_module_failure_blocks_dependants_but_not_independent_modules() -> None:
    calls: list[str] = []

    def fail(_ctx):
        calls.append("failed")
        raise RuntimeError("source unavailable")

    runner = Orchestrator([
        ModuleSpec("health", fail),
        ModuleSpec("decision", lambda _ctx: calls.append("decision") or _result({"value": 1}),
                   depends_on=("health",)),
        ModuleSpec("orbit", lambda _ctx: calls.append("orbit") or _result({"value": 2})),
    ])
    result = runner.run({})

    assert calls == ["failed", "orbit"]
    assert result.modules["health"].status == "failed"
    assert "source unavailable" in result.modules["health"].error
    assert result.modules["decision"].status == "blocked"
    assert result.modules["orbit"].status == "success"
    assert not result.successful
    with pytest.raises(OrchestrationError, match="health: RuntimeError"):
        result.raise_for_failures()


def test_missing_input_blocks_module_and_reports_exact_key() -> None:
    runner = Orchestrator([
        ModuleSpec("vision", lambda _ctx: {"detections": []}, required_inputs=("images",)),
        ModuleSpec("telemetry", lambda _ctx: _result({"health": "computed"})),
    ])
    result = runner.run({})

    assert result.modules["vision"].status == "blocked"
    assert result.modules["vision"].reason == "missing required inputs: images"
    assert result.modules["telemetry"].status == "success"


def test_orchestrator_rejects_invalid_graph_and_outputs() -> None:
    with pytest.raises(ValueError, match="unknown dependencies"):
        Orchestrator([ModuleSpec("a", lambda _ctx: _result({}), depends_on=("missing",))])
    with pytest.raises(ValueError, match="dependency cycle"):
        Orchestrator([
            ModuleSpec("a", lambda _ctx: _result({"a": 1}), depends_on=("b",)),
            ModuleSpec("b", lambda _ctx: _result({"b": 1}), depends_on=("a",)),
        ])
    result = Orchestrator([ModuleSpec("bad", lambda _ctx: None)]).run({})
    assert result.modules["bad"].status == "failed"
    assert "must return a ModuleResult" in result.modules["bad"].error


def test_unknown_selected_module_fails_explicitly() -> None:
    runner = Orchestrator([ModuleSpec("health", lambda _ctx: _result({"health": 1}))])
    with pytest.raises(ValueError, match="unknown requested module"):
        runner.run({}, selected=("health", "missing"))


def test_module_result_requires_provenance_and_config_is_hashed() -> None:
    with pytest.raises(TypeError, match="typed provenance"):
        ModuleResult({"prediction": 1}, None)
    runner = Orchestrator([
        ModuleSpec(
            "health",
            lambda ctx: _result({"threshold": ctx.config["threshold"]}),
        )
    ])
    result = runner.run({}, config={"threshold": 0.75})

    assert result.modules["health"].outputs["threshold"] == 0.75
    assert len(result.config_sha256) == 64
    assert result.modules["health"].provenance.input_sources == ("test",)
    assert result.modules["health"].provenance.config_digest == result.config_sha256
    assert result.modules["health"].duration_s is not None
