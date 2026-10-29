import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"


def frontmatter():
    match = re.match(r"^---\n(.*?)\n---\n", SKILL.read_text(), re.S)
    return match.group(1) if match else ""


class SkillFrontmatter(unittest.TestCase):
    def test_frontmatter_is_present_with_name_and_description(self):
        fm = frontmatter()
        self.assertRegex(fm, r"(?m)^name: refine-setup$")
        self.assertRegex(fm, r"(?m)^description: \S")

    def test_description_is_a_single_line(self):
        lines = [ln for ln in frontmatter().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2, "frontmatter must be exactly name + a one-line description")

    def test_unquoted_description_has_no_colon_space_that_breaks_yaml(self):
        desc = next(ln for ln in frontmatter().splitlines() if ln.startswith("description: "))
        value = desc[len("description: "):]
        self.assertFalse(value.startswith(('"', "'")), "quoted descriptions are not covered by this check")
        self.assertNotIn(": ", value)
        self.assertNotIn(" #", value)

    def test_yaml_parser_agrees_when_available(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")
        data = yaml.safe_load(frontmatter())
        self.assertEqual(data["name"], "refine-setup")
        self.assertIsInstance(data["description"], str)


if __name__ == "__main__":
    unittest.main()
