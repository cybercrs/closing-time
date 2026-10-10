"""Pure calculations and evaluations for Closing Time."""

from __future__ import annotations

from collections.abc import Mapping

from closing_time.case_data import (
    ACCOUNT_CHALLENGES,
    ADJUSTMENT_ITEMS,
    INTEGRITY_SCENARIOS,
    RECOGNITION_QUESTIONS,
    STATEMENT_QUESTIONS,
    UNADJUSTED_BALANCES,
    AccountChallenge,
    AdjustmentItem,
)


ASSET_ACCOUNTS = {
    "Cash",
    "Accounts Receivable",
    "Supplies",
    "Prepaid Insurance",
    "Equipment",
}
LIABILITY_ACCOUNTS = {
    "Accounts Payable",
    "Unearned Revenue",
    "Salaries Payable",
    "Interest Payable",
}
EQUITY_ACCOUNTS = {"Common Stock"}
REVENUE_ACCOUNTS = {"Service Revenue"}
EXPENSE_ACCOUNTS = {
    "Salaries Expense",
    "Rent Expense",
    "Supplies Expense",
    "Insurance Expense",
    "Interest Expense",
}


def format_currency(value: int) -> str:
    """Format a whole-dollar amount for students."""

    if value < 0:
        return f"-${abs(value):,.0f}"
    return f"${value:,.0f}"


def adjustment_by_id(item_id: str) -> AdjustmentItem:
    return next(item for item in ADJUSTMENT_ITEMS if item.id == item_id)


def recognition_by_id(item_id: str):
    return next(item for item in RECOGNITION_QUESTIONS if item.id == item_id)


def challenge_by_id(item_id: str) -> AccountChallenge:
    return next(item for item in ACCOUNT_CHALLENGES if item.id == item_id)


def integrity_by_id(item_id: str):
    return next(item for item in INTEGRITY_SCENARIOS if item.id == item_id)


def adjusted_balances() -> dict[str, int]:
    """Return all ending balances after the six May adjustments."""

    balances = dict(UNADJUSTED_BALANCES)
    for item in ADJUSTMENT_ITEMS:
        for account, change in item.changes:
            balances[account] = balances.get(account, 0) + change
    return balances


def statement_values(balances: Mapping[str, int] | None = None) -> dict[str, int]:
    """Calculate the three linked statement totals from account balances."""

    source = balances or adjusted_balances()
    service_revenue = source.get("Service Revenue", 0)
    total_expenses = sum(source.get(account, 0) for account in EXPENSE_ACCOUNTS)
    net_income = service_revenue - total_expenses
    ending_retained_earnings = net_income
    total_assets = sum(source.get(account, 0) for account in ASSET_ACCOUNTS)
    total_liabilities = sum(source.get(account, 0) for account in LIABILITY_ACCOUNTS)
    total_equity = sum(source.get(account, 0) for account in EQUITY_ACCOUNTS) + ending_retained_earnings
    return {
        "service_revenue": service_revenue,
        "total_expenses": total_expenses,
        "net_income": net_income,
        "beginning_retained_earnings": 0,
        "dividends": 0,
        "ending_retained_earnings": ending_retained_earnings,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "total_liabilities_equity": total_liabilities + total_equity,
    }


def balance_rows() -> list[dict[str, str]]:
    """Build a student-facing unadjusted/change/adjusted comparison."""

    ending = adjusted_balances()
    rows = []
    for account, opening in UNADJUSTED_BALANCES.items():
        change = ending[account] - opening
        rows.append(
            {
                "Account": account,
                "Unadjusted": format_currency(opening),
                "Change": ("+" if change > 0 else "") + format_currency(change),
                "Adjusted": format_currency(ending[account]),
            }
        )
    return rows


def evaluate_recognition(item_id: str, selected: str) -> dict[str, object]:
    item = recognition_by_id(item_id)
    return {
        "correct": selected == item.correct,
        "selected": selected,
        "expected": item.correct,
        "explanation": item.explanation,
    }


def evaluate_classification(item_id: str, selected: str) -> dict[str, object]:
    item = adjustment_by_id(item_id)
    return {
        "correct": selected == item.classification,
        "selected": selected,
        "expected": item.classification,
        "explanation": item.explanation,
    }


def evaluate_account_challenge(
    item_id: str,
    effect: str,
    omission: str,
) -> dict[str, object]:
    item = challenge_by_id(item_id)
    checks = {
        "effect": effect == item.correct_effect,
        "omission": omission == item.correct_omission,
    }
    return {
        "correct": all(checks.values()),
        "checks": checks,
        "expected": {
            "effect": item.correct_effect,
            "omission": item.correct_omission,
        },
        "explanation": item.explanation,
    }


def evaluate_statement_responses(responses: Mapping[str, str]) -> dict[str, dict[str, object]]:
    results = {}
    for item in STATEMENT_QUESTIONS:
        submitted = str(responses.get(item.id, ""))
        results[item.id] = {
            "label": item.prompt,
            "submitted": submitted,
            "expected": item.correct,
            "correct": submitted == item.correct,
            "explanation": item.explanation,
        }
    return results


def evaluate_integrity(item_id: str, selected: str) -> dict[str, object]:
    item = integrity_by_id(item_id)
    return {
        "correct": selected == item.correct,
        "selected": selected,
        "expected": item.correct,
        "explanation": item.explanation,
        "statement_effect": item.statement_effect,
    }


def equation_check(balances: Mapping[str, int] | None = None) -> dict[str, int | bool]:
    source = balances or adjusted_balances()
    values = statement_values(source)
    assets = values["total_assets"]
    liabilities_equity = values["total_liabilities_equity"]
    return {
        "assets": assets,
        "liabilities_equity": liabilities_equity,
        "balanced": assets == liabilities_equity,
    }
