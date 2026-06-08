"""Composio integration — GitHub, Slack, Linear, Gmail action layer."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from supercompress.stack._paths import FIXTURES
from supercompress.stack.config import Settings, get_settings
from supercompress.stack.integrations import ALL_TOOLKIT_SLUGS

logger = logging.getLogger(__name__)


def normalize_composio_slug(slug: str) -> str:
    """Map Composio toolkit slugs to our dashboard slugs."""
    s = str(slug or "").lower().strip().replace("-", "").replace("_", "")
    aliases = {
        "googlecalendar": "googlecalendar",
        "googlecal": "googlecalendar",
    }
    return aliases.get(s, s)


@dataclass
class ConnectResult:
    """OAuth connect link from Composio."""

    toolkit: str
    redirect_url: Optional[str] = None
    already_connected: bool = False
    error: Optional[str] = None


@dataclass
class ComposioActionResult:
    action: str
    success: bool
    data: Any
    error: Optional[str] = None


@dataclass
class GitHubSnapshot:
    prs_needing_review: List[Dict[str, Any]] = field(default_factory=list)
    open_issues: List[Dict[str, Any]] = field(default_factory=list)
    recent_commits: List[Dict[str, Any]] = field(default_factory=list)

    def to_context_block(self) -> str:
        lines = ["## GitHub (Composio)"]
        if self.prs_needing_review:
            lines.append("\n### PRs needing your review")
            for pr in self.prs_needing_review[:10]:
                lines.append(
                    f"- #{pr.get('number')} {pr.get('title')} — {pr.get('html_url', pr.get('url', ''))}"
                )
        if self.open_issues:
            lines.append("\n### Open issues")
            for issue in self.open_issues[:10]:
                lines.append(f"- #{issue.get('number')} {issue.get('title')}")
        if self.recent_commits:
            lines.append("\n### Recent commits (across your repos)")
            for c in self.recent_commits[:8]:
                repo = c.get("_repo", c.get("repository", {}).get("full_name", ""))
                msg = c.get("message", c.get("commit", {}).get("message", ""))[:80]
                prefix = f"[{repo}] " if repo else ""
                lines.append(f"- {c.get('sha', '')[:7]} {prefix}{msg}")
        return "\n".join(lines) if len(lines) > 1 else "## GitHub\nNo data."


@dataclass
class LinearSnapshot:
    blocked: List[Dict[str, Any]] = field(default_factory=list)
    in_progress: List[Dict[str, Any]] = field(default_factory=list)
    urgent: List[Dict[str, Any]] = field(default_factory=list)

    def to_context_block(self) -> str:
        lines = ["## Linear (Composio)"]
        for label, items in [
            ("Blocked", self.blocked),
            ("In Progress", self.in_progress),
            ("Urgent", self.urgent),
        ]:
            if items:
                lines.append(f"\n### {label}")
                for item in items[:8]:
                    lines.append(f"- {item.get('identifier', item.get('id', '?'))} {item.get('title', '')}")
        return "\n".join(lines) if len(lines) > 1 else "## Linear\nNo data."


@dataclass
class GmailSnapshot:
    unanswered: List[Dict[str, Any]] = field(default_factory=list)
    important: List[Dict[str, Any]] = field(default_factory=list)

    def to_context_block(self) -> str:
        lines = ["## Gmail (Composio)"]
        if self.unanswered:
            lines.append("\n### Unanswered (24h)")
            for m in self.unanswered[:8]:
                lines.append(f"- From: {m.get('from', m.get('sender', '?'))} — {m.get('subject', '')}")
        if self.important:
            lines.append("\n### Important")
            for m in self.important[:5]:
                lines.append(f"- {m.get('subject', '')}")
        return "\n".join(lines) if len(lines) > 1 else "## Gmail\nNo data."


@dataclass
class ComposioGatherResult:
    github: GitHubSnapshot
    linear: LinearSnapshot
    gmail: GmailSnapshot
    raw_actions: List[ComposioActionResult] = field(default_factory=list)

    def all_context_blocks(self) -> List[str]:
        blocks: List[str] = []
        gh = self.github.to_context_block()
        if "No data" not in gh:
            blocks.append(gh)
        lin = self.linear.to_context_block()
        if "No data" not in lin:
            blocks.append(lin)
        gm = self.gmail.to_context_block()
        if "No data" not in gm:
            blocks.append(gm)
        return blocks or ["## Connected apps\nNo integration data yet — run `supercompress connect github`."]


class ComposioHub:
    """Session-based Composio hub with multi-toolkit gather + execute."""

    TOOLKITS = ALL_TOOLKIT_SLUGS

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._composio = None
        self._session = None
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._tools_cache_key: Optional[tuple[str, ...]] = None
        self._connected_cache: Optional[set[str]] = None

    def connected_toolkits(self) -> set[str]:
        """OAuth-connected toolkits for this harbor user."""
        if self._connected_cache is not None:
            return self._connected_cache
        slugs: set[str] = set()
        try:
            listed = self.composio.connected_accounts.list(
                user_ids=[self.settings.harbor_user_id],
                statuses=["ACTIVE"],
                limit=50,
            )
            for item in getattr(listed, "items", None) or []:
                raw_slug = None
                toolkit = getattr(item, "toolkit", None)
                if toolkit is not None:
                    raw_slug = getattr(toolkit, "slug", None) or getattr(toolkit, "name", None)
                if not raw_slug:
                    raw_slug = getattr(item, "toolkit_slug", None) or getattr(item, "integration_id", None)
                if raw_slug:
                    slugs.add(normalize_composio_slug(str(raw_slug)))
        except Exception as exc:
            logger.warning("Composio connected_accounts.list failed: %s", exc)
        self._connected_cache = slugs
        return slugs

    def dashboard_linked(self, toolkits: List[str]) -> List[str]:
        """Toolkits from dashboard list that are OAuth-connected for this user."""
        connected = self.connected_toolkits()
        return [tk for tk in toolkits if tk in connected]

    def integration_status(self) -> Dict[str, bool]:
        connected = self.connected_toolkits()
        return {slug: slug in connected for slug in self.TOOLKITS}

    def _toolkits_for_session(self) -> List[str]:
        """Configured toolkits that are also OAuth-connected."""
        wanted = self.settings.active_toolkits()
        connected = self.connected_toolkits()
        if not connected:
            return wanted
        active = [slug for slug in wanted if slug in connected]
        return active or wanted

    def invalidate_cache(self) -> None:
        self._tools_cache = None
        self._tools_cache_key = None
        self._connected_cache = None

    @property
    def composio(self):
        if self._composio is None:
            import os

            from composio import Composio
            from composio_openai import OpenAIProvider

            if self.settings.composio_api_key:
                os.environ.setdefault("COMPOSIO_API_KEY", self.settings.composio_api_key)
            self._composio = Composio(provider=OpenAIProvider())
        return self._composio

    @property
    def session(self):
        if self._session is None:
            self._session = self.composio.create(user_id=self.settings.harbor_user_id)
        return self._session

    def get_openai_tools(self, toolkits: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        kits = toolkits or self._toolkits_for_session()
        cache_key = tuple(sorted(kits))
        if self._tools_cache_key == cache_key and self._tools_cache is not None:
            return self._tools_cache
        if not kits:
            return []
        tools = self.composio.tools.get(
            user_id=self.settings.harbor_user_id,
            toolkits=kits,
            limit=100,
        )
        self._tools_cache = tools
        self._tools_cache_key = cache_key
        return tools

    def execute(self, action: str, arguments: Dict[str, Any]) -> ComposioActionResult:
        try:
            result = self.composio.tools.execute(
                action,
                user_id=self.settings.harbor_user_id,
                arguments=arguments,
            )
            return ComposioActionResult(action=action, success=True, data=result)
        except Exception as exc:
            return ComposioActionResult(action=action, success=False, data=None, error=str(exc))

    def _safe_list(self, action: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        res = self.execute(action, arguments)
        if not res.success or res.data is None:
            return []
        data = res.data
        if isinstance(data, dict):
            if "data" in data:
                inner = data["data"]
                if isinstance(inner, dict):
                    for key in (
                        "pull_requests", "issues", "items", "issues_list",
                        "messages", "commits", "repositories", "search_results",
                    ):
                        if key in inner and isinstance(inner[key], list):
                            return inner[key]
                    if "response_data" in inner and isinstance(inner["response_data"], list):
                        return inner["response_data"]
                if isinstance(inner, list):
                    return inner
            for key in ("pull_requests", "issues", "items", "messages", "commits", "repositories"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        if isinstance(data, list):
            return data
        return []

    def gather_github(self) -> GitHubSnapshot:
        """Account-wide GitHub via Composio OAuth — optional owner/repo narrows scope."""
        owner = self.settings.github_owner.strip() if self.settings.github_owner else ""
        repo = self.settings.github_repo.strip() if self.settings.github_repo else ""
        snap = GitHubSnapshot()

        if owner and repo:
            prs = self._safe_list(
                "GITHUB_LIST_PULL_REQUESTS",
                {"owner": owner, "repo": repo, "state": "open"},
            )
            snap.prs_needing_review = [p for p in prs if p.get("draft") is not True][:15]
            snap.open_issues = self._safe_list(
                "GITHUB_LIST_REPOSITORY_ISSUES",
                {"owner": owner, "repo": repo, "state": "open"},
            )[:15]
            snap.recent_commits = self._safe_list(
                "GITHUB_LIST_COMMITS",
                {"owner": owner, "repo": repo, "per_page": 10},
            )[:10]
            return snap

        snap.prs_needing_review = self._safe_list(
            "GITHUB_FIND_PULL_REQUESTS",
            {"q": "is:open is:pr review-requested:@me archived:false", "per_page": 20},
        )[:20]

        snap.open_issues = self._safe_list(
            "GITHUB_FIND_PULL_REQUESTS",
            {"q": "is:open is:issue assignee:@me archived:false", "per_page": 15},
        )[:15]

        repos = self._safe_list(
            "GITHUB_FIND_REPOSITORIES",
            {"q": "sort:updated fork:true", "per_page": 8},
        )
        for r in repos:
            full = r.get("full_name") or r.get("name", "")
            if "/" not in full:
                continue
            o, rn = full.split("/", 1)
            commits = self._safe_list(
                "GITHUB_LIST_COMMITS",
                {"owner": o, "repo": rn, "per_page": 2},
            )
            for c in commits:
                c["_repo"] = full
            snap.recent_commits.extend(commits)
            if len(snap.recent_commits) >= 10:
                break
        snap.recent_commits = snap.recent_commits[:10]
        return snap

    def gather_linear(self) -> LinearSnapshot:
        """All issues visible to your Linear account (no team plan required)."""
        snap = LinearSnapshot()
        issues = self._safe_list("LINEAR_LIST_LINEAR_ISSUES", {"first": 50})
        for issue in issues:
            state = str(issue.get("state", issue.get("state_name", ""))).lower()
            priority = issue.get("priority", 0)
            if "block" in state or issue.get("blocked"):
                snap.blocked.append(issue)
            elif "progress" in state or "started" in state:
                snap.in_progress.append(issue)
            if priority in (1, "urgent", "Urgent") or issue.get("priority_label") == "Urgent":
                snap.urgent.append(issue)
        return snap

    def gather_gmail(self) -> GmailSnapshot:
        snap = GmailSnapshot()
        messages = self._safe_list(
            "GMAIL_FETCH_EMAILS",
            {"max_results": 20, "query": "is:unread newer_than:1d"},
        )
        snap.unanswered = messages[:15]
        important = self._safe_list(
            "GMAIL_FETCH_EMAILS",
            {"max_results": 10, "query": "is:important newer_than:3d"},
        )
        snap.important = important[:10]
        return snap

    def gather_all(self) -> ComposioGatherResult:
        raw: List[ComposioActionResult] = []
        connected = self.connected_toolkits()
        use = self.settings.active_toolkits()

        gh = self.gather_github() if "github" in use and (not connected or "github" in connected) else GitHubSnapshot()
        lin = self.gather_linear() if "linear" in use and (not connected or "linear" in connected) else LinearSnapshot()
        gm = self.gather_gmail() if "gmail" in use and (not connected or "gmail" in connected) else GmailSnapshot()
        return ComposioGatherResult(github=gh, linear=lin, gmail=gm, raw_actions=raw)

    def extra_toolkit_context(self) -> str:
        """Lightweight context for optional connected toolkits."""
        connected = self.connected_toolkits()
        use = set(self.settings.active_toolkits())
        labels = {
            "notion": "Notion",
            "googlecalendar": "Google Calendar",
            "googlesheets": "Google Sheets",
            "googledrive": "Google Drive",
            "discord": "Discord",
            "trello": "Trello",
            "jira": "Jira",
            "airtable": "Airtable",
            "asana": "Asana",
            "slack": "Slack",
        }
        active = [labels[s] for s in labels if s in use and s in connected]
        if not active:
            return ""
        return "## Connected toolkits\n" + ", ".join(active) + " — agent tools available via Composio."

    def slack_delivery_ready(self) -> bool:
        if not self.settings.wants_toolkit("slack"):
            return False
        if "slack" not in self.connected_toolkits():
            return False
        return bool(self.settings.slack_ready() or self._resolve_slack_channel())

    def _resolve_slack_channel(self) -> Optional[str]:
        if self.settings.slack_channel_id.strip():
            return self.settings.slack_channel_id.strip()
        channels = self._safe_list(
            "SLACK_LIST_ALL_CHANNELS",
            {"types": "public_channel,private_channel", "limit": 100},
        )
        for ch in channels:
            if (ch.get("name") or "").lower() in ("general", "random", "build", "dev", "engineering"):
                cid = ch.get("id")
                if cid:
                    return str(cid)
        for ch in channels:
            cid = ch.get("id")
            if cid:
                return str(cid)
        return None

    def post_slack_digest(self, text: str, channel: Optional[str] = None) -> ComposioActionResult:
        if "slack" not in self.connected_toolkits():
            return ComposioActionResult(
                action="SLACK_SEND_MESSAGE",
                success=False,
                data=None,
                error="Slack not connected — run `supercompress connect slack` or skip Slack for solo use",
            )
        ch = channel or self._resolve_slack_channel()
        if not ch:
            return ComposioActionResult(
                action="SLACK_SEND_MESSAGE",
                success=False,
                data=None,
                error="Set SLACK_CHANNEL_ID in .env or connect Slack with a workspace channel",
            )
        return self.execute(
            "SLACK_SEND_MESSAGE",
            {"channel": ch, "text": text},
        )

    def _resolve_linear_team_id(self) -> Optional[str]:
        if self.settings.linear_team_id:
            return self.settings.linear_team_id
        teams = self._safe_list("LINEAR_LIST_LINEAR_TEAMS", {})
        for team in teams:
            tid = team.get("id") or team.get("team_id")
            if tid:
                return str(tid)
        return None

    def create_linear_issue(
        self,
        title: str,
        description: str,
        team_id: Optional[str] = None,
    ) -> ComposioActionResult:
        args: Dict[str, Any] = {"title": title, "description": description}
        tid = team_id or self._resolve_linear_team_id()
        if tid:
            args["team_id"] = tid
        return self.execute("LINEAR_CREATE_LINEAR_ISSUE", args)

    def update_linear_issue(
        self,
        issue_id: str,
        *,
        description: Optional[str] = None,
        title: Optional[str] = None,
    ) -> ComposioActionResult:
        args: Dict[str, Any] = {"issue_id": issue_id}
        if description is not None:
            args["description"] = description
        if title is not None:
            args["title"] = title
        return self.execute("LINEAR_UPDATE_ISSUE", args)

    def create_github_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        *,
        labels: Optional[List[str]] = None,
    ) -> ComposioActionResult:
        args: Dict[str, Any] = {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
        }
        if labels:
            args["labels"] = labels
        return self.execute("GITHUB_CREATE_AN_ISSUE", args)

    def create_gmail_draft(
        self,
        subject: str,
        body: str,
        *,
        to: str = "me",
    ) -> ComposioActionResult:
        return self.execute(
            "GMAIL_CREATE_EMAIL_DRAFT",
            {"recipient": to, "subject": subject, "body": body},
        )

    def send_gmail(
        self,
        subject: str,
        body: str,
        *,
        to: Optional[str] = None,
    ) -> ComposioActionResult:
        recipient = to or self.settings.harbor_gmail_to or "me"
        return self.execute(
            "GMAIL_SEND_EMAIL",
            {"recipient_email": recipient, "subject": subject, "body": body},
        )

    def sync_gmail_message(self, subject: str, body: str, *, to: Optional[str] = None) -> ComposioActionResult:
        if self.settings.gmail_sends_immediately():
            return self.send_gmail(subject, body, to=to)
        return self.create_gmail_draft(subject, body, to=to or self.settings.harbor_gmail_to)

    def create_notion_page(self, title: str, content: str) -> ComposioActionResult:
        return self.execute(
            "NOTION_CREATE_NOTION_PAGE",
            {"title": title, "content": content},
        )

    def post_discord_message(self, content: str, *, channel_id: Optional[str] = None) -> ComposioActionResult:
        args: Dict[str, Any] = {"content": content[:2000]}
        if channel_id:
            args["channel_id"] = channel_id
        return self.execute("DISCORD_SEND_MESSAGE", args)

    def draft_gmail_reply(self, thread_id: str, body: str) -> ComposioActionResult:
        return self.execute(
            "GMAIL_REPLY_TO_THREAD",
            {"thread_id": thread_id, "message_body": body},
        )

    def create_github_comment(self, owner: str, repo: str, issue_number: int, body: str) -> ComposioActionResult:
        return self.execute(
            "GITHUB_CREATE_ISSUE_COMMENT",
            {"owner": owner, "repo": repo, "issue_number": issue_number, "body": body},
        )

    def _resolve_auth_config_id(self, toolkit: str) -> str:
        """Find or create a Composio-managed auth config for a toolkit slug."""
        slug = toolkit.lower().strip()
        listed = self.composio.auth_configs.list(toolkit_slug=slug)
        items = list(getattr(listed, "items", None) or [])
        for item in items:
            if getattr(item, "status", "") == "ENABLED":
                return item.id
        if items:
            return items[0].id
        created = self.composio.auth_configs.create(
            slug,
            {"type": "use_composio_managed_auth", "name": f"SuperCompress {slug}"},
        )
        return created.id

    def auth_connect(self, toolkit: str) -> ConnectResult:
        """Start Composio OAuth for a toolkit; returns a real redirect URL."""
        slug = toolkit.lower().strip()
        if slug not in self.TOOLKITS:
            return ConnectResult(
                toolkit=slug,
                error=f"Unknown toolkit '{slug}'. Use: {', '.join(self.TOOLKITS)}",
            )
        try:
            auth_config_id = self._resolve_auth_config_id(slug)
            req = self.composio.connected_accounts.link(
                user_id=self.settings.harbor_user_id,
                auth_config_id=auth_config_id,
            )
            self.invalidate_cache()
            url = req.redirect_url
            if url and url.startswith(("http://", "https://")):
                return ConnectResult(toolkit=slug, redirect_url=url)
            return ConnectResult(
                toolkit=slug,
                error="Composio did not return a redirect URL. Try again at https://dashboard.composio.dev",
            )
        except Exception as exc:
            from composio import exceptions as composio_exc

            if isinstance(exc, composio_exc.ComposioMultipleConnectedAccountsError):
                return ConnectResult(toolkit=slug, already_connected=True)
            return ConnectResult(toolkit=slug, error=str(exc))

    def auth_connect_url(self, toolkit: str) -> Optional[str]:
        """Return OAuth redirect URL, or None if already connected / failed."""
        result = self.auth_connect(toolkit)
        return result.redirect_url

    def wait_for_connection(
        self,
        toolkit: str,
        *,
        timeout_sec: int = 180,
        poll_sec: float = 3.0,
    ) -> ConnectResult:
        """Poll until toolkit OAuth completes or timeout."""
        import time

        slug = toolkit.lower().strip()
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            self.invalidate_cache()
            if slug in self.connected_toolkits():
                return ConnectResult(toolkit=slug, already_connected=True)
            time.sleep(poll_sec)
        return ConnectResult(
            toolkit=slug,
            error=f"Timed out waiting for {slug} OAuth ({timeout_sec}s). Run supercompress connect {slug} again.",
        )

    def connection_summary(self) -> Dict[str, Any]:
        """Enabled vs OAuth-linked toolkits for doctor/dashboard."""
        enabled = self.settings.active_toolkits()
        connected = self.integration_status()
        linked = [s for s in enabled if connected.get(s)]
        missing = [s for s in enabled if not connected.get(s)]
        return {
            "enabled": enabled,
            "linked": linked,
            "missing_oauth": missing,
            "all_linked": not missing,
        }

    @property
    def mcp_url(self) -> str:
        return self.session.mcp.url


class DemoComposioHub(ComposioHub):
    """Fixture-backed Composio for demo/CI."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(settings)
        self._fixture_dir = FIXTURES

    def connected_toolkits(self) -> set[str]:
        return set(self.settings.active_toolkits())

    def integration_status(self) -> Dict[str, bool]:
        return {slug: slug in self.connected_toolkits() for slug in self.TOOLKITS}

    def _toolkits_for_session(self) -> List[str]:
        return self.settings.active_toolkits()

    def connection_summary(self) -> Dict[str, Any]:
        enabled = self.settings.active_toolkits()
        connected = self.integration_status()
        linked = [slug for slug in enabled if connected.get(slug)]
        missing = [slug for slug in enabled if not connected.get(slug)]
        return {
            "enabled": enabled,
            "linked": linked,
            "missing_oauth": missing,
            "all_linked": not missing,
        }

    def slack_delivery_ready(self) -> bool:
        return self.settings.wants_toolkit("slack")

    def _load(self, name: str) -> Dict[str, Any]:
        return json.loads((self._fixture_dir / name).read_text())

    def gather_github(self) -> GitHubSnapshot:
        data = self._load("github_snapshot.json")
        return GitHubSnapshot(**data)

    def gather_linear(self) -> LinearSnapshot:
        data = self._load("linear_snapshot.json")
        return LinearSnapshot(**data)

    def gather_gmail(self) -> GmailSnapshot:
        data = self._load("gmail_snapshot.json")
        return GmailSnapshot(**data)

    def get_openai_tools(self, toolkits: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        kits = set(toolkits or self._toolkits_for_session())
        tools: List[Dict[str, Any]] = []
        if "slack" in kits:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "SLACK_SEND_MESSAGE",
                        "description": "Post a message to Slack",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "channel": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["channel", "text"],
                        },
                    },
                }
            )
        if "linear" in kits:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "LINEAR_CREATE_LINEAR_ISSUE",
                        "description": "Create a Linear issue",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["title", "description"],
                        },
                    },
                }
            )
        if "github" in kits:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "GITHUB_CREATE_ISSUE_COMMENT",
                        "description": "Comment on a GitHub issue",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "owner": {"type": "string"},
                                "repo": {"type": "string"},
                                "issue_number": {"type": "integer"},
                                "body": {"type": "string"},
                            },
                            "required": ["owner", "repo", "issue_number", "body"],
                        },
                    },
                }
            )
        return tools

    def execute(self, action: str, arguments: Dict[str, Any]) -> ComposioActionResult:
        return ComposioActionResult(action=action, success=True, data={"demo": True, "arguments": arguments})

    def post_slack_digest(self, text: str, channel: Optional[str] = None) -> ComposioActionResult:
        return self.execute("SLACK_SEND_MESSAGE", {"channel": channel or "C-demo", "text": text})

    def create_linear_issue(self, title: str, description: str, team_id: Optional[str] = None) -> ComposioActionResult:
        return self.execute(
            "LINEAR_CREATE_LINEAR_ISSUE",
            {"title": title, "description": description, "team_id": team_id},
        )

    def update_linear_issue(self, issue_id: str, *, description: Optional[str] = None, title: Optional[str] = None) -> ComposioActionResult:
        args: Dict[str, Any] = {"issue_id": issue_id}
        if description is not None:
            args["description"] = description
        if title is not None:
            args["title"] = title
        return self.execute("LINEAR_UPDATE_ISSUE", args)

    def create_github_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        *,
        labels: Optional[List[str]] = None,
    ) -> ComposioActionResult:
        return self.execute(
            "GITHUB_CREATE_AN_ISSUE",
            {"owner": owner, "repo": repo, "title": title, "body": body, "labels": labels or []},
        )

    def create_gmail_draft(self, subject: str, body: str, *, to: str = "me") -> ComposioActionResult:
        return self.execute("GMAIL_CREATE_EMAIL_DRAFT", {"recipient": to, "subject": subject, "body": body})

    def send_gmail(self, subject: str, body: str, *, to: Optional[str] = None) -> ComposioActionResult:
        return self.execute("GMAIL_SEND_EMAIL", {"recipient_email": to or "me", "subject": subject, "body": body})

    def sync_gmail_message(self, subject: str, body: str, *, to: Optional[str] = None) -> ComposioActionResult:
        if self.settings.gmail_sends_immediately():
            return self.send_gmail(subject, body, to=to)
        return self.create_gmail_draft(subject, body, to=to or "me")

    def create_notion_page(self, title: str, content: str) -> ComposioActionResult:
        return self.execute("NOTION_CREATE_NOTION_PAGE", {"title": title, "content": content})

    def post_discord_message(self, content: str, *, channel_id: Optional[str] = None) -> ComposioActionResult:
        return self.execute("DISCORD_SEND_MESSAGE", {"content": content, "channel_id": channel_id or ""})

    def auth_connect(self, toolkit: str) -> ConnectResult:
        slug = toolkit.lower().strip()
        return ConnectResult(
            toolkit=slug,
            redirect_url=f"https://connect.composio.dev/link/demo?toolkit={slug}",
        )


def get_composio(settings: Optional[Settings] = None) -> ComposioHub:
    s = settings or get_settings()
    if s.demo_mode or not s.has_composio():
        return DemoComposioHub(s)
    return ComposioHub(s)
