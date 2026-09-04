import unittest

from streamlit.testing.v1 import AppTest

from closing_time.case_data import (
    ACCOUNT_CHALLENGES,
    ADJUSTMENT_ITEMS,
    INTEGRITY_SCENARIOS,
    RECOGNITION_QUESTIONS,
    STATEMENT_FIELDS,
)
from closing_time.engine import statement_values
from closing_time.progress import SNAPSHOT_PARAM, decode_snapshot


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


class PerfectCloseFlowTests(unittest.TestCase):
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
            button(app, "Classify the evidence").click().run()
            button(app, "Continue").click().run()

        for item in ACCOUNT_CHALLENGES:
            app.radio(key=f"widget_effect_{item.id}").set_value(item.correct_effect)
            app.number_input(key=f"widget_ending_a_{item.id}").set_value(item.ending_a)
            app.number_input(key=f"widget_ending_b_{item.id}").set_value(item.ending_b)
            app.radio(key=f"widget_omission_{item.id}").set_value(item.correct_omission)
            button(app, "Check the account ripple").click().run()
            button(app, "Continue").click().run()

        expected = statement_values()
        for key, _ in STATEMENT_FIELDS:
            app.number_input(key=f"widget_statement_{key}").set_value(expected[key])
        button(app, "Check the financial statements").click().run()
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
        for banned in ("debit", "credit", "journal", "ledger posting"):
            self.assertNotIn(banned, rendered)

        saved_value = app.query_params[SNAPSHOT_PARAM]
        saved = decode_snapshot(saved_value[0] if isinstance(saved_value, list) else saved_value)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["ct_stage"], 5)
        self.assertEqual(len(saved["ct_integrity_responses"]), len(INTEGRITY_SCENARIOS))


if __name__ == "__main__":
    unittest.main()
