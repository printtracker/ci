import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


class VersionTests(unittest.TestCase):
    def test_version_selection(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/version.yml"
        script = textwrap.dedent(workflow.read_text().split("        run: |\n", 1)[1])
        cases = [
            ("explicit server version", [["v1.7.0", "dgi-v0.2.0"]], "1.7.0", "1.7.0"),
            ("explicit prerelease", [["v1.7.0", "dgi-v0.2.0"]], "1.7.0-rc.1", "1.7.0-rc.1"),
            ("explicit version without tags", [[]], "1.7.0", "1.7.0"),
            ("existing mixed-tag fallback", [["v1.7.0", "dgi-v0.2.0"]], "", "dgi-v0.2.0"),
            ("root only", [["v1.6.0"]], "", "1.6.0"),
            ("unprefixed root", [["1.7.0"]], "", "1.7.0"),
            ("commit after release", [["v1.7.0"], []], "", "1.7.0-1-g{sha}"),
            ("newer component", [["v1.7.0"], ["dgi-v0.3.0"]], "", "dgi-v0.3.0"),
            ("component only", [["dgi-v0.2.0"]], "", "dgi-v0.2.0"),
            ("custom tag", [["release-42"]], "", "release-42"),
            ("no tags", [[]], "", "{sha}"),
            ("multiline version", [[]], "1.7.0\nref=other", None),
            ("shell in version", [[]], "$(touch injected)", None),
            ("invalid image tag", [[]], "release/1.7.0", None),
        ]
        for name, commits, version, expected in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                def git(*args):
                    return subprocess.run(
                        ["git", "-C", directory, *args],
                        check=True, capture_output=True, text=True,
                    ).stdout.strip()

                git("init", "--quiet")
                git("config", "user.name", "Version test")
                git("config", "user.email", "version-test@example.com")
                for tags in commits:
                    git("-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture")
                    for tag in tags:
                        git("-c", "tag.gpgsign=false", "tag", tag)

                sha = git("rev-parse", "--short", "HEAD")
                output = Path(directory) / "output"
                ref = "v1.7.0" if version else "feature/test"
                result = subprocess.run(
                    ["bash", "-e", "-c", script], cwd=directory,
                    env={**os.environ, "GITHUB_OUTPUT": str(output),
                         "VERSION_OVERRIDE": version, "REF_NAME": ref},
                    capture_output=True, text=True,
                )
                if expected is None:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("invalid version override", result.stderr)
                    self.assertFalse(output.exists())
                    self.assertFalse((Path(directory) / "injected").exists())
                    continue
                self.assertEqual(result.returncode, 0, result.stderr)
                values = dict(line.split("=", 1) for line in output.read_text().splitlines())
                self.assertEqual(values["tag"], expected.format(sha=sha))
                self.assertEqual(values["sha"], sha)
                self.assertEqual(values["ref"], ref.replace("/", "_"))


if __name__ == "__main__":
    unittest.main()
