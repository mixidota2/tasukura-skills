"""Validate the portable skill package without running commands on user data."""

import re
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
SHELL_EXAMPLES = re.findall(
    r"```bash\n(.*?)```", (ROOT / "README.md").read_text(), re.S
)


class SkillPackageTests(unittest.TestCase):
    def test_skill_discovery(self):
        self.assertTrue(SKILLS, "No installable skills found")
        for directory in (ROOT / "skills").iterdir():
            if directory.is_dir():
                self.assertTrue((directory / "SKILL.md").is_file())

    def test_frontmatter(self):
        for skill in SKILLS:
            with self.subTest(skill=skill.parent.name):
                match = re.match(r"\A---\n(.*?)\n---\n(.+)\Z", skill.read_text(), re.S)
                self.assertIsNotNone(match, "Missing YAML frontmatter or instructions")
                metadata = yaml.safe_load(match[1])
                self.assertIsInstance(metadata, dict)
                self.assertEqual(metadata["name"], skill.parent.name)
                self.assertRegex(metadata["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertLessEqual(len(metadata["name"]), 64)
                description = metadata["description"]
                self.assertIsInstance(description, str)
                self.assertTrue(description.strip())
                self.assertLessEqual(len(description), 1024)
                self.assertNotRegex(description, r"[<>]")

    def test_relative_markdown_links(self):
        for document in [ROOT / "README.md", *SKILLS]:
            for link in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", document.read_text()):
                parsed = urlsplit(link)
                if parsed.scheme or not parsed.path:
                    continue
                target = (document.parent / unquote(parsed.path)).resolve()
                with self.subTest(document=document.name, link=link):
                    target.relative_to(ROOT)
                    self.assertTrue(target.exists(), "Broken local link")

    def test_standalone_resources(self):
        for skill in SKILLS:
            for path in skill.parent.rglob("*"):
                with self.subTest(path=path):
                    self.assertFalse(
                        path.is_symlink(), "Skill must not rely on external symlinks"
                    )
            self.assertNotIn("/workspace/", skill.read_text())
            self.assertNotIn("/path/to/tasukura/", skill.read_text())

    def test_install_layout(self):
        for skill in SKILLS:
            for agent in (".claude", ".agents"):
                with self.subTest(skill=skill.parent.name, agent=agent):
                    with tempfile.TemporaryDirectory() as home:
                        installed = Path(home) / agent / "skills" / skill.parent.name
                        installed.parent.mkdir(parents=True)
                        installed.symlink_to(skill.parent, target_is_directory=True)
                        self.assertEqual(
                            (installed / "SKILL.md").read_bytes(), skill.read_bytes()
                        )

    def test_no_bundled_task_data(self):
        for directory in (ROOT / "skills", ROOT / "tests"):
            for path in directory.rglob("*"):
                if path.is_file():
                    self.assertNotIn(path.suffix, {".db", ".sqlite", ".sqlite3"})
                    self.assertNotEqual(path.name, "config.toml")

    def test_documented_installation(self):
        for agent in (".claude", ".agents"):
            script = next(
                block
                for block in SHELL_EXAMPLES
                if f'mkdir -p "$HOME/{agent}/skills"' in block
            )
            for existing in ("absent", "directory", "symlink", "broken-symlink"):
                with self.subTest(agent=agent, existing=existing):
                    with tempfile.TemporaryDirectory() as home:
                        destination = Path(home) / agent / "skills" / "tk"
                        destination.parent.mkdir(parents=True)
                        if existing == "directory":
                            destination.mkdir()
                            (destination / "customization").write_text("keep me")
                        elif "symlink" in existing:
                            target = Path(home) / "original"
                            if existing == "symlink":
                                target.mkdir()
                            destination.symlink_to(target, target_is_directory=True)
                        result = subprocess.run(
                            ["bash", "-c", script],
                            cwd=ROOT,
                            env={**os.environ, "HOME": home},
                            capture_output=True,
                        )
                        if existing == "absent":
                            self.assertEqual(result.returncode, 0, result.stderr)
                            self.assertEqual(destination.resolve(), ROOT / "skills/tk")
                        else:
                            self.assertNotEqual(result.returncode, 0)
                            if existing == "directory":
                                self.assertEqual(
                                    list(destination.iterdir()),
                                    [destination / "customization"],
                                )
                            else:
                                self.assertEqual(
                                    destination.readlink(), Path(home) / "original"
                                )

    def test_documented_migration(self):
        script = next(block for block in SHELL_EXAMPLES if "backup=" in block)
        for existing in (
            "directory",
            "symlink",
            "broken-symlink",
            "relative-symlink",
            "broken-relative-symlink",
            "absent",
        ):
            for backup_exists in (False, True):
                with self.subTest(existing=existing, backup_exists=backup_exists):
                    with tempfile.TemporaryDirectory() as home:
                        destination = Path(home) / ".claude/skills/tk"
                        backup = (
                            Path(home)
                            / ".claude/skill-backups/tk.before-tasukura-skills"
                        )
                        destination.parent.mkdir(parents=True)
                        if existing == "directory":
                            destination.mkdir()
                            (destination / "customization").write_text("keep me")
                        elif "symlink" in existing:
                            target = Path(home) / "original"
                            if not existing.startswith("broken-"):
                                target.mkdir()
                            link_target = (
                                Path("../../original")
                                if "relative" in existing
                                else target
                            )
                            destination.symlink_to(
                                link_target, target_is_directory=True
                            )
                        if backup_exists:
                            backup.parent.mkdir(parents=True)
                            backup.write_text("previous backup")
                        result = subprocess.run(
                            ["bash", "-c", script],
                            cwd=ROOT,
                            env={**os.environ, "HOME": home},
                            capture_output=True,
                        )
                        if existing == "absent" or backup_exists:
                            self.assertNotEqual(result.returncode, 0)
                            self.assertFalse(
                                destination.resolve() == ROOT / "skills/tk"
                            )
                            if backup_exists:
                                self.assertEqual(backup.read_text(), "previous backup")
                            continue
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(destination.resolve(), ROOT / "skills/tk")
                        self.assertEqual(
                            list(destination.parent.iterdir()), [destination]
                        )
                        if existing == "directory":
                            self.assertEqual(
                                (backup / "customization").read_text(), "keep me"
                            )
                        else:
                            self.assertTrue(backup.readlink().is_absolute())
                            self.assertEqual(backup.resolve(), Path(home) / "original")
                            self.assertEqual(
                                backup.exists(), not existing.startswith("broken-")
                            )


if __name__ == "__main__":
    unittest.main()
