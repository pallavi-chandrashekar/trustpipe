"""TrustPipe Web Dashboard — Plotly Dash application.

Launch: trustpipe dashboard --port 8050
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import dash
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

from trustpipe.core.engine import TrustPipe


def create_app(tp: TrustPipe) -> dash.Dash:
    """Create the Dash application with all layouts and callbacks."""

    app = dash.Dash(
        __name__,
        title="TrustPipe Dashboard",
        suppress_callback_exceptions=True,
    )

    app.layout = html.Div([
        # Header
        html.Div([
            html.H1("TrustPipe", style={"display": "inline", "marginRight": "12px"}),
            html.Span("AI Data Supply Chain Trust & Provenance",
                       style={"color": "#888", "fontSize": "16px"}),
        ], style={"padding": "20px 30px", "borderBottom": "1px solid #eee"}),

        # Tabs
        dcc.Tabs(id="tabs", value="overview", children=[
            dcc.Tab(label="Overview", value="overview"),
            dcc.Tab(label="Records", value="records"),
            dcc.Tab(label="Compliance", value="compliance"),
        ]),

        # Content
        html.Div(id="tab-content", style={"padding": "20px 30px"}),

        # Auto-refresh every 30s
        dcc.Interval(id="refresh", interval=30_000, n_intervals=0),
    ], style={"fontFamily": "system-ui, -apple-system, sans-serif", "maxWidth": "1200px", "margin": "0 auto"})

    @app.callback(
        Output("tab-content", "children"),
        [Input("tabs", "value"), Input("refresh", "n_intervals")],
    )
    def render_tab(tab: str, _n: int) -> html.Div:
        if tab == "overview":
            return _build_overview(tp)
        elif tab == "records":
            return _build_records(tp)
        elif tab == "compliance":
            return _build_compliance(tp)
        return html.Div("Unknown tab")

    return app


def _build_overview(tp: TrustPipe) -> html.Div:
    """Overview tab: status cards + trust score gauges."""
    status = tp.status()
    verify = tp.verify()

    # Status cards
    cards = html.Div([
        _card("Records", str(status["record_count"]), "#3498db"),
        _card("Chain Length", str(status["chain_length"]), "#2ecc71"),
        _card("Integrity", verify["integrity"], "#2ecc71" if verify["integrity"] == "OK" else "#e74c3c"),
        _card("Failed", str(verify["failed"]), "#e74c3c" if verify["failed"] > 0 else "#2ecc71"),
    ], style={"display": "flex", "gap": "20px", "marginBottom": "30px"})

    # Trust score gauges for latest datasets
    records = tp._storage.get_latest_records(tp.project, limit=20)
    dataset_names = list(dict.fromkeys(r.name for r in records))[:6]  # unique, max 6

    gauges = []
    for name in dataset_names:
        score_data = tp._storage.load_latest_trust_score(name, tp.project)
        if score_data:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score_data["composite"],
                title={"text": name, "font": {"size": 14}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": _score_color(score_data["composite"])},
                    "steps": [
                        {"range": [0, 40], "color": "#fde8e8"},
                        {"range": [40, 70], "color": "#fef3cd"},
                        {"range": [70, 100], "color": "#d4edda"},
                    ],
                },
            ))
            fig.update_layout(height=200, margin=dict(t=40, b=10, l=30, r=30))
            gauges.append(html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False}),
                                   style={"width": "280px"}))

    gauge_section = html.Div([
        html.H3("Trust Scores"),
        html.Div(gauges, style={"display": "flex", "flexWrap": "wrap", "gap": "10px"}),
    ]) if gauges else html.Div()

    # Chain root
    root_info = html.Div([
        html.H3("Merkle Chain"),
        html.Code(status["chain_root"] or "empty", style={"fontSize": "12px", "color": "#666"}),
    ], style={"marginTop": "20px"})

    return html.Div([cards, gauge_section, root_info])


def _build_records(tp: TrustPipe) -> html.Div:
    """Records tab: table of all provenance records."""
    records = tp._storage.get_latest_records(tp.project, limit=100)

    data = [
        {
            "ID": r.id,
            "Name": r.name,
            "Source": r.source or "-",
            "Rows": r.row_count or "-",
            "Columns": r.column_count or "-",
            "Tags": ", ".join(r.tags) if r.tags else "-",
            "Merkle Root": r.merkle_root[:16] + "..." if r.merkle_root else "-",
            "Created": r.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for r in records
    ]

    return html.Div([
        html.H3(f"Provenance Records ({len(records)})"),
        dash_table.DataTable(
            data=data,
            columns=[{"name": col, "id": col} for col in data[0].keys()] if data else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
            ],
            page_size=20,
            sort_action="native",
            filter_action="native",
        ) if data else html.P("No records yet.", style={"color": "#888"}),
    ])


def _build_compliance(tp: TrustPipe) -> html.Div:
    """Compliance tab: gap summary across all datasets."""
    records = tp._storage.get_latest_records(tp.project, limit=100)
    dataset_names = list(dict.fromkeys(r.name for r in records))[:10]

    rows = []
    for name in dataset_names:
        try:
            import json
            report = tp.comply(name, output_format="json")
            parsed = json.loads(report)
            gaps = parsed.get("gaps", [])
            critical = sum(1 for g in gaps if g["severity"] == "CRITICAL")
            warning = sum(1 for g in gaps if g["severity"] == "WARNING")
            info = sum(1 for g in gaps if g["severity"] == "INFO")
            score_data = tp._storage.load_latest_trust_score(name, tp.project)
            trust = f"{score_data['composite']}/100 ({score_data['grade']})" if score_data else "-"
            rows.append({
                "Dataset": name,
                "Trust Score": trust,
                "Critical": critical,
                "Warnings": warning,
                "Info": info,
                "Total Gaps": len(gaps),
            })
        except Exception:
            rows.append({"Dataset": name, "Trust Score": "-", "Critical": "?", "Warnings": "?", "Info": "?", "Total Gaps": "?"})

    return html.Div([
        html.H3("Compliance Overview"),
        dash_table.DataTable(
            data=rows,
            columns=[{"name": col, "id": col} for col in rows[0].keys()] if rows else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            style_data_conditional=[
                {"if": {"filter_query": "{Critical} > 0"}, "backgroundColor": "#fde8e8"},
            ],
            page_size=20,
        ) if rows else html.P("No datasets tracked yet.", style={"color": "#888"}),
    ])


def _card(title: str, value: str, color: str) -> html.Div:
    return html.Div([
        html.Div(title, style={"fontSize": "12px", "color": "#888", "textTransform": "uppercase"}),
        html.Div(value, style={"fontSize": "28px", "fontWeight": "bold", "color": color}),
    ], style={
        "padding": "16px 24px", "borderRadius": "8px", "backgroundColor": "#fff",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "minWidth": "120px",
    })


def _score_color(score: int) -> str:
    if score >= 85:
        return "#2ecc71"
    if score >= 70:
        return "#3498db"
    if score >= 55:
        return "#f39c12"
    return "#e74c3c"


def run_dashboard(
    tp: TrustPipe,
    host: str = "127.0.0.1",
    port: int = 8050,
    debug: bool = False,
) -> None:
    """Launch the dashboard server."""
    app = create_app(tp)
    app.run(host=host, port=port, debug=debug)
