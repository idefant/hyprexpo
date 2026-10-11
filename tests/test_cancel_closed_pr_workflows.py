from pathlib import Path
import json
import os
import subprocess
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/cancel-closed-pr-workflows.yml"


class CancelClosedPrWorkflowsTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text()

    def test_runs_only_after_a_pull_request_closes(self):
        self.assertIn("pull_request:\n    types: [closed]", self.workflow)

    def test_has_only_the_actions_write_permission_needed_to_cancel(self):
        self.assertIn("permissions:\n  actions: write", self.workflow)

    def test_limits_cancellation_to_active_runs_for_the_closed_pr(self):
        self.assertIn("for status in queued in_progress", self.workflow)
        self.assertIn("PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}", self.workflow)
        self.assertIn("PR_HEAD_REF: ${{ github.event.pull_request.head.ref }}", self.workflow)
        self.assertIn("PR_HEAD_REPOSITORY: ${{ github.event.pull_request.head.repo.full_name }}", self.workflow)
        self.assertIn("event=pull_request&status=${status}&head_sha=${PR_HEAD_SHA}", self.workflow)
        self.assertIn(".head_branch == env.PR_HEAD_REF", self.workflow)
        self.assertIn(".head_repository.full_name == env.PR_HEAD_REPOSITORY", self.workflow)
        self.assertIn(".id != (env.GITHUB_RUN_ID | tonumber)", self.workflow)
        self.assertIn("actions/runs/${run_id}/cancel", self.workflow)

    def test_selects_a_pr_run_when_github_omits_pull_request_associations(self):
        response = {
            "workflow_runs": [
                {
                    "id": 42,
                    "head_sha": "target-sha",
                    "head_branch": "fix/cache",
                    "head_repository": {"full_name": "sandwichfarm/hyprexpo"},
                    "pull_requests": [],
                },
                {
                    "id": 43,
                    "head_sha": "target-sha",
                    "head_branch": "other-branch",
                    "head_repository": {"full_name": "sandwichfarm/hyprexpo"},
                    "pull_requests": [],
                },
                {
                    "id": 44,
                    "head_sha": "target-sha",
                    "head_branch": "fix/cache",
                    "head_repository": {"full_name": "sandwichfarm/hyprexpo"},
                    "pull_requests": [],
                },
            ]
        }
        result = subprocess.run(
            ["jq", "-r", """
                .workflow_runs[]
                | select(.id != (env.GITHUB_RUN_ID | tonumber))
                | select(.head_branch == env.PR_HEAD_REF)
                | select(.head_repository.full_name == env.PR_HEAD_REPOSITORY)
                | .id
            """],
            input=json.dumps(response),
            text=True,
            capture_output=True,
            check=True,
            env={**os.environ, "GITHUB_RUN_ID": "44", "PR_HEAD_REF": "fix/cache",
                 "PR_HEAD_REPOSITORY": "sandwichfarm/hyprexpo"},
        )
        self.assertEqual(result.stdout.strip(), "42")


if __name__ == "__main__":
    unittest.main()
