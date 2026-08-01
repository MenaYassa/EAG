"""Runtime component registry for EAG."""

from typing import Any

from eag.chief.runtime.errors import ChiefRuntimeError


class RuntimeRegistry:
    """Registers and manages runtime components (planners, executors, validators)."""

    def __init__(self) -> None:
        self._components: dict[str, Any] = {}

    def register_planner(self, name: str, planner: Any) -> None:
        self._components[f"planner:{name}"] = planner

    def register_executor(self, name: str, executor: Any) -> None:
        self._components[f"executor:{name}"] = executor

    def register_validator(self, name: str, validator: Any) -> None:
        self._components[f"validator:{name}"] = validator

    def get_planner(self, name: str) -> Any:
        key = f"planner:{name}"
        if key not in self._components:
            raise ChiefRuntimeError(f"Planner '{name}' not found.")
        return self._components[key]

    def get_executor(self, name: str) -> Any:
        key = f"executor:{name}"
        if key not in self._components:
            raise ChiefRuntimeError(f"Executor '{name}' not found.")
        return self._components[key]

    def get_validator(self, name: str) -> Any:
        key = f"validator:{name}"
        if key not in self._components:
            raise ChiefRuntimeError(f"Validator '{name}' not found.")
        return self._components[key]

    def list_planners(self) -> tuple[str, ...]:
        return tuple(k.split(":", 1)[1] for k in self._components if k.startswith("planner:"))

    def list_executors(self) -> tuple[str, ...]:
        return tuple(k.split(":", 1)[1] for k in self._components if k.startswith("executor:"))

    def list_validators(self) -> tuple[str, ...]:
        return tuple(k.split(":", 1)[1] for k in self._components if k.startswith("validator:"))
