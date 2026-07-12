from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PythonParameter:
    name: str
    annotation: str | None = None
    default: str | None = None
    kind: str = "POSITIONAL"


@dataclass(frozen=True, slots=True)
class PythonFunction:
    name: str
    parameters: tuple[PythonParameter, ...] = ()
    returns: str | None = None
    decorators: tuple[str, ...] = ()
    is_async: bool = False
    docstring: str | None = None
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class PythonClass:
    name: str
    bases: tuple[str, ...] = ()
    methods: tuple[PythonFunction, ...] = ()
    decorators: tuple[str, ...] = ()
    docstring: str | None = None
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class PythonImport:
    module: str
    symbol: str | None = None
    alias: str | None = None
    relative_level: int = 0


@dataclass(frozen=True, slots=True)
class PythonModule:
    name: str
    docstring: str | None = None
    imports: tuple[PythonImport, ...] = ()
    functions: tuple[PythonFunction, ...] = ()
    classes: tuple[PythonClass, ...] = ()
    constants: tuple[str, ...] = ()
