"""Dependency-injected orchestration for independently executable COSMOS-AI modules.

The runner composes adapters; it does not invent shared identity or join unpaired datasets.
Module failures are recorded explicitly, dependants are blocked, and independent modules
continue so partial execution remains possible.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping, Sequence

from .contracts import Provenance

logger = logging.getLogger(__name__)

ModuleStatus = Literal["success", "failed", "blocked", "not_requested"]
ModuleRunner = Callable[["ModuleContext"], "ModuleResult"]


class OrchestrationError(RuntimeError):
    """Raised when callers require a successful run but one or more modules failed."""

    def __init__(self, result: "PipelineExecution"):
        self.result = result
        failures = [
            f"{name}: {node.error or node.reason}"
            for name, node in result.modules.items()
            if node.status in {"failed", "blocked"}
        ]
        super().__init__("pipeline did not complete successfully: " + "; ".join(failures))


@dataclass(frozen=True)
class ModuleContext:
    inputs: Mapping[str, Any]
    outputs: Mapping[str, Mapping[str, Any]]
    config: Mapping[str, Any]
    config_sha256: str


@dataclass(frozen=True)
class ModuleResult:
    """Successful adapter return value with required source provenance."""

    outputs: Mapping[str, Any]
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.outputs, Mapping):
            raise TypeError("module outputs must be a mapping")
        if not self.outputs:
            raise ValueError("a successful module must return at least one named output")
        if any(not isinstance(key, str) or not key.strip() for key in self.outputs):
            raise ValueError("module output keys must be non-empty strings")
        if not isinstance(self.provenance, Provenance):
            raise TypeError("successful module results require typed provenance")


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    run: ModuleRunner
    depends_on: tuple[str, ...] = ()
    required_inputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("module name must not be empty")
        if self.name in self.depends_on:
            raise ValueError(f"module {self.name!r} cannot depend on itself")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError(f"module {self.name!r} has duplicate dependencies")
        if len(set(self.required_inputs)) != len(self.required_inputs):
            raise ValueError(f"module {self.name!r} has duplicate required inputs")


@dataclass(frozen=True)
class ModuleExecution:
    name: str
    status: ModuleStatus
    outputs: Mapping[str, Any] = field(default_factory=dict)
    provenance: Provenance | None = None
    reason: str = ""
    error: str = ""
    started_at: str | None = None
    duration_s: float | None = None


@dataclass(frozen=True)
class PipelineExecution:
    modules: Mapping[str, ModuleExecution]
    requested: tuple[str, ...]
    config_sha256: str
    started_at: str
    duration_s: float

    @property
    def successful(self) -> bool:
        return all(
            result.status in {"success", "not_requested"}
            for result in self.modules.values()
        )

    def raise_for_failures(self) -> None:
        if not self.successful:
            raise OrchestrationError(self)


class Orchestrator:
    """Execute module adapters with dependency, input, and partial-run handling."""

    def __init__(self, modules: Sequence[ModuleSpec]):
        specs = {module.name: module for module in modules}
        if len(specs) != len(modules):
            raise ValueError("module names must be unique")
        for module in modules:
            if not callable(module.run):
                raise TypeError(f"module {module.name!r} runner must be callable")
            unknown = set(module.depends_on) - specs.keys()
            if unknown:
                raise ValueError(f"module {module.name!r} has unknown dependencies: {sorted(unknown)}")
        self._specs = specs
        self._order = self._topological_order()

    def _topological_order(self) -> tuple[str, ...]:
        state: dict[str, int] = {}
        order: list[str] = []

        def visit(name: str) -> None:
            mark = state.get(name, 0)
            if mark == 1:
                raise ValueError(f"module dependency cycle includes {name!r}")
            if mark == 2:
                return
            state[name] = 1
            for dependency in self._specs[name].depends_on:
                visit(dependency)
            state[name] = 2
            order.append(name)

        for name in self._specs:
            visit(name)
        return tuple(order)

    def _dependency_closure(self, requested: tuple[str, ...]) -> set[str]:
        closure: set[str] = set()

        def include(name: str) -> None:
            if name not in self._specs:
                raise ValueError(f"unknown requested module: {name!r}")
            if name in closure:
                return
            closure.add(name)
            for dependency in self._specs[name].depends_on:
                include(dependency)

        for name in requested:
            include(name)
        return closure

    def run(
        self,
        inputs: Mapping[str, Any],
        selected: Sequence[str] | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> PipelineExecution:
        started = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        requested = tuple(self._specs) if selected is None else tuple(dict.fromkeys(selected))
        active = self._dependency_closure(requested)
        completed: dict[str, ModuleExecution] = {
            name: ModuleExecution(name=name, status="not_requested")
            for name in self._specs
        }
        successful_outputs: dict[str, Mapping[str, Any]] = {}
        initial_inputs = MappingProxyType(dict(inputs))
        resolved_config = MappingProxyType(dict(config or {}))
        config_digest = hashlib.sha256(
            json.dumps(dict(resolved_config), sort_keys=True, allow_nan=False).encode()
        ).hexdigest()

        for name in self._order:
            if name not in active:
                continue
            spec = self._specs[name]
            blocked_by = [
                dependency for dependency in spec.depends_on
                if completed[dependency].status != "success"
            ]
            if blocked_by:
                completed[name] = ModuleExecution(
                    name=name,
                    status="blocked",
                    reason=f"dependencies did not succeed: {', '.join(blocked_by)}",
                )
                continue
            missing = [key for key in spec.required_inputs if key not in initial_inputs]
            if missing:
                completed[name] = ModuleExecution(
                    name=name,
                    status="blocked",
                    reason=f"missing required inputs: {', '.join(missing)}",
                )
                continue
            context = ModuleContext(
                inputs=initial_inputs,
                outputs=MappingProxyType(dict(successful_outputs)),
                config=resolved_config,
                config_sha256=config_digest,
            )
            module_started = time.monotonic()
            module_started_at = datetime.now(timezone.utc).isoformat()
            try:
                result = spec.run(context)
                if not isinstance(result, ModuleResult):
                    raise TypeError("module runner must return a ModuleResult with provenance")
                outputs = dict(result.outputs)
                provenance = result.provenance
                if provenance.config_digest not in {None, config_digest}:
                    raise ValueError("module provenance config_digest does not match this run")
                if provenance.config_digest is None:
                    provenance = replace(provenance, config_digest=config_digest)
            except Exception as exc:
                logger.exception("COSMOS-AI module %s failed", name)
                completed[name] = ModuleExecution(
                    name=name,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                    started_at=module_started_at,
                    duration_s=time.monotonic() - module_started,
                )
                continue
            successful_outputs[name] = MappingProxyType(outputs)
            completed[name] = ModuleExecution(
                name=name,
                status="success",
                outputs=MappingProxyType(outputs),
                provenance=provenance,
                started_at=module_started_at,
                duration_s=time.monotonic() - module_started,
            )
            logger.info("COSMOS-AI module %s completed", name)

        return PipelineExecution(
            modules=MappingProxyType(completed),
            requested=requested,
            config_sha256=config_digest,
            started_at=started_at,
            duration_s=time.monotonic() - started,
        )
