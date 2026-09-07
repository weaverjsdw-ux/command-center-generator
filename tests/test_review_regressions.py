import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewRegressionTests(unittest.TestCase):
    def test_demo_brief_includes_boundary_conclusion(self):
        html = (ROOT / "examples" / "demo_dashboard.html").read_text(
            encoding="utf-8"
        )
        block = re.search(
            r"conclusions:\s*\[(.*?)\]\s*,\s*authorized:", html, re.DOTALL
        )
        self.assertIsNotNone(block, "Could not locate MAP.conclusions")
        cards = re.findall(r"\{\s*t:\s*\"", block.group(1))
        self.assertEqual(len(cards), 5)
        self.assertIn('t: "Boundary check"', block.group(1))
        self.assertIn('src: "boundary check"', block.group(1))

    def test_unassigned_research_assets_render_unknown(self):
        html = (ROOT / "examples" / "research_dashboard.html").read_text(
            encoding="utf-8"
        )
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


if __name__ == "__main__":
    unittest.main()
