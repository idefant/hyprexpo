from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/compatibility.yml"


class CompatibilityBuildGateTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text()

    def test_computes_build_need_from_the_event_diff(self):
        self.assertIn("build_needed", self.workflow)
        self.assertIn("git diff --name-only", self.workflow)
        self.assertIn("scripts/ci-targets.py build-needed", self.workflow)

    def test_skips_only_the_expensive_build_job(self):
        self.assertIn("if: needs.changes.outputs.build_needed == 'true'", self.workflow)
        self.assertIn('test "$BUILD_RESULT" = success || test "$BUILD_RESULT" = skipped', self.workflow)


if __name__ == "__main__":
    unittest.main()
