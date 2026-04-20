"""Rich console formatters for trust scores and scan results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def format_trust_score(score: "TrustScore") -> None:
    """Print a beautifully formatted trust score."""
    from trustpipe.trust.scorer import TrustScore

    # Grade color
    grade_colors = {"A+": "green", "A": "green", "B": "blue", "C": "yellow", "D": "red", "F": "red"}
    grade_color = grade_colors.get(score.grade, "white")

    # Header
    header = Text()
    header.append("Trust Score: ", style="bold")
    header.append(f"{score.composite}", style=f"bold {grade_color}")
    header.append("/100 ", style="dim")
    header.append(f"(Grade: {score.grade})", style=f"bold {grade_color}")
    if score.dataset_name:
        header.append(f"  [{score.dataset_name}]", style="dim")
    console.print(header)
    console.print()

    # Dimension table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Dimension", style="cyan", min_width=22)
    table.add_column("Score", justify="center", min_width=8)
    table.add_column("Bar", min_width=22)
    table.add_column("Weight", justify="right", style="dim")
    table.add_column("Grade", justify="center")

    for d in sorted(score.dimensions, key=lambda x: -x.raw_score):
        bar_len = int(d.raw_score * 20)
        bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)

        d_grade_color = grade_colors.get(d.grade, "white")
        score_text = f"{d.raw_score * 100:.1f}"

        table.add_row(
            d.name,
            score_text,
            f"[{d_grade_color}]{bar}[/{d_grade_color}]",
            f"{d.weight:.2f}",
            f"[{d_grade_color}]{d.grade}[/{d_grade_color}]",
        )

    console.print(table)

    # Warnings
    if score.warnings:
        console.print()
        for w in score.warnings:
            if "critically low" in w:
                console.print(f"  [red]![/red] {w}")
            elif "below acceptable" in w:
                console.print(f"  [yellow]![/yellow] {w}")
            else:
                console.print(f"  [dim]![/dim] {w}")


def format_scan_result(result: "ScanResult") -> None:
    """Print a formatted scan result."""
    from trustpipe.trust.scorer import ScanResult

    if result.flagged_count == 0:
        console.print("[green]\u2713[/green] No anomalies detected")
    else:
        pct = result.anomaly_fraction * 100
        console.print(
            f"[yellow]![/yellow] {result.flagged_count} anomalous records "
            f"detected ({pct:.1f}% of {result.total_count})"
        )

    console.print(f"  Detector: {result.detector_used}")

    if result.details:
        for k, v in result.details.items():
            console.print(f"  {k}: {v}")
