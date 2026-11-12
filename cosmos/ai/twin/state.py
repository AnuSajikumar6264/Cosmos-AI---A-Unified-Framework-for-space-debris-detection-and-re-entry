"""Object state of the COSMOS-AI digital twin.

An :class:`ObjectTwin` is the twin of one catalogued object at one time ``as_of``.  It holds
what is known about the object at that time (identity, orbit, physical properties, operational
status, debris family, space weather) and the outputs that the modules attach to it.  Module
outputs always carry their provenance (module, model, validation status) and their own
uncertainty, so that a consumer can see which part of the twin is validated on real data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..contracts import Provenance as OutputProvenance


@dataclass
class ModuleOutput:
    module: str                       # health | debris | reentry | coupling
    model: str
    validation: str                   # e.g. "validated-real (GCAT temporal test 2016-2021)"
    values: dict[str, Any]
    uncertainty: dict[str, Any] = field(default_factory=dict)
    abstain: bool = False
    reason: str = ""
    provenance: OutputProvenance | None = None

    def __post_init__(self) -> None:
        for name in ("module", "model", "validation"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"ModuleOutput.{name} must be a string")
            if not value.strip():
                raise ValueError(f"ModuleOutput.{name} must not be empty")
        if self.abstain:
            if not isinstance(self.reason, str):
                raise TypeError("an abstaining ModuleOutput reason must be a string")
            if not self.reason.strip():
                raise ValueError("an abstaining ModuleOutput must include a reason")


@dataclass
class ObjectTwin:
    object_id: str                    # GCAT JCAT / NORAD number
    name: str
    object_class: str                 # P payload, R rocket stage, C component, D fragment
    as_of: str
    orbit: dict[str, Any]             # perigee, apogee, inc (km, deg) and orbit epoch
    physical: dict[str, Any]          # mass, dimensions, area-to-mass source, RCS
    operational_status: str | None    # catalogue health proxy for payloads ('+', 'P', '-', ...)
    family: dict[str, Any]            # launch / breakup family and causal sibling statistics
    space_weather: dict[str, Any]
    outputs: list[ModuleOutput] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.object_id, str):
            raise TypeError("ObjectTwin.object_id must be a string")
        if not self.object_id.strip():
            raise ValueError("ObjectTwin.object_id must not be empty")
        OutputProvenance(as_of=self.as_of, input_sources=("twin state",))
        if self.object_class not in {"P", "R", "C", "D"}:
            raise ValueError(f"unsupported object class: {self.object_class!r}")

    def attach(self, out: ModuleOutput) -> None:
        if out.provenance is not None and out.provenance.as_of != self.as_of:
            raise ValueError("module output provenance date must match the twin as-of date")
        self.outputs.append(out)

    def regime(self) -> str:
        """Re-entry regime implied by the health evidence (coupling C3)."""
        return classify_regime(self.object_class, self.operational_status)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["regime"] = self.regime()
        return d


def classify_regime(object_class: str, operational_status: str | None) -> str:
    """Apply the existing C3 regime rule without constructing a placeholder twin."""
    if object_class not in {"P", "R", "C", "D"}:
        raise ValueError(f"unsupported object class: {object_class!r}")
    if object_class != "P":
        return "natural_decay"
    if operational_status in ("+", "P", "B", "S", "X"):
        return "operator_controlled"
    if operational_status == "-":
        return "natural_decay"
    return "unknown"
