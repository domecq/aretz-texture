"""Claude Code PostToolUse hook that formats and lints Python files after an edit.

Layer 1 of the quality checks (docs/agent-pipeline.md, section 10). It runs
``ruff check --fix`` and ``ruff format`` on the edited file. Problems ruff
cannot fix are sent back to the agent: exit code 2 shows stderr to it.
"""

import json
import subprocess
import sys
from pathlib import Path

OK = 0
REPORT_TO_AGENT = 2


def run_ruff(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ruff with the interpreter of the project environment."""
    return subprocess.run(
        [sys.executable, "-m", "ruff", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    """Format and lint the file named in the hook input, if it is Python."""
    payload = json.loads(sys.stdin.read())
    file_path = Path(str(payload.get("tool_input", {}).get("file_path", "")))
    if file_path.suffix != ".py" or not file_path.is_file():
        return OK
    # Fix first: removing an unused import can leave lines that need formatting.
    check = run_ruff(["check", "--fix", "--quiet", str(file_path)])
    run_ruff(["format", "--quiet", str(file_path)])
    if check.returncode != 0:
        sys.stderr.write(f"ruff found problems it cannot fix in {file_path}:\n{check.stdout}")
        return REPORT_TO_AGENT
    return OK


if __name__ == "__main__":
    sys.exit(main())
