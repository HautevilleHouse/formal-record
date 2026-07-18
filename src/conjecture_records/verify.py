from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

SHELL_META_RE = re.compile(r"[;|<>`\n]|\$\(")
SAFE_ENV = {"PYTHONDONTWRITEBYTECODE": "1"}


class UnsafeCommand(ValueError):
    pass


def _safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise UnsafeCommand("path must remain relative to the commentary checkout")
    return path


def parse_allowed_command(command: str) -> tuple[Path, list[str], dict[str, str]]:
    if SHELL_META_RE.search(command):
        raise UnsafeCommand("shell metacharacter is outside the command policy")
    cwd = Path(".")
    env = dict(SAFE_ENV)
    text = command.strip()
    if text.startswith("PYTHONDONTWRITEBYTECODE=1 "):
        text = text.removeprefix("PYTHONDONTWRITEBYTECODE=1 ")
    if " && " in text:
        prefix, text = text.split(" && ", 1)
        prefix_tokens = shlex.split(prefix)
        if len(prefix_tokens) != 2 or prefix_tokens[0] != "cd":
            raise UnsafeCommand("only a single relative cd prefix is allowed")
        cwd = _safe_relative(prefix_tokens[1])
    tokens = shlex.split(text)
    if not tokens:
        raise UnsafeCommand("empty command")
    if tokens[0] == "python3":
        if len(tokens) != 2 or not tokens[1].endswith(".py"):
            raise UnsafeCommand("Python routes must name exactly one checker script")
        _safe_relative(tokens[1])
    elif tokens[:2] == ["lake", "build"]:
        if len(tokens) > 3 or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", token) for token in tokens[2:]):
            raise UnsafeCommand("Lean target is outside the command policy")
    else:
        raise UnsafeCommand("route is descriptive or uses an unsupported executable")
    return cwd, tokens, env


def plan_routes(record: dict[str, Any], commentary_root: Path) -> list[dict[str, Any]]:
    packet_relative = Path(record["provenance"]["source_identity_path"]).parents[1]
    packet_root = (commentary_root / packet_relative).resolve()
    root = commentary_root.resolve()
    if root not in packet_root.parents:
        raise UnsafeCommand("packet path escaped commentary root")
    plans: list[dict[str, Any]] = []
    for route in record["verification"]["routes"]:
        command = route["command"]
        try:
            relative_cwd, argv, env = parse_allowed_command(command)
            base = root if "openconjectures/" in command else packet_root
            cwd = (base / relative_cwd).resolve()
            if root != cwd and root not in cwd.parents:
                raise UnsafeCommand("working directory escaped commentary root")
            plans.append({"command": command, "cwd": str(cwd), "argv": argv, "env": env, "allowed": True})
        except UnsafeCommand as error:
            plans.append({"command": command, "allowed": False, "reason": str(error)})
    return plans


def execute_plans(plans: list[dict[str, Any]], timeout_seconds: int = 300) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for plan in plans:
        if not plan["allowed"]:
            results.append({"command": plan["command"], "status": "skipped", "reason": plan["reason"]})
            continue
        environment = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), **plan["env"]}
        completed = subprocess.run(
            plan["argv"],
            cwd=plan["cwd"],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        results.append(
            {
                "command": plan["command"],
                "status": "passed" if completed.returncode == 0 else "failed",
                "returncode": completed.returncode,
                "output_tail": completed.stdout[-2000:],
            }
        )
    return results
