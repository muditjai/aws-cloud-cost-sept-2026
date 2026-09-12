from __future__ import annotations

import unittest
from pathlib import Path

from aws_cloud_cost_agent.web import _group_artifacts


class ArtifactGroupingTests(unittest.TestCase):
    def test_groups_artifacts_by_workflow_stage(self) -> None:
        artifacts = [
            Path("recommendations_amazon_rds.md"),
            Path("overall_bill_data_2026-09-01_2026-09-12.md"),
            Path("service_sku_analysis_amazon_rds.md"),
            Path("connection_check_2026-09-12.md"),
            Path("legacy_service_report.md"),
        ]

        grouped = _group_artifacts(artifacts)

        self.assertEqual(
            grouped["Connection Check"],
            [Path("connection_check_2026-09-12.md")],
        )
        self.assertEqual(
            grouped["Overall Bill"],
            [Path("overall_bill_data_2026-09-01_2026-09-12.md")],
        )
        self.assertEqual(
            grouped["Per Service Analysis"],
            [
                Path("service_sku_analysis_amazon_rds.md"),
                Path("legacy_service_report.md"),
            ],
        )
        self.assertEqual(
            grouped["Recommendations"],
            [Path("recommendations_amazon_rds.md")],
        )


if __name__ == "__main__":
    unittest.main()
