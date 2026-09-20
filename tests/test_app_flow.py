import unittest

from streamlit.testing.v1 import AppTest

from closing_time.case_data import (
    ACCOUNT_CHALLENGES,
    ADJUSTMENT_ITEMS,
    INTEGRITY_SCENARIOS,
    RECOGNITION_QUESTIONS,
    STATEMENT_QUESTIONS,
)
from closing_time.progress import SNAPSHOT_PARAM, decode_snapshot


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


class PerfectCloseFlowTests(unittest.TestCase):
    def test_draft_restores_and_wrong_answer_revises_in_one_check(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
        button(app, "Begin the close").click().run()
        item = RECOGNITION_QUESTIONS[0]
        wrong = next(option for option in item.options if option != item.correct)

        app.radio(key=f"widget_recognition_{item.id}").set_value(wrong).run()
        saved_value = app.query_params[SNAPSHOT_PARAM]
        saved = decode_snapshot(saved_value[0] if isinstance(saved_value, list) else saved_value)
        self.assertEqual(saved["ct_drafts"]["recognition"][item.id], wrong)

        button(app, "Check the reporting period").click().run()
        self.assertTrue(any(item.label == "Check revised answer" for item in app.button))
        app.radio(key=f"widget_recognition_{item.id}").set_value(item.correct)
        button(app, "Check revised answer").click().run()

        self.assertEqual(app.session_state.ct_recognition_responses[item.id], item.correct)
        self.assertTrue(any(item.label == "Continue" for item in app.button))

    def test_complete_close_reaches_debrief_without_accounting_mechanics(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
        self.assertFalse(app.exception)
        button(app, "Begin the close").click().run()

        for item in RECOGNITION_QUESTIONS:
            app.radio(key=f"widget_recognition_{item.id}").set_value(item.correct)
            button(app, "Check the reporting period").click().run()
            button(app, "Continue").click().run()

        for item in ADJUSTMENT_ITEMS:
            app.radio(key=f"widget_classification_{item.id}").set_value(item.classification)
            button(app, "Identify the transaction").click().run()
            button(app, "Continue").click().run()

        for item in ACCOUNT_CHALLENGES:
            self.assertEqual(len(app.number_input), 0)
            self.assertNotEqual(app.radio(key=f"widget_effect_{item.id}").options, list(item.effect_options))
            app.radio(key=f"widget_effect_{item.id}").set_value(item.correct_effect)
            app.radio(key=f"widget_omission_{item.id}").set_value(item.correct_omission)
            button(app, "Check the account ripple").click().run()
            button(app, "Continue").click().run()

        for item in STATEMENT_QUESTIONS:
            app.radio(key=f"widget_statement_{item.id}").set_value(item.correct)
        equation_copy = "\n".join(item.value for item in app.markdown)
        self.assertIn("A = L + SE", equation_copy)
        button(app, "Check the statement connections").click().run()
        button(app, "Continue to the integrity review").click().run()

        for index, item in enumerate(INTEGRITY_SCENARIOS):
            app.radio(key=f"widget_integrity_{item.id}").set_value(item.correct)
            button(app, "Evaluate the proposal").click().run()
            if index < len(INTEGRITY_SCENARIOS) - 1:
                button(app, "Continue").click().run()

        self.assertFalse(app.exception)
        self.assertTrue(any("Close complete" in item.value for item in app.success))
        rendered = "\n".join(item.value for item in app.markdown).lower()
        self.assertIn("final mastery: complete", "\n".join(item.value for item in app.caption).lower())
        self.assertNotIn("chapter 6", rendered)
        for banned in ("debit", "credit", "journal", "ledger posting"):
            self.assertNotIn(banned, rendered)

        saved_value = app.query_params[SNAPSHOT_PARAM]
        saved = decode_snapshot(saved_value[0] if isinstance(saved_value, list) else saved_value)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["ct_stage"], 5)
        self.assertEqual(len(saved["ct_integrity_responses"]), len(INTEGRITY_SCENARIOS))


if __name__ == "__main__":
    unittest.main()
