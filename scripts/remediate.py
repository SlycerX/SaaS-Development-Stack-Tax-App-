"""Open a Snyk fix pull request with a Cursor cloud agent.

The SDK call runs only when CURSOR_API_KEY is present. The job itself always starts.
The agent may not edit waivers or production IAM.
"""

from __future__ import annotations

import os
import sys

PROMPT = """
You are the security agent for this repository.

Read the latest Snyk Code, Snyk Open Source, Snyk Container, and Snyk IaC findings.
Open a pull request that fixes the critical and high findings you can fix in application code,
Playwright tests, or existing Terraform modules.

Do not edit docs/security/waivers.
Do not change production IAM, the GitHub OIDC trust policy, or Amazon Cognito settings.
Do not skip Snyk, Playwright, Grafana k6, OWASP ZAP, or any environment.
If a fix would break docs/guardrails.md, stop and describe the deviation in the pull request
instead of making that change.
""".strip()


def main() -> int:
    api_key = os.getenv("CURSOR_API_KEY", "").strip()
    if not api_key:
        print("CURSOR_API_KEY is not set. Remediation was not started.")
        return 0

    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if not repository or repository.startswith("CHANGE_ME"):
        print("GITHUB_REPOSITORY must be org/repo before remediation can open a pull request.", file=sys.stderr)
        return 1

    from cursor_sdk import Agent, AgentOptions, CloudAgentOptions, CloudRepository, CursorAgentError

    repo_url = f"https://github.com/{repository}"
    try:
        result = Agent.prompt(
            PROMPT,
            AgentOptions(
                api_key=api_key,
                model="composer-2.5",
                cloud=CloudAgentOptions(
                    repos=[CloudRepository(url=repo_url, starting_ref="main")],
                    auto_create_pr=True,
                    skip_reviewer_request=True,
                ),
            ),
        )
    except CursorAgentError as exc:
        print(f"startup failed: {exc.message}, retryable={exc.is_retryable}", file=sys.stderr)
        return 1

    status = getattr(result, "status", "")
    print(f"status={status}")
    print(getattr(result, "result", ""))
    if status == "error":
        return 2
    if status not in {"finished", ""}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
