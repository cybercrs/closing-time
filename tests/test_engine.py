import re
import unittest

from closing_time.case_data import (
    ACCOUNT_CHALLENGES,
    ADJUSTMENT_ITEMS,
    INTEGRITY_SCENARIOS,
    RECOGNITION_QUESTIONS,
    STATEMENT_QUESTIONS,
    UNADJUSTED_BALANCES,
)
from closing_time.engine import (
    ASSET_ACCOUNTS,
    EXPENSE_ACCOUNTS,
    LIABILITY_ACCOUNTS,
    REVENUE_ACCOUNTS,
    adjusted_balances,
    equation_check,
    evaluate_account_challenge,
    evaluate_integrity,
    evaluate_statement_responses,
    format_currency,
    statement_values,
)


class ClosingCalculationTests(unittest.TestCase):
    def test_all_adjusted_balances_and_statement_totals(self):
        balances = adjusted_balances()
        self.assertEqual(balances["Prepaid Insurance"], 11_000)
        self.assertEqual(balances["Supplies"], 700)
        self.assertEqual(balances["Unearned Revenue"], 3_000)
        self.assertEqual(balances["Accounts Receivable"], 9_800)
        self.assertEqual(balances["Salaries Payable"], 2_500)
        self.assertEqual(balances["Interest Payable"], 300)
        self.assertEqual(balances["Service Revenue"], 37_600)

        values = statement_values(balances)
        self.assertEqual(values["total_expenses"], 20_500)
        self.assertEqual(values["net_income"], 17_100)
        self.assertEqual(values["ending_retained_earnings"], 17_100)
        self.assertEqual(values["total_assets"], 67_100)
        self.assertEqual(values["total_liabilities"], 10_000)
        self.assertEqual(values["total_liabilities_equity"], 67_100)
        self.assertTrue(equation_check(balances)["balanced"])

    def test_unadjusted_records_balance_but_are_incomplete(self):
        values = statement_values(UNADJUSTED_BALANCES)
        self.assertEqual(values["total_assets"], 66_000)
        self.assertEqual(values["total_liabilities_equity"], 66_000)
        self.assertEqual(values["net_income"], 12_800)

    def test_each_adjustment_connects_one_balance_sheet_and_one_income_statement_account(self):
        balance_sheet_accounts = ASSET_ACCOUNTS | LIABILITY_ACCOUNTS
        income_statement_accounts = REVENUE_ACCOUNTS | EXPENSE_ACCOUNTS
        for item in ADJUSTMENT_ITEMS:
            accounts = {account for account, _ in item.changes}
            self.assertEqual(len(accounts & balance_sheet_accounts), 1, item.id)
            self.assertEqual(len(accounts & income_statement_accounts), 1, item.id)
            self.assertNotIn("Cash", accounts, item.id)

    def test_case_covers_all_four_adjustment_classes(self):
        classes = [item.classification for item in ADJUSTMENT_ITEMS]
        self.assertEqual(classes.count("Prepaid expense (deferral)"), 2)
        self.assertEqual(classes.count("Unearned revenue (deferral)"), 1)
        self.assertEqual(classes.count("Accrued revenue"), 1)
        self.assertEqual(classes.count("Accrued expense"), 2)

    def test_interest_evidence_identifies_the_studio_as_borrower(self):
        interest = next(item for item in ADJUSTMENT_ITEMS if item.id == "interest")
        wording = f"{interest.document} {interest.title} {interest.story}".lower()
        self.assertIn("borrower", wording)
        self.assertIn("lender", wording)

    def test_account_challenges_check_direction_balance_and_omission_effect(self):
        for item in ACCOUNT_CHALLENGES:
            result = evaluate_account_challenge(
                item.id,
                item.correct_effect,
                item.correct_omission,
            )
            self.assertTrue(result["correct"], item.id)
            wrong = evaluate_account_challenge(
                item.id,
                item.effect_options[-1],
                item.omission_options[-1],
            )
            self.assertFalse(wrong["correct"], item.id)

    def test_statement_questions_check_conceptual_connections(self):
        self.assertEqual(len(STATEMENT_QUESTIONS), 3)
        responses = {item.id: item.correct for item in STATEMENT_QUESTIONS}
        first = STATEMENT_QUESTIONS[0]
        responses[first.id] = next(option for option in first.options if option != first.correct)
        results = evaluate_statement_responses(responses)
        self.assertFalse(results[first.id]["correct"])
        self.assertEqual(results[first.id]["expected"], first.correct)
        self.assertTrue(results[STATEMENT_QUESTIONS[1].id]["correct"])

    def test_integrity_round_includes_transparent_and_misleading_choices(self):
        acceptable = [item for item in INTEGRITY_SCENARIOS if item.correct.startswith("Acceptable")]
        misleading = [item for item in INTEGRITY_SCENARIOS if item.correct.startswith("Not acceptable")]
        self.assertEqual(len(acceptable), 1)
        self.assertEqual(len(misleading), 3)
        for item in INTEGRITY_SCENARIOS:
            self.assertTrue(evaluate_integrity(item.id, item.correct)["correct"])

    def test_currency_format_places_minus_sign_before_symbol(self):
        self.assertEqual(format_currency(-1_700), "-$1,700")
        self.assertEqual(format_currency(17_100), "$17,100")

    def test_student_case_language_avoids_unassigned_mechanics(self):
        fields = []
        for item in RECOGNITION_QUESTIONS:
            fields.extend((item.title, item.story, item.prompt, item.explanation, *item.options))
        for item in ADJUSTMENT_ITEMS:
            fields.extend((item.title, item.story, item.explanation, item.classification))
        for item in ACCOUNT_CHALLENGES:
            fields.extend((item.title, item.instruction, item.explanation, *item.effect_options, *item.omission_options))
        for item in INTEGRITY_SCENARIOS:
            fields.extend((item.title, item.proposal, item.explanation, item.statement_effect, *item.options))
        student_text = " ".join(fields).lower()
        for banned in (r"\bdebits?\b", r"\bcredits?\b", r"\bjournal\b", r"\bledger\b", r"\bposting\b"):
            self.assertIsNone(re.search(banned, student_text), banned)


if __name__ == "__main__":
    unittest.main()
