"""
Tool definitions for the Needle 2 agent.

Each function is decorated with @needle.tool. The signature (types +
Annotated constraints) and the docstring are what the model sees — so
treat the docstrings as prompts. Constraints are enforced at decode
time by Needle's grammar compiler, not by the model "choosing" to obey.
"""
import os
import subprocess
from typing import Annotated, Literal

import needle


# ---------- Tool 1: read_file ----------
@needle.tool
def read_file(
    path: Annotated[
        str,
        needle.Field(
            pattern=r"^[a-zA-Z0-9_\-./]+$",
            min_length=1,
            description="Relative path from repo root, e.g. 'scripts/assemble_model.py'.",
        ),
    ]
):
    """Read a file from the repository and return its contents as text.

    Use this whenever you need to inspect source code, config, or docs
    before answering or acting. Paths are relative to the repo root.
    """
    if ".." in path or path.startswith("/"):
        return {"error": "Path must be relative and may not contain '..'."}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > 20000:
            content = content[:20000] + "\n... [truncated at 20000 chars]"
        return content
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


# ---------- Tool 2: run_command (whitelist only) ----------
@needle.tool
def run_command(
    cmd: Annotated[
        str,
        needle.Field(
            enum=[
                "ls",
                "ls -la",
                "git status",
                "git log --oneline -5",
                "git diff --stat",
                "python3 --version",
                "find . -maxdepth 2 -type f -name '*.py'",
            ],
            description="Only whitelisted read-only inspection commands are allowed.",
        ),
    ]
):
    """Execute a whitelisted shell command and return stdout/stderr.

    Use only for inspection (listing files, git status, version checks).
    Destructive or networked commands are not available.
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:1000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30s"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


# ---------- Tool 3: post_comment ----------
@needle.tool
def post_comment(
    body: Annotated[
        str,
        needle.Field(min_length=1, max_length=4000),
    ]
):
    """Post a comment on the current pull request or issue.

    Use this to communicate findings to humans. In CI, requires
    GITHUB_TOKEN and PR_NUMBER env vars. Outside a PR context, the call
    is a no-op and returns why.
    """
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number = os.environ.get("PR_NUMBER", "")
    token = os.environ.get("GITHUB_TOKEN", "")

    if not pr_number:
        return {"posted": False, "reason": "No PR_NUMBER env var — not in a PR context."}
    if not token:
        return {"posted": False, "reason": "No GITHUB_TOKEN env var."}
    if not repo:
        return {"posted": False, "reason": "No GITHUB_REPOSITORY env var."}

    try:
        import requests
        resp = requests.post(
            f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"body": body},
            timeout=20,
        )
        return {"posted": resp.status_code == 201, "status": resp.status_code}
    except Exception as e:
        return {"posted": False, "error": f"{type(e).__name__}: {e}"}


# ---------- Tool 4: set_label ----------
@needle.tool
def set_label(
    label: Literal["bug", "enhancement", "question", "ci-fix", "documentation"]
):
    """Add a label to the current PR/issue.

    Allowed labels are restricted to: bug, enhancement, question,
    ci-fix, documentation. Use to classify what kind of change this is.
    """
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number = os.environ.get("PR_NUMBER", "")
    token = os.environ.get("GITHUB_TOKEN", "")

    if not pr_number or not token or not repo:
        return {"labeled": False, "reason": "Not in a PR context or missing token."}

    try:
        import requests
        resp = requests.post(
            f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"labels": [label]},
            timeout=20,
        )
        return {"labeled": resp.status_code == 200, "label": label, "status": resp.status_code}
    except Exception as e:
        return {"labeled": False, "error": f"{type(e).__name__}: {e}"}
