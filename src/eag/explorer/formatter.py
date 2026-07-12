import json
from dataclasses import asdict, is_dataclass
from typing import Any, Protocol

from eag.explorer.models import (
    DependencyView,
    ModuleView,
    OverviewView,
    SearchView,
    StatisticsView,
    SymbolView,
    View,
)


class Formatter(Protocol):
    def format(self, view: View) -> str: ...


class JsonFormatter:
    def format(self, view: View) -> str:
        def serialize(obj: Any) -> Any:
            if is_dataclass(obj) and not isinstance(obj, type):
                return asdict(obj)
            return str(obj)

        return json.dumps(view, default=serialize, indent=2)


class TerminalFormatter:
    def format(self, view: View) -> str:
        if isinstance(view, OverviewView):
            return self._format_overview(view)
        if isinstance(view, StatisticsView):
            return self._format_statistics(view)
        if isinstance(view, SymbolView):
            return self._format_symbol(view)
        if isinstance(view, ModuleView):
            return self._format_module(view)
        if isinstance(view, DependencyView):
            return self._format_dependency(view)
        if isinstance(view, SearchView):
            return self._format_search(view)
        return str(view)

    def _format_overview(self, view: OverviewView) -> str:
        lines = [
            "Engineering Overview",
            "═══════════════════════════════════════",
            "",
            f"Repository:  {view.repository}",
            f"Health:      {view.health}",
            "",
            "Knowledge:",
            f"  Modules:        {view.modules}",
            f"  Symbols:        {view.symbols}",
            f"  Dependencies:   {view.dependencies}",
            "",
            "Capabilities:",
        ]
        for cap in view.capabilities:
            lines.append(f"  ✓ {cap}")

        lines.extend(
            [
                "",
                "Available Commands:",
                "  find, module, deps, search, stats",
            ]
        )
        return "\n".join(lines)

    def _format_statistics(self, view: StatisticsView) -> str:
        lines = [
            "Engineering Statistics",
            "──────────────────────────",
            f"Files:        {view.files}",
            f"Modules:      {view.modules}",
            "",
            "Symbols:",
            f"  Classes:      {view.classes}",
            f"  Interfaces:   {view.interfaces}",
            f"  Protocols:    {view.protocols}",
            f"  Enums:        {view.enums}",
            f"  Dataclasses:  {view.dataclasses}",
            f"  Functions:    {view.functions}",
            f"  Methods:      {view.methods}",
            f"  Constants:    {view.constants}",
            f"  Total:        {view.symbols}",
            "",
            f"Dependencies: {view.dependencies}",
            f"Avg Syms/Mod: {view.avg_symbols_per_module}",
        ]
        return "\n".join(lines)

    def _format_symbol(self, view: SymbolView) -> str:
        lines = [
            f"{view.name}",
            "──────────────────────────",
            f"Kind:       {view.kind}",
            f"Module:     {view.module}",
            f"File:       {view.file}",
            f"Visibility: {view.visibility}",
        ]
        if view.methods:
            lines.append("\nMethods:")
            for m in view.methods:
                lines.append(f"  • {m}")
        if view.dependencies:
            lines.append("\nDependencies:")
            for d in view.dependencies:
                lines.append(f"  • {d}")
        return "\n".join(lines)

    def _format_module(self, view: ModuleView) -> str:
        lines = [
            "Module",
            "──────────────────────────",
            f"Name: {view.name}",
            f"File: {view.file}",
        ]
        if view.symbols:
            lines.append("\nSymbols:")
            for s in view.symbols:
                lines.append(f"  • {s}")
        if view.dependencies:
            lines.append("\nDependencies:")
            for d in view.dependencies:
                lines.append(f"  • {d}")
        return "\n".join(lines)

    def _format_dependency(self, view: DependencyView) -> str:
        lines = [
            f"Dependencies for {view.source}",
            "──────────────────────────",
        ]
        if view.dependencies:
            for d in view.dependencies:
                lines.append(f"  • {d}")
        else:
            lines.append("  None")
        return "\n".join(lines)

    def _format_search(self, view: SearchView) -> str:
        lines = [
            f"Search Results for '{view.query}'",
            "──────────────────────────",
        ]
        if view.results:
            for r in view.results:
                lines.append(f"  • {r}")
        else:
            lines.append("  No results found.")
        return "\n".join(lines)
