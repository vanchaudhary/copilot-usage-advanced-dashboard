import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "cpuad-updater"))
os.environ.setdefault("GITHUB_PAT", "test-token")
os.environ.setdefault("ORGANIZATION_SLUGS", "standalone:test-enterprise")

from main import ElasticsearchManager, GitHubOrganizationManager, Indexes
from metrics_2_usage_convertor import convert_user_report_to_usage


class ChatReportingTests(unittest.TestCase):
    def test_report_chat_records_have_source_and_interaction_count(self):
        records = [{
            "day": "2026-09-15",
            "user_login": "user",
            "team_slug": "team",
            "used_chat": True,
            "totals_by_model_feature": [{
                "feature": "chat_panel_agent_mode",
                "model": "model",
                "user_initiated_interaction_count": 3,
                "code_acceptance_activity_count": 1,
            }],
        }]
        daily = convert_user_report_to_usage(records)["team"][0]
        self.assertEqual(daily["total_active_chat_users"], 1)
        self.assertEqual(daily["breakdown_chat"][0]["report_source"], "user-28-day")
        self.assertEqual(daily["breakdown_chat"][0]["chat_turns"], 3)

    def test_every_chat_target_restricts_report_source(self):
        path = ROOT / "src" / "cpuad-updater" / "grafana" / "dashboard-template.json"
        dashboard = json.loads(path.read_text(encoding="utf-8"))["dashboard"]
        chat_row = next(row for row in dashboard["panels"] if row["title"] == "Copilot Chat")
        queries = [target["query"] for panel in chat_row["panels"]
                   for target in panel["targets"] if "query" in target]
        self.assertEqual(len(queries), 7)
        self.assertTrue(all("report_source.keyword: user-28-day" in query for query in queries))

    def test_cleanup_only_removes_current_report_totals_and_chat(self):
        manager = object.__new__(ElasticsearchManager)
        manager.es = Mock()

        manager.clear_report_usage("test-enterprise")

        self.assertEqual(manager.es.delete_by_query.call_count, 2)
        self.assertEqual(
            {call.kwargs["index"] for call in manager.es.delete_by_query.call_args_list},
            {Indexes.index_name_total, Indexes.index_name_breakdown_chat},
        )
        for call in manager.es.delete_by_query.call_args_list:
            self.assertEqual(call.kwargs["query"], {"bool": {"filter": [
                {"term": {"organization_slug": "test-enterprise"}},
                {"term": {"report_source.keyword": "user-28-day"}},
            ]}})

    @patch("main.requests.get")
    def test_billing_metrics_keep_each_csv_date(self, get):
        csv_data = (
            "date,username,model,quantity,unit_type,gross_amount,input,output\n"
            "2026-08-07,user,model,2,ai-credits,4,10,20\n"
            "2026-08-09,user,model,3,ai-credits,6,30,40\n"
        )
        get.side_effect = [
            Mock(json=lambda: {"status": "completed", "end_date": "2026-08-31", "download_urls": ["https://example.test/report.csv"]}, raise_for_status=lambda: None),
            Mock(text=csv_data, raise_for_status=lambda: None),
        ]
        manager = object.__new__(GitHubOrganizationManager)
        manager.api_type = "enterprises"
        manager.organization_slug = "test-enterprise"

        records = manager.get_ai_billing_report(report_id=42, save_to_json=False)

        raw = [record for record in records if record.get("record_type") == "csv_row"]
        credits = [record for record in records if record.get("category") == "ai_credits"]
        self.assertEqual([record["day"] for record in raw], ["2026-08-07", "2026-08-09"])
        self.assertEqual([record["day"] for record in credits], ["2026-08-07", "2026-08-09"])


if __name__ == "__main__":
    unittest.main()