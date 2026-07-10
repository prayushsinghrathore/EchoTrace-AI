"""
ReportRenderer — converts ReportData into various output formats.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.reports.schemas import ReportData


class ReportRenderer:
    """Renders ReportData to markdown, HTML, JSON, or plain text."""

    def render_markdown(self, data: ReportData) -> str:
        lines = [
            f"# {data.metadata.title}",
            "",
            f"**Generated:** {datetime.now(UTC).isoformat()}",
            "**Format:** Markdown",
            f"**Version:** {data.metadata.version}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            data.executive_summary or "No executive summary available.",
            "",
            "---",
            "",
            "## Evidence Summary",
            "",
            data.evidence_summary or "No evidence recorded.",
            "",
        ]

        if data.timeline:
            lines.extend([
                "---",
                "",
                "## Timeline",
                "",
            ])
            for event in data.timeline:
                dt = event.get("date", "?")
                title = event.get("title", "Untitled")
                desc = event.get("description", "")
                lines.append(f"- **[{dt}]** {title}")
                if desc:
                    lines.append(f"  - {desc}")

        if data.entities:
            lines.extend([
                "---",
                "",
                "## Entities",
                "",
            ])
            for ent in data.entities:
                etype = ent.get("type", "?")
                label = ent.get("label", "Unnamed")
                desc = ent.get("description", "")
                lines.append(f"- **{etype}:** {label}")
                if desc:
                    lines.append(f"  - {desc}")

        if data.relationships:
            lines.extend([
                "---",
                "",
                "## Relationships",
                "",
            ])
            for rel in data.relationships:
                rtype = rel.get("type", "?")
                src = rel.get("source", "?")
                tgt = rel.get("target", "?")
                conf = rel.get("confidence", "N/A")
                lines.append(f"- **{rtype}:** {src} → {tgt} (confidence: {conf})")

        if data.findings:
            lines.extend(["\n---\n\n## Findings\n"])
            for f_item in data.findings:
                lines.append(f"- **{f_item.get('title', 'Finding')}:** {f_item.get('description', '')}")

        if data.recommendations:
            lines.extend(["\n---\n\n## Recommendations\n"])
            for rec in data.recommendations:
                pri = rec.get("priority", "medium")
                lines.append(f"- **[{pri}]** {rec.get('title', '')}: {rec.get('description', '')}")

        if data.statistics:
            lines.extend([
                "\n---\n",
                "## Statistics",
                "",
            ])
            for k, v in data.statistics.items():
                lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")

        return "\n".join(lines)

    def render_html(self, data: ReportData) -> str:
        md = self.render_markdown(data)
        # Simple HTML wrapper
        lines_html = ""
        for line in md.split("\n"):
            lines_html += f"<p>{line}</p>\n" if line.strip() else "<br>\n"
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{data.metadata.title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 900px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #1a1a2e; }}
h1 {{ color: #1a1a2e; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
h2 {{ color: #2d3748; margin-top: 30px; }}
code {{ background: #f7fafc; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
</style>
</head>
<body>
{lines_html}
</body>
</html>"""

    def render_json(self, data: ReportData) -> str:
        return json.dumps(data.model_dump(), indent=2, default=str)
