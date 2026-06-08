"""Integration catalog — solo builders + extended Composio toolkits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class IntegrationInfo:
    slug: str
    label: str
    blurb: str
    recommended: bool
    solo_default: bool
    category: str = "core"  # core | productivity | comms | dev


INTEGRATIONS: List[IntegrationInfo] = [
    IntegrationInfo(
        slug="github",
        label="GitHub",
        blurb="Whole account — PRs, issues, commits across repos",
        recommended=True,
        solo_default=True,
        category="dev",
    ),
    IntegrationInfo(
        slug="gmail",
        label="Gmail",
        blurb="Inbox triage + Harbor can auto-send project updates",
        recommended=True,
        solo_default=True,
        category="comms",
    ),
    IntegrationInfo(
        slug="slack",
        label="Slack",
        blurb="Broadcast briefs and build updates to a channel",
        recommended=False,
        solo_default=False,
        category="comms",
    ),
    IntegrationInfo(
        slug="notion",
        label="Notion",
        blurb="Pages and databases — agent can read/write your workspace",
        recommended=True,
        solo_default=False,
        category="productivity",
    ),
    IntegrationInfo(
        slug="googlecalendar",
        label="Google Calendar",
        blurb="Upcoming events and schedule context for planning",
        recommended=False,
        solo_default=False,
        category="productivity",
    ),
    IntegrationInfo(
        slug="googlesheets",
        label="Google Sheets",
        blurb="Spreadsheets for specs, metrics, and launch checklists",
        recommended=False,
        solo_default=False,
        category="productivity",
    ),
    IntegrationInfo(
        slug="googledrive",
        label="Google Drive",
        blurb="Files and docs tied to your build",
        recommended=False,
        solo_default=False,
        category="productivity",
    ),
    IntegrationInfo(
        slug="discord",
        label="Discord",
        blurb="Post updates to a server channel",
        recommended=False,
        solo_default=False,
        category="comms",
    ),
    IntegrationInfo(
        slug="trello",
        label="Trello",
        blurb="External boards — optional alongside Harbor Board",
        recommended=False,
        solo_default=False,
        category="productivity",
    ),
    IntegrationInfo(
        slug="jira",
        label="Jira",
        blurb="Enterprise tickets — optional external sync",
        recommended=False,
        solo_default=False,
        category="dev",
    ),
    IntegrationInfo(
        slug="airtable",
        label="Airtable",
        blurb="Bases and records for specs and CRM-style tracking",
        recommended=False,
        solo_default=False,
        category="productivity",
    ),
    IntegrationInfo(
        slug="asana",
        label="Asana",
        blurb="Tasks and projects in Asana",
        recommended=False,
        solo_default=False,
        category="productivity",
    ),
    IntegrationInfo(
        slug="linear",
        label="Linear",
        blurb="Optional — Harbor Board is your default; use Linear if you already live there",
        recommended=False,
        solo_default=False,
        category="dev",
    ),
]

ALL_TOOLKIT_SLUGS = [i.slug for i in INTEGRATIONS]
SOLO_DEFAULT_TOOLKITS = [i.slug for i in INTEGRATIONS if i.solo_default]


def integration_map() -> Dict[str, IntegrationInfo]:
    return {i.slug: i for i in INTEGRATIONS}


def morning_brief_instructions(
    *,
    connected: Dict[str, bool],
    slack_ready: bool,
) -> str:
    sections: List[str] = []
    if connected.get("github"):
        sections.append("GitHub")
    if connected.get("gmail"):
        sections.append("Gmail")
    if connected.get("notion"):
        sections.append("Notion")
    if connected.get("googlecalendar"):
        sections.append("Calendar")
    sections.extend(["Harbor Board", "Market intel", "Actions"])

    actions: List[str] = [
        f"Write a morning brief under 400 words with sections: {', '.join(sections)}.",
        "Reference Harbor Board items in Backlog/Building columns when relevant.",
        "Be specific — cite PR numbers, card titles, and URLs when available.",
    ]

    if connected.get("slack") and slack_ready:
        actions.append("Post the brief to Slack using SLACK_SEND_MESSAGE.")
    else:
        actions.append("Put the full brief in your final reply for the terminal.")

    if connected.get("gmail"):
        actions.append("Flag urgent unanswered emails in Actions.")

    return "\n".join(f"{i}. {line}" for i, line in enumerate(actions, start=1))


def incident_instructions(
    *,
    connected: Dict[str, bool],
    slack_ready: bool,
) -> str:
    steps: List[str] = ["Write a severity assessment with blast radius."]
    if connected.get("slack") and slack_ready:
        steps.append("Post a status update to Slack.")
    if connected.get("discord"):
        steps.append("Post a short status to Discord if configured.")
    if connected.get("github"):
        steps.append("If a matching GitHub issue exists, add a comment.")
    if connected.get("jira"):
        steps.append("Create or update a Jira incident ticket.")
    if not any(connected.get(k) for k in ("slack", "discord", "github", "jira")):
        steps.append("Deliver the full incident report in your final reply.")
    return "\n".join(f"{i}. {step}" for i, step in enumerate(steps, start=1))
