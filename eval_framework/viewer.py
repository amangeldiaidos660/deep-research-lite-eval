from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from eval_framework.pricing import cost_details


def render_viewer(run_summary: dict[str, Any], output_path: str | Path) -> None:
    cards: list[str] = []
    for case in run_summary.get("cases", []):
        cards.append(_render_case(case))

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Deep Research Lite Eval Viewer</title>
  <style>
    :root {{
      --bg: #f7f4ec;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d9d1c3;
      --accent: #0f766e;
      --bad: #b91c1c;
      --good: #166534;
    }}
    body {{ font-family: Georgia, serif; background: linear-gradient(135deg, #f5efe3, #eef7f4); color: var(--ink); margin: 0; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ margin: 0 0 8px; font-size: 2.2rem; }}
    h2 {{ margin-bottom: 8px; }}
    .sub {{ color: var(--muted); margin-bottom: 24px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 18px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
    .row {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 10px 0; }}
    .pill {{ border-radius: 999px; padding: 4px 10px; font-size: 0.9rem; background: #ece6da; }}
    .ok {{ color: var(--good); }}
    .bad {{ color: var(--bad); }}
    details {{ margin-top: 10px; }}
    summary {{ cursor: pointer; font-weight: 600; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #faf6ee; border: 1px solid var(--line); padding: 12px; border-radius: 12px; }}
    .timeline {{ border-top: 1px solid var(--line); margin-top: 14px; padding-top: 10px; }}
    .timeline details {{ background: #fcf8f1; border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; }}
  </style>
</head>
<body>
  <main>
    <h1>Deep Research Lite Eval Viewer</h1>
    <div class="sub">Trace-first inspection for failures, tool usage, and per-case reliability.</div>
    {''.join(cards)}
  </main>
</body>
</html>"""
    Path(output_path).write_text(document, encoding="utf-8")


def _render_case(case: dict[str, Any]) -> str:
    attempt_html: list[str] = []
    for attempt in case.get("attempt_results", []):
        trace = attempt.get("trace", {})
        pricing = cost_details(trace)
        metric_rows = []
        for metric in attempt.get("metric_results", []):
            status = "SKIP" if metric["passed"] is None else ("PASS" if metric["passed"] else "FAIL")
            css = "ok" if metric["passed"] else ("bad" if metric["passed"] is False else "")
            metric_rows.append(
                f"<li><strong>{html.escape(metric['name'])}</strong>: "
                f"<span class='{css}'>{status}</span> "
                f"- {html.escape(metric['reason'])}</li>"
            )

        attempt_html.append(
            "<details>"
            f"<summary>Attempt {attempt['attempt_index']} - {'PASS' if attempt['passed'] else 'FAIL'}</summary>"
            f"<div class='row'><span class='pill'>trace: {html.escape(attempt['trace_path'])}</span>"
            f"<span class='pill'>stopped: {html.escape(str(trace.get('stopped_reason', '')))}</span>"
            f"<span class='pill'>latency: {html.escape(str(trace.get('wall_time_ms', 0)))} ms</span>"
            f"<span class='pill'>cost: ${html.escape(str(pricing['effective_cost_usd']))}</span>"
            f"<span class='pill'>cost source: {html.escape(str(pricing['cost_source']))}</span></div>"
            f"<ul>{''.join(metric_rows)}</ul>"
            f"{_render_trace_timeline(trace)}"
            "</details>"
        )

    return (
        "<section class='card'>"
        f"<h2>{html.escape(case['case_id'])}</h2>"
        f"<div>{html.escape(case.get('description', ''))}</div>"
        f"<div class='row'><span class='pill'>pass rate: {case['pass_count']}/{case['attempts']}</span>"
        f"<span class='pill'>pass^{case.get('reliability_k', 3)}: {case['pass_pow_k']}</span></div>"
        + "".join(attempt_html)
        + "</section>"
    )


def _render_trace_timeline(trace: dict[str, Any]) -> str:
    messages = trace.get("messages", [])
    if not messages:
        return "<div class='sub'>No trace messages captured for this attempt.</div>"

    rows: list[str] = ["<div class='timeline'><details open><summary>Message Timeline</summary>"]
    for idx, message in enumerate(messages, start=1):
        role = str(message.get("role", ""))
        title = f"{idx}. {role}"
        if message.get("name"):
            title += f" / {message['name']}"
        rows.append("<details>")
        rows.append(f"<summary>{html.escape(title)}</summary>")
        rows.append("<div class='row'>")
        if "latency_ms" in message:
            rows.append(
                f"<span class='pill'>latency: {html.escape(str(message.get('latency_ms')))} ms</span>"
            )
        if role == "tool" and message.get("tool_use_id"):
            rows.append(
                f"<span class='pill'>tool_use_id: {html.escape(str(message.get('tool_use_id')))}</span>"
            )
        rows.append("</div>")

        content = message.get("content")
        if role == "assistant":
            content = message.get("text", "")
        if content not in (None, "", []):
            rows.append("<div><strong>Content</strong></div>")
            rows.append(f"<pre>{html.escape(_pretty(content))}</pre>")

        for call_index, call in enumerate(message.get("tool_calls", []), start=1):
            rows.append("<details>")
            rows.append(
                f"<summary>Tool Call {call_index}: {html.escape(str(call.get('name', '')))}</summary>"
            )
            rows.append("<div><strong>Args</strong></div>")
            rows.append(f"<pre>{html.escape(_pretty(call.get('args', {})))}</pre>")
            rows.append("</details>")

        rows.append("</details>")
    rows.append("</details></div>")
    return "".join(rows)


def _pretty(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)
