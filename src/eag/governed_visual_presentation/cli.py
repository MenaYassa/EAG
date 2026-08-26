"""Typer registration for the G2.4.24 loopback-only visual host."""

from __future__ import annotations

import typer

from eag.governed_visual_presentation import start_fixed_profile_visual_host


def register_fixed_profile_visual_command(app: typer.Typer) -> None:
    """Register the one isolated local visual-host command."""

    @app.command("serve-fixed-profile-visual")
    def serve_fixed_profile_visual(
        port: int = typer.Option(8765, "--port", min=1, max=65535, help="Loopback-only local port."),  # noqa: B008
    ) -> None:
        """Serve the G2.4.24 visual page only on 127.0.0.1 until interrupted."""
        typer.echo(f"EAG fixed-profile visual host: http://127.0.0.1:{port}/")
        start_fixed_profile_visual_host(port=port)


__all__ = ["register_fixed_profile_visual_command"]
