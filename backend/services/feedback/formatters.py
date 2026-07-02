"""Human-readable report bodies for email, GitHub issues, and webhooks."""

from __future__ import annotations

from backend.models.match_report import MatchErrorReport

_ISSUE_LABELS: dict[str, str] = {
    "wrong_part_number": "Wrong McMaster part #",
    "wrong_category_or_search": "Wrong McMaster category/search",
    "missed_hardware": "Missed hardware line",
    "wrong_finish_or_material": "Wrong finish/material",
    "should_be_not_applicable": "Should not link to McMaster",
    "other": "Other McMaster issue",
    "makerworld_wrong_line": "Wrong MakerWorld BOM line",
    "makerworld_missing_hardware": "Missing MakerWorld hardware",
    "makerworld_wrong_quantity": "Wrong MakerWorld quantity",
    "makerworld_parse_error": "MakerWorld parse error",
    "makerworld_other": "Other MakerWorld issue",
}


def issue_type_label(issue_type: str) -> str:
    return _ISSUE_LABELS.get(issue_type, issue_type.replace("_", " ").title())


def report_title(report: MatchErrorReport) -> str:
    side = "MakerWorld" if report.report_side == "makerworld" else "McMaster"
    part_hint = ""
    if report.part and report.part.original_name:
        part_hint = f" — {report.part.original_name}"
    elif report.makerworld_line_text:
        part_hint = f" — {report.makerworld_line_text[:60]}"
    return f"[{side} report] {issue_type_label(report.issue_type)}{part_hint}"


def _part_section(report: MatchErrorReport) -> list[str]:
    lines: list[str] = []
    if report.part:
        lines.append(f"- **Part:** {report.part.original_name}")
        if report.part.specification:
            lines.append(f"- **Spec:** {report.part.specification}")
        if report.part.mcmaster_part_number:
            lines.append(f"- **Matched SKU:** `{report.part.mcmaster_part_number}`")
        if report.part.mcmaster_url:
            lines.append(f"- **Matched URL:** {report.part.mcmaster_url}")
        if report.part.match_tier:
            lines.append(f"- **Match tier:** {report.part.match_tier}")
    if report.part_index is not None:
        lines.append(f"- **Part index:** {report.part_index}")
    return lines


def report_markdown(report: MatchErrorReport, *, github_issue_url: str = "") -> str:
    lines = [
        f"**Report ID:** `{report.id}`",
        f"**Reported at:** {report.reported_at}",
        f"**Side:** {report.report_side}",
        f"**Issue type:** {issue_type_label(report.issue_type)}",
        "",
        "## Description",
        report.message,
        "",
    ]
    if report.project_title or report.project_id:
        lines.extend(
            [
                "## Project",
                f"- **Title:** {report.project_title or '—'}",
                f"- **Project ID:** `{report.project_id or '—'}`",
            ]
        )
    if report.makerworld_url:
        lines.append(f"- **MakerWorld:** {report.makerworld_url}")
    if report.page_url:
        lines.append(f"- **Page:** {report.page_url}")
    if report.reporter_email:
        lines.append(f"- **Reporter email:** {report.reporter_email}")
    lines.append("")

    part_lines = _part_section(report)
    if part_lines:
        lines.append("## BOM line")
        lines.extend(part_lines)
        lines.append("")

    corrections: list[str] = []
    if report.expected_part_number:
        corrections.append(f"- **Expected part #:** `{report.expected_part_number}`")
    if report.expected_url:
        corrections.append(f"- **Expected URL:** {report.expected_url}")
    if report.expected_finish:
        corrections.append(f"- **Expected finish:** {report.expected_finish}")
    if report.makerworld_line_text:
        corrections.append(f"- **MakerWorld line:** {report.makerworld_line_text}")
    if report.expected_line_text:
        corrections.append(f"- **Expected line:** {report.expected_line_text}")
    if report.expected_quantity is not None:
        corrections.append(f"- **Expected quantity:** {report.expected_quantity:g}")
    if report.parse_context:
        corrections.append(f"- **Parse context:** {report.parse_context}")
    if corrections:
        lines.append("## Expected correction")
        lines.extend(corrections)
        lines.append("")

    if github_issue_url:
        lines.append(f"---\nGitHub issue: {github_issue_url}")

    return "\n".join(lines)


def report_plain_text(report: MatchErrorReport) -> str:
    return (
        report_markdown(report)
        .replace("**", "")
        .replace("`", "")
        .replace("## ", "\n")
    )


def webhook_payload(
    report: MatchErrorReport,
    *,
    github_issue_url: str = "",
) -> dict[str, object]:
    part_name = report.part.original_name if report.part else ""
    return {
        "event": "match_error_report",
        "report_id": report.id,
        "reported_at": report.reported_at,
        "report_side": report.report_side,
        "issue_type": report.issue_type,
        "issue_label": issue_type_label(report.issue_type),
        "title": report_title(report),
        "message": report.message,
        "project_id": report.project_id,
        "project_title": report.project_title,
        "makerworld_url": report.makerworld_url,
        "page_url": report.page_url,
        "part_index": report.part_index,
        "part_name": part_name,
        "expected_part_number": report.expected_part_number,
        "expected_url": report.expected_url,
        "github_issue_url": github_issue_url,
    }


def discord_embed_payload(report: MatchErrorReport, *, github_issue_url: str = "") -> dict:
    description = report.message[:1800]
    fields: list[dict[str, object]] = [
        {"name": "Side", "value": report.report_side, "inline": True},
        {"name": "Type", "value": issue_type_label(report.issue_type), "inline": True},
        {"name": "Report ID", "value": report.id, "inline": False},
    ]
    if report.part and report.part.original_name:
        fields.append({"name": "BOM line", "value": report.part.original_name[:256], "inline": False})
    if report.page_url:
        fields.append({"name": "Page", "value": report.page_url[:256], "inline": False})
    if github_issue_url:
        fields.append({"name": "GitHub", "value": github_issue_url, "inline": False})

    return {
        "embeds": [
            {
                "title": report_title(report)[:256],
                "description": description,
                "color": 0xE4572E,
                "fields": fields,
            }
        ]
    }
