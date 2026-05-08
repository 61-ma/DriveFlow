import unittest

from app.models import Stage
from app.service import TravelAssistantService


class TravelAssistantServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TravelAssistantService()

    def test_main_flow_can_complete_all_key_frames(self) -> None:
        start = self.service.start_session()
        session_id = start.session_id

        confirmation = self.service.handle_message(session_id, "帮我规划一个云南5天的行程")
        self.assertEqual(confirmation.stage, Stage.CONFIRMING_INFO)
        self.assertIn("预算", confirmation.missing_info)

        plan = self.service.handle_message(
            session_id,
            "我从上海出发，国庆去，预算8000，喜欢自然风光和慢节奏",
        )
        self.assertEqual(plan.stage, Stage.PLAN_GENERATED)
        self.assertIsNotNone(plan.plan)
        self.assertEqual(plan.plan.days[0].city, "昆明")

        revised = self.service.revise_plan(session_id, "预算降到6000，不要太赶，加一天大理")
        self.assertEqual(revised.stage, Stage.REVISING_PLAN)
        self.assertEqual(revised.plan.total_estimated_cost, 6000)
        self.assertEqual(len(revised.plan.days), 6)
        self.assertTrue(any(day.city == "大理" for day in revised.plan.days))

        confirmed = self.service.confirm_plan(session_id)
        self.assertEqual(confirmed.stage, Stage.PLAN_CONFIRMED)

        shared = self.service.share_plan(session_id)
        self.assertEqual(shared.stage, Stage.SHARED)

    def test_missing_info_requires_follow_up(self) -> None:
        start = self.service.start_session()
        reply = self.service.handle_message(start.session_id, "想去云南玩5天")
        self.assertEqual(reply.stage, Stage.CONFIRMING_INFO)
        self.assertListEqual(reply.missing_info, ["出发地", "出行时间", "预算"])

    def test_cannot_share_before_plan_exists(self) -> None:
        start = self.service.start_session()
        with self.assertRaises(ValueError):
            self.service.share_plan(start.session_id)


if __name__ == "__main__":
    unittest.main()

