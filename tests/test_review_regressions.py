import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewRegressionTests(unittest.TestCase):
    @staticmethod
    def read(relative_path):
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_demo_brief_includes_boundary_conclusion(self):
        html = self.read("examples/demo_dashboard.html")
        block = re.search(
            r"conclusions:\s*\[(.*?)\]\s*,\s*authorized:", html, re.DOTALL
        )
        self.assertIsNotNone(block, "Could not locate MAP.conclusions")
        cards = re.findall(r"\{\s*t:\s*\"", block.group(1))
        self.assertEqual(len(cards), 5)
        self.assertIn('t: "Boundary check"', block.group(1))
        self.assertIn('src: "boundary check"', block.group(1))

    def test_unassigned_research_assets_render_unknown(self):
        html = self.read("examples/research_dashboard.html")
        for code in ("MEM-3", "TOOL-1", "MEM-2"):
            record = re.search(
                rf'\{{code:"{code}".*?outsideFacing:', html, re.DOTALL
            )
            self.assertIsNotNone(record, f"Could not locate {code}")
            self.assertIn(
                'status:"UNKNOWN"',
                record.group(0),
                f"{code} is named by no operator decision and must be unassigned",
            )

        self.assertIn("named by no decision → UNKNOWN / unassigned", html)
        self.assertNotIn("named by no decision → catalog-only", html)

    def test_honest_calls_preserve_explicit_postures(self):
        package = self.read("GENERATOR_PACKAGE.md")
        dashboard = self.read("examples/demo_dashboard.html")
        self.assertIn("explicit disposition word (or unambiguous synonym)", package)
        self.assertIn('posture:"maintain for myself"', dashboard)
        self.assertIn('posture:"keep running"', dashboard)

    def test_computed_parked_pub2_remains_in_boundary_panel(self):
        package = self.read("GENERATOR_PACKAGE.md")
        dashboard = self.read("examples/demo_dashboard.html")
        self.assertIn("PUB-2 public-repo visibility (computed PARKED", package)
        self.assertIn(
            "PUB-2 public-repo visibility — computed PARKED by the outside-facing rule",
            dashboard,
        )

    def test_zero_authorization_copy_does_not_invent_catalog_status(self):
        package = self.read("GENERATOR_PACKAGE.md")
        self.assertIn(
            'If zero authorized → "No action authorized — no authorized move stated"',
            package,
        )
        self.assertNotIn('If zero authorized → "No action authorized — catalog only"', package)

    def test_fixture_asks_neutral_single_field_questions(self):
        builder = self.read("docs/prompts/MAP_BUILDER_PACKAGE.md")
        q2 = re.search(r"> \*\*Q2:\*\*(.*?)\n>\n> \*\*A:\*\*", builder, re.DOTALL)
        q3 = re.search(r"> \*\*Q3:\*\*(.*?)\n>\n> \*\*A:\*\*", builder, re.DOTALL)
        self.assertIsNotNone(q2)
        self.assertIsNotNone(q3)
        self.assertIn("What disposition, if any", q2.group(1))
        self.assertNotIn("schedule", q2.group(1).lower())
        self.assertIn("What schedule, if any", q3.group(1))

    def test_existing_gate_is_only_asked_for_classification(self):
        builder = self.read("docs/prompts/MAP_BUILDER_PACKAGE.md")
        q5 = re.search(r"> \*\*Q5:\*\*(.*?)\n>\n> \*\*A:\*\*", builder, re.DOTALL)
        self.assertIsNotNone(q5)
        self.assertIn("already says", q5.group(1))
        self.assertIn("How should that source statement be classified", q5.group(1))

    def test_h4_names_every_governed_asset(self):
        h4_scope = "PUB-1, PUB-2, PUB-3 public-visibility actions"
        for relative_path in (
            "GENERATOR_PACKAGE.md",
            "docs/prompts/MAP_BUILDER_PACKAGE.md",
            "examples/demo_source_map.md",
            "examples/demo_dashboard.html",
        ):
            with self.subTest(path=relative_path):
                self.assertIn(h4_scope, self.read(relative_path))

    def test_pub1_queue_preserves_h4_public_showing_restriction(self):
        dashboard = self.read("examples/demo_dashboard.html")
        pub1 = re.search(
            r'\{ code:"PUB-1".*?dndcell:"(.*?)" \}', dashboard, re.DOTALL
        )
        self.assertIsNotNone(pub1)
        self.assertIn("public showing", pub1.group(1))
        self.assertIn("H4 secrets/PII sweep", pub1.group(1))

    def test_h1_names_every_asset_governed_by_adoption_reality(self):
        for relative_path in (
            "GENERATOR_PACKAGE.md",
            "docs/prompts/MAP_BUILDER_PACKAGE.md",
            "examples/demo_source_map.md",
        ):
            line = next(
                line for line in self.read(relative_path).splitlines()
                if line.startswith("- **H1")
            )
            for asset in ("INF-1", "INF-2", "INF-3", "PUB-1", "PUB-2", "PUB-3"):
                with self.subTest(path=relative_path, asset=asset):
                    self.assertIn(asset, line)


if __name__ == "__main__":
    unittest.main()
