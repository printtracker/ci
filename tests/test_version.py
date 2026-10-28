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
        script = script.replace("${{github.head_ref || github.ref_name}}", "feature/test")
        cases = [
            ("root and component", [["v1.7.0", "dgi-v0.2.0"]], "1.7.0"),
            ("root only", [["v1.6.0"]], "1.6.0"),
            ("unprefixed root", [["1.7.0", "dgi-v0.2.0"]], "1.7.0"),
            ("prerelease", [["v1.7.0-rc.1", "dgi-v0.2.0"]], "1.7.0-rc.1"),
            ("newer component", [["v1.7.0"], ["dgi-v0.3.0"]], "1.7.0-1-g{sha}"),
            ("component only", [["dgi-v0.2.0"]], "dgi-v0.2.0"),
            ("custom tag", [["release-42"]], "release-42"),
            ("no tags", [[]], "{sha}"),
        ]
        for name, commits, expected in cases:
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
                subprocess.run(
                    ["bash", "-e", "-c", script], cwd=directory, check=True,
                    env={**os.environ, "GITHUB_OUTPUT": str(output)},
                    capture_output=True, text=True,
                )
                values = dict(line.split("=", 1) for line in output.read_text().splitlines())
                self.assertEqual(values["tag"], expected.format(sha=sha))
                self.assertEqual(values["sha"], sha)
                self.assertEqual(values["ref"], "feature_test")


if __name__ == "__main__":
    unittest.main()
