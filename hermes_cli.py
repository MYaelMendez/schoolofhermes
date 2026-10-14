#!/usr/bin/env python3
"""
hermes_cli.py — the Hermes Agent CLI, expressed in Python.

A structural model of the hermes CLI, transcribed from:
  1. references/cli-reference.md (curated skill reference)
  2. hermes --help (live ground truth on this host)

The model is data, not reimplementation — it describes the grammar
(surfaces, flags, subcommands, paths) so a Python tool or agent can
reason about the CLI without shelling out.

Grammar:
    hermes [global_flags] [command [subcommand [args...]]]

    no subcommand = interactive chat
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Global flags — apply to ANY invocation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Flag:
    names: tuple[str, ...]
    dest: str
    help: str
    takes_value: bool = True

    @property
    def long(self) -> str:
        return next((n for n in self.names if n.startswith("--")), self.names[0])


GLOBAL_FLAGS: tuple[Flag, ...] = (
    Flag(("--version", "-V"), "version", "Show version", takes_value=False),
    Flag(("-z", "--oneshot"), "oneshot", "One-shot: print ONLY the final response (for scripts/pipes)"),
    Flag(("-m", "--model"), "model", "Model override for this invocation"),
    Flag(("--provider",), "provider", "Provider override for this invocation"),
    Flag(("-t", "--toolsets"), "toolsets", "Comma-separated toolsets for this invocation"),
    Flag(("-r", "--resume"), "resume", "Resume session by ID or title"),
    Flag(("-c", "--continue"), "continue", "Resume by name, or most recent session"),
    Flag(("-w", "--worktree"), "worktree", "Isolated git worktree mode (parallel agents)", takes_value=False),
    Flag(("-s", "--skills"), "skills", "Preload skills (comma-separated or repeat)"),
    Flag(("-p", "--profile"), "profile", "Use a named profile"),
    Flag(("--yolo",), "yolo", "Skip dangerous command approval", takes_value=False),
    Flag(("--tui",), "tui", "Force the Ink TUI surface", takes_value=False),
    Flag(("--cli",), "cli", "Force classic REPL", takes_value=False),
    Flag(("--ignore-rules",), "ignore_rules", "Skip AGENTS.md/SOUL.md/memory/skill injection", takes_value=False),
    Flag(("--safe-mode",), "safe_mode", "Disable ALL customizations (troubleshooting)", takes_value=False),
    Flag(("--pass-session-id",), "pass_session_id", "Include session ID in system prompt", takes_value=False),
)


# ---------------------------------------------------------------------------
# Command tree
# ---------------------------------------------------------------------------

@dataclass
class Command:
    """A hermes subcommand (possibly with its own subcommands)."""
    name: str
    help: str
    subcommands: dict[str, str] = field(default_factory=dict)
    flags: tuple[Flag, ...] = ()
    args: tuple[str, ...] = ()

    def full_help(self) -> str:
        """One-line summary including subcommands, if any."""
        parts = [self.help]
        if self.subcommands:
            subs = " | ".join(self.subcommands)
            parts.append(f"[{subs}]")
        return " — ".join(parts)


COMMANDS: dict[str, Command] = {
    # ── chat ──────────────────────────────────────────────────────
    "chat": Command(
        "chat",
        "Interactive chat with the agent",
        flags=(
            Flag(("-q", "--query"), "query", "Single query, non-interactive"),
            Flag(("--image",), "image", "Attach a local image to a single query"),
            Flag(("-Q", "--quiet"), "quiet", "Suppress banner, spinner, tool previews", takes_value=False),
            Flag(("--checkpoints",), "checkpoints", "Enable filesystem checkpoints (/rollback)", takes_value=False),
            Flag(("--max-turns",), "max_turns", "Cap tool-calling iterations"),
            Flag(("--source",), "source", "Session source tag (default: cli)"),
        ),
    ),

    # ── config & setup ────────────────────────────────────────────
    "setup": Command("setup", "Wizard (model|tts|terminal|gateway|tools|agent)"),
    "model": Command("model", "Interactive model/provider picker"),
    "fallback": Command(
        "fallback", "Fallback provider chain",
        subcommands={"add": "Add fallback provider", "remove": "Remove fallback provider", "list": "List fallback chain"},
    ),
    "config": Command(
        "config", "View and edit configuration",
        subcommands={
            "show": "Show all config",
            "edit": "Open config in editor",
            "get": "Get a config value",
            "set": "Set a config value",
            "unset": "Remove a config key",
            "path": "Print config file path",
            "env-path": "Print .env file path",
            "check": "Validate config",
            "migrate": "Migrate deprecated settings",
        },
    ),
    "login": Command("login", "OAuth sign-in"),
    "logout": Command("logout", "Clear stored auth"),
    "doctor": Command("doctor", "Check dependencies and config", flags=(Flag(("--fix",), "fix", "Auto-fix issues", takes_value=False),)),
    "status": Command("status", "Component summary", flags=(Flag(("--full",), "full", "Every section", takes_value=False),)),
    "migrate": Command("migrate", "Migrate configuration for retired models or deprecated settings"),
    "codex-runtime": Command("codex-runtime", "Manage the optional codex app-server runtime"),

    # ── tools & skills ────────────────────────────────────────────
    "tools": Command(
        "tools", "Per-platform toolsets",
        subcommands={
            "list": "List available toolsets",
            "enable": "Enable a toolset",
            "disable": "Disable a toolset",
        },
    ),
    "skills": Command(
        "skills", "Search, install, configure, and manage skills",
        subcommands={
            "list": "List installed skills",
            "browse": "Browse Skills Hub",
            "search": "Search by query",
            "inspect": "Inspect a skill by ID",
            "install": "Install by Hub ID or direct SKILL.md URL",
            "config": "Enable/disable skills per platform",
            "check": "Check skill health",
            "update": "Update installed skills",
            "uninstall": "Remove a skill",
            "publish": "Publish a skill",
            "tap": "Add a GitHub repo as a skill source",
        },
    ),
    "bundles": Command("bundles", "Skill bundles (one /<name> alias loads several skills)"),
    "curator": Command("curator", "Background skill maintenance (status, run, pause, pin)"),

    # ── MCP ───────────────────────────────────────────────────────
    "mcp": Command(
        "mcp", "MCP server management",
        subcommands={
            "add": "Add MCP server (--url or --command)",
            "remove": "Remove MCP server",
            "list": "List MCP servers",
            "test": "Test an MCP server",
            "catalog": "Curated catalog",
            "install": "Install from catalog",
            "configure": "Toggle tool selection",
            "serve": "Run Hermes as an MCP server",
        },
    ),

    # ── gateway ───────────────────────────────────────────────────
    "gateway": Command(
        "gateway", "Messaging gateway management",
        subcommands={
            "run": "Start gateway",
            "install": "Install platform integration",
            "start": "Start daemon",
            "stop": "Stop daemon",
            "restart": "Restart daemon",
            "status": "Show gateway status",
            "setup": "Platform setup wizard",
        },
    ),

    # ── sessions ──────────────────────────────────────────────────
    "sessions": Command(
        "sessions", "Session management",
        subcommands={
            "list": "List sessions",
            "browse": "Browse sessions (reads state.db)",
            "rename": "Rename a session",
            "delete": "Delete a session",
            "export": "Export session to file",
            "prune": "Prune old sessions",
            "stats": "Session statistics",
        },
    ),

    # ── cron & webhooks ───────────────────────────────────────────
    "cron": Command(
        "cron", "Cron job management",
        subcommands={
            "list": "List schedules",
            "create": "Create schedule ('30m', 'every 2h', '0 9 * * *', ISO)",
            "edit": "Edit schedule",
            "pause": "Pause schedule",
            "resume": "Resume schedule",
            "run": "Run schedule now",
            "remove": "Remove schedule",
            "status": "Schedule status",
        },
    ),
    "webhook": Command(
        "webhook", "Manage dynamic webhook subscriptions",
        subcommands={
            "subscribe": "Subscribe to webhook",
            "list": "List subscriptions",
            "remove": "Remove subscription",
            "test": "Test webhook",
        },
    ),

    # ── profiles & credentials ────────────────────────────────────
    "profile": Command(
        "profile", "Profile management",
        subcommands={
            "list": "List profiles",
            "create": "Create profile (--clone|--clone-all|--clone-from)",
            "use": "Switch profile",
            "show": "Show current profile",
            "delete": "Delete profile",
            "rename": "Rename profile",
            "alias": "Set profile alias",
            "export": "Export profile",
            "import": "Import profile",
            "migrate-identity": "Retry a completed rename's identity migration",
        },
    ),
    "auth": Command(
        "auth", "Manage pooled provider credentials",
        subcommands={
            "add": "Add OAuth or API-key credential",
            "list": "List credentials",
            "remove": "Remove credential",
            "reset": "Reset provider credentials",
            "status": "Credential pool status",
        },
    ),

    # ── surfaces ──────────────────────────────────────────────────
    "desktop": Command("desktop", "Native desktop app"),
    "gui": Command("gui", "GUI launcher (alias for desktop)"),
    "dashboard": Command("dashboard", "Web admin panel + embedded chat", flags=(Flag(("--stop",), "stop", "Stop dashboard", takes_value=False),)),
    "proxy": Command("proxy", "Local OpenAI-compatible proxy backed by OAuth providers"),
    "portal": Command("portal", "Quick setup / sign in via Nous Portal"),
    "acp": Command("acp", "ACP server (IDE integration)"),
    "lsp": Command("lsp", "Language Server Protocol management"),

    # ── pets, skins, memory ───────────────────────────────────────
    "skin": Command(
        "skin", "List, switch, and tweak skins",
        subcommands={"list": "List skins", "use": "Activate a skin", "set": "Set skin properties"},
    ),
    "pets": Command("pets", "Browse, install, and select petdex animated pets"),
    "memory": Command(
        "memory", "Configure external memory provider",
        subcommands={"setup": "Configure provider", "status": "Show status", "off": "Disable", "reset": "Reset"},
    ),
    "secrets": Command(
        "secrets", "Manage external secret sources",
        subcommands={"bitwarden": "Bitwarden integration", "onepassword": "1Password integration"},
    ),
    "moa": Command("moa", "Configure Mixture of Agents provider/model slots"),

    # ── ops ───────────────────────────────────────────────────────
    "worktree": Command("worktree", "Audit and reclaim accumulated git worktrees and merged branches"),
    "browser": Command("browser", "Real-profile browsing helpers"),
    "hooks": Command("hooks", "Inspect and manage shell-script hooks"),
    "security": Command("security", "Supply-chain audit (OSV.dev) for venv, plugins, and MCP servers"),
    "approvals": Command("approvals", "Approval-prompt tools (mine history into allowlist proposals)"),
    "backup": Command("backup", "Back up Hermes home directory to a zip file"),
    "checkpoints": Command("checkpoints", "Inspect / prune / clear ~/.hermes/checkpoints/"),
    "import": Command("import", "Restore a Hermes backup from a zip file"),
    "import-agent": Command("import-agent", "Import a Claude Code or Codex CLI setup into Hermes"),
    "console": Command("console", "Open the safe Hermes command console"),
    "logs": Command("logs", "View agent/error logs", flags=(Flag(("-f",), "f", "Follow", takes_value=False),)),
    "send": Command("send", "Send a message to a configured platform (scripts, cron jobs, CI)"),
    "pairing": Command("pairing", "Manage DM pairing codes for user authorization"),
    "plugins": Command("plugins", "Manage and validate plugins"),
    "insights": Command("insights", "Usage insights"),
    "journey": Command("journey", "Timeline of learned skills + memories over time"),
    "computer-use": Command("computer-use", "Computer use configuration"),
    "pause": Command("pause", "Emergency stop: pause cron/kanban dispatch and new gateway turns"),
    "resume": Command("resume", "Lift the emergency stop set by `hermes pause`"),
    "dump": Command("dump", "Dump setup summary for support/debugging"),
    "debug": Command("debug", "Debug tools — upload logs and system info for support"),
    "egress": Command("egress", "Manage the iron-proxy egress credential-injection firewall"),
    "verify": Command("verify", "Detect a project's run recipe and smoke-test it"),

    # ── lifecycle ─────────────────────────────────────────────────
    "completion": Command(
        "completion", "Shell completion",
        subcommands={"bash": "Bash completion", "zsh": "Zsh completion", "fish": "Fish completion"},
    ),
    "update": Command("update", "Update Hermes"),
    "uninstall": Command("uninstall", "Uninstall Hermes"),
    "claw": Command(
        "claw", "Claw migration",
        subcommands={"migrate": "Migrate MCP config"},
    ),
    "kanban": Command("kanban", "Multi-profile collaboration board (tasks, links, comments)"),
    "project": Command("project", "Manage projects (named, multi-folder workspaces)"),
}


# ---------------------------------------------------------------------------
# Gateway platforms (20+)
# ---------------------------------------------------------------------------

GATEWAY_PLATFORMS: frozenset[str] = frozenset({
    "telegram", "discord", "slack", "whatsapp", "imessage", "signal",
    "email", "sms", "matrix", "mattermost", "teams", "line",
    "simplex", "ntfy", "google-chat", "home-assistant", "dingtalk",
    "feishu", "wecom", "weixin", "api-server", "webhooks",
})


# ---------------------------------------------------------------------------
# Canonical paths
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HermesPaths:
    HOME = "~/.hermes"
    CONFIG = "~/.hermes/config.yaml"
    ENV = "~/.hermes/.env"
    STATE_DB = "~/.hermes/state.db"
    GATEWAY_LOG = "~/.hermes/logs/gateway.log"
    CHECKPOINTS = "~/.hermes/checkpoints/"
    SKILLS = "~/.hermes/skills/"
    SESSIONS = "~/.hermes/sessions/"
    LOGS = "~/.hermes/logs/"
    AUTH = "~/.hermes/auth.json"


# ---------------------------------------------------------------------------
# Credential pool — rotates, skips exhausted keys
# ---------------------------------------------------------------------------

@dataclass
class CredentialPool:
    provider: str
    credentials: list[str] = field(default_factory=list)
    _exhausted: set[int] = field(default_factory=set)
    _cursor: int = 0

    def rotate(self) -> str:
        """Return the next credential, skipping exhausted ones."""
        if not self.credentials:
            raise ValueError(f"no credentials for {self.provider}")
        n = len(self.credentials)
        for _ in range(n):
            idx = self._cursor % n
            self._cursor += 1
            if idx not in self._exhausted:
                return self.credentials[idx]
        raise RuntimeError(f"all credentials exhausted for {self.provider}")

    def mark_exhausted(self, credential: str) -> None:
        """Mark a credential as exhausted; rotate will skip it."""
        if credential in self.credentials:
            self._exhausted.add(self.credentials.index(credential))


# ---------------------------------------------------------------------------
# The CLI itself
# ---------------------------------------------------------------------------

class HermesCLI:
    """A minimal argparse-driven shell that mirrors the real hermes CLI."""

    def __init__(self) -> None:
        self.commands = COMMANDS
        self.global_flags = GLOBAL_FLAGS
        self.paths = HermesPaths

    def has_command(self, name: str) -> bool:
        return name in self.commands

    def get_command(self, name: str) -> Optional[Command]:
        return self.commands.get(name)

    def full_help(self) -> str:
        """Print the full command listing."""
        lines = [
            "hermes [flags] [command] [subcommand]  (no subcommand = interactive chat)",
            "",
            "Global flags:",
        ]
        for f in self.global_flags:
            names = "  ".join(f.names)
            lines.append(f"  {names:<30}  {f.help}")
        lines.append("")
        lines.append("Commands:")
        for name, cmd in sorted(self.commands.items()):
            lines.append(f"  {name:<20}  {cmd.full_help()}")
        return "\n".join(lines)

    def describe(self, *tokens: str) -> str:
        """Describe what `hermes <tokens...>` would do."""
        if not tokens:
            return "interactive chat (no subcommand)"
        cmd_name = tokens[0]
        if cmd_name not in self.commands:
            return f"unknown command: {cmd_name}"
        cmd = self.commands[cmd_name]
        if len(tokens) > 1 and tokens[1] in cmd.subcommands:
            return f"hermes {cmd_name} {tokens[1]}  —  {cmd.subcommands[tokens[1]]}"
        return f"hermes {cmd_name}  —  {cmd.full_help()}"


# ---------------------------------------------------------------------------
# Run it
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    cli = HermesCLI()

    if len(sys.argv) == 1 or sys.argv[1] in ("--help", "-h"):
        print(cli.full_help())
    elif sys.argv[1] == "--describe":
        # usage: python hermes_cli.py --describe chat -q "hello"
        print(cli.describe(*sys.argv[2:]))
    else:
        print(cli.describe(*sys.argv[1:]))
