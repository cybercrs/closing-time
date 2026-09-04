"""Case content centered on account changes and financial-statement effects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecognitionQuestion:
    id: str
    document: str
    title: str
    story: str
    prompt: str
    options: tuple[str, ...]
    correct: str
    explanation: str


@dataclass(frozen=True)
class AdjustmentItem:
    id: str
    document: str
    title: str
    story: str
    classification: str
    amount: int
    changes: tuple[tuple[str, int], ...]
    explanation: str


@dataclass(frozen=True)
class AccountChallenge:
    id: str
    adjustment_id: str
    title: str
    instruction: str
    account_a: str
    account_b: str
    effect_options: tuple[str, ...]
    correct_effect: str
    ending_a: int
    ending_b: int
    omission_options: tuple[str, ...]
    correct_omission: str
    explanation: str


@dataclass(frozen=True)
class IntegrityScenario:
    id: str
    title: str
    proposal: str
    options: tuple[str, ...]
    correct: str
    explanation: str
    statement_effect: str


COMPANY_NAME = "Gem City Creative Studio"
REPORTING_DATE = "May 31"

CLASSIFICATION_OPTIONS = (
    "Prepaid expense (deferral)",
    "Unearned revenue (deferral)",
    "Accrued revenue",
    "Accrued expense",
)

INTEGRITY_OPTIONS = (
    "Acceptable if it is faithfully reported",
    "Not acceptable because it misstates May",
)


RECOGNITION_QUESTIONS = (
    RecognitionQuestion(
        id="insurance_month",
        document="Insurance policy",
        title="A year of coverage",
        story=(
            "On May 1, the studio paid $12,000 for insurance coverage from May 1 "
            "through April 30 of next year."
        ),
        prompt="How much insurance expense belongs in May?",
        options=("$0", "$1,000", "$12,000"),
        correct="$1,000",
        explanation=(
            "May used one of the twelve months of coverage. Accrual accounting "
            "reports the portion consumed in May, not the amount of cash paid."
        ),
    ),
    RecognitionQuestion(
        id="deposit_earned",
        document="Workshop progress report",
        title="Cash arrived before the work",
        story=(
            "Clients paid $9,000 in advance for a three-part workshop series. By "
            "May 31, the studio has completed two of the three workshops."
        ),
        prompt="How much service revenue belongs in May?",
        options=("$0", "$6,000", "$9,000"),
        correct="$6,000",
        explanation=(
            "Two-thirds of the promised service has been completed, so $6,000 is "
            "revenue. The remaining $3,000 still represents work owed to clients."
        ),
    ),
    RecognitionQuestion(
        id="unbilled_service",
        document="Project completion email",
        title="Work finished before billing",
        story=(
            "A $3,800 design project was completed on May 30. The client will be "
            "billed in June and will pay later."
        ),
        prompt="When should the $3,800 of service revenue be reported?",
        options=("May", "June when billed", "When cash is collected"),
        correct="May",
        explanation=(
            "The performance obligation was satisfied in May. Billing and cash "
            "collection can occur later without changing the reporting period."
        ),
    ),
    RecognitionQuestion(
        id="unpaid_wages",
        document="Payroll calendar",
        title="Work performed before payday",
        story=(
            "Employees earned $2,500 from May 27 through May 31. Their next payday "
            "is June 5."
        ),
        prompt="When should the $2,500 of salary expense be reported?",
        options=("May", "June when paid", "Half in May and half in June"),
        correct="May",
        explanation=(
            "The employees made their effort in May. May therefore reports the "
            "expense even though the cash payment occurs in June."
        ),
    ),
)


UNADJUSTED_BALANCES = {
    "Cash": 15_600,
    "Accounts Receivable": 6_000,
    "Supplies": 2_400,
    "Prepaid Insurance": 12_000,
    "Equipment": 30_000,
    "Accounts Payable": 4_200,
    "Unearned Revenue": 9_000,
    "Salaries Payable": 0,
    "Interest Payable": 0,
    "Common Stock": 40_000,
    "Service Revenue": 27_800,
    "Salaries Expense": 11_000,
    "Rent Expense": 4_000,
    "Supplies Expense": 0,
    "Insurance Expense": 0,
    "Interest Expense": 0,
}


ADJUSTMENT_ITEMS = (
    AdjustmentItem(
        id="insurance",
        document="Insurance policy",
        title="One month of insurance has expired",
        story=(
            "The $12,000 policy began May 1 and covers twelve months. The records "
            "still show the full $12,000 as Prepaid Insurance."
        ),
        classification="Prepaid expense (deferral)",
        amount=1_000,
        changes=(("Prepaid Insurance", -1_000), ("Insurance Expense", 1_000)),
        explanation=(
            "Cash was paid before the benefit was consumed. One month has now "
            "expired, so the asset decreases and May expense increases."
        ),
    ),
    AdjustmentItem(
        id="supplies",
        document="Physical supplies count",
        title="Supplies were used during May",
        story=(
            "The Supplies account shows $2,400. A May 31 count finds only $700 of "
            "supplies remaining."
        ),
        classification="Prepaid expense (deferral)",
        amount=1_700,
        changes=(("Supplies", -1_700), ("Supplies Expense", 1_700)),
        explanation=(
            "$1,700 of supplies were consumed. The remaining asset is $700, and "
            "the amount used becomes a May expense."
        ),
    ),
    AdjustmentItem(
        id="workshops",
        document="Workshop completion log",
        title="Two workshops are complete",
        story=(
            "The studio received $9,000 in advance for three workshops. Two were "
            "completed by May 31, but the records still show all $9,000 as "
            "Unearned Revenue."
        ),
        classification="Unearned revenue (deferral)",
        amount=6_000,
        changes=(("Unearned Revenue", -6_000), ("Service Revenue", 6_000)),
        explanation=(
            "Cash arrived before the services. Completing two workshops removes "
            "$6,000 of the obligation and creates $6,000 of May revenue."
        ),
    ),
    AdjustmentItem(
        id="unbilled",
        document="Signed client approval",
        title="A completed project has not been billed",
        story=(
            "A client approved a completed $3,800 project on May 30. No bill or "
            "cash receipt has yet been recorded."
        ),
        classification="Accrued revenue",
        amount=3_800,
        changes=(("Accounts Receivable", 3_800), ("Service Revenue", 3_800)),
        explanation=(
            "The service was performed before billing or collection. The amount "
            "owed by the client and May revenue both increase."
        ),
    ),
    AdjustmentItem(
        id="wages",
        document="Payroll calendar",
        title="Employees have earned unpaid wages",
        story=(
            "Employees earned $2,500 through May 31 that will be paid on June 5. "
            "The May records do not yet include this amount."
        ),
        classification="Accrued expense",
        amount=2_500,
        changes=(("Salaries Expense", 2_500), ("Salaries Payable", 2_500)),
        explanation=(
            "Employees worked before the cash payment. May expense and the amount "
            "owed to employees both increase."
        ),
    ),
    AdjustmentItem(
        id="interest",
        document="Lender statement",
        title="Interest has accumulated",
        story=(
            "$300 of loan interest accumulated during May and will be paid in "
            "June. The May records do not yet include it."
        ),
        classification="Accrued expense",
        amount=300,
        changes=(("Interest Expense", 300), ("Interest Payable", 300)),
        explanation=(
            "The cost belongs to May even though payment is later. May expense and "
            "the amount owed to the lender both increase."
        ),
    ),
)


ACCOUNT_CHALLENGES = (
    AccountChallenge(
        id="insurance_ripple",
        adjustment_id="insurance",
        title="Insurance account ripple",
        instruction="Apply only the insurance information to the balances shown.",
        account_a="Prepaid Insurance",
        account_b="Insurance Expense",
        effect_options=(
            "Prepaid Insurance decreases $1,000; Insurance Expense increases $1,000",
            "Cash decreases $1,000; Insurance Expense increases $1,000",
            "Prepaid Insurance increases $1,000; Insurance Expense decreases $1,000",
            "Neither account changes until the policy ends",
        ),
        correct_effect="Prepaid Insurance decreases $1,000; Insurance Expense increases $1,000",
        ending_a=11_000,
        ending_b=1_000,
        omission_options=(
            "Assets and net income would be overstated; expenses would be understated",
            "Assets and net income would be understated; expenses would be overstated",
            "Only cash would be understated",
        ),
        correct_omission="Assets and net income would be overstated; expenses would be understated",
        explanation=(
            "Using one month of coverage reduces the remaining benefit. Omitting "
            "the change leaves too much asset and too little expense."
        ),
    ),
    AccountChallenge(
        id="workshop_ripple",
        adjustment_id="workshops",
        title="Workshop account ripple",
        instruction="Apply only the completed-workshop information to the balances shown.",
        account_a="Unearned Revenue",
        account_b="Service Revenue",
        effect_options=(
            "Unearned Revenue decreases $6,000; Service Revenue increases $6,000",
            "Cash increases $6,000; Service Revenue increases $6,000",
            "Unearned Revenue increases $6,000; Service Revenue decreases $6,000",
            "Neither account changes until all three workshops are complete",
        ),
        correct_effect="Unearned Revenue decreases $6,000; Service Revenue increases $6,000",
        ending_a=3_000,
        ending_b=33_800,
        omission_options=(
            "Liabilities would be overstated; revenue and net income would be understated",
            "Liabilities would be understated; revenue and net income would be overstated",
            "Assets would be understated; expenses would be overstated",
        ),
        correct_omission="Liabilities would be overstated; revenue and net income would be understated",
        explanation=(
            "Completing two workshops satisfies two-thirds of the obligation. "
            "Without the adjustment, too much obligation remains and too little "
            "revenue is reported."
        ),
    ),
    AccountChallenge(
        id="unbilled_ripple",
        adjustment_id="unbilled",
        title="Unbilled project account ripple",
        instruction="Apply only the completed-project information to the balances shown.",
        account_a="Accounts Receivable",
        account_b="Service Revenue",
        effect_options=(
            "Accounts Receivable increases $3,800; Service Revenue increases $3,800",
            "Cash increases $3,800; Service Revenue increases $3,800",
            "Accounts Receivable decreases $3,800; Service Revenue decreases $3,800",
            "Neither account changes until the client is billed",
        ),
        correct_effect="Accounts Receivable increases $3,800; Service Revenue increases $3,800",
        ending_a=9_800,
        ending_b=31_600,
        omission_options=(
            "Assets, revenue, and net income would be understated",
            "Assets, revenue, and net income would be overstated",
            "Liabilities and expenses would be understated",
        ),
        correct_omission="Assets, revenue, and net income would be understated",
        explanation=(
            "The completed work creates both an amount due from the client and May "
            "revenue. Waiting for billing would understate both."
        ),
    ),
    AccountChallenge(
        id="wages_ripple",
        adjustment_id="wages",
        title="Payroll account ripple",
        instruction="Apply only the unpaid-wage information to the balances shown.",
        account_a="Salaries Expense",
        account_b="Salaries Payable",
        effect_options=(
            "Salaries Expense increases $2,500; Salaries Payable increases $2,500",
            "Cash decreases $2,500; Salaries Expense increases $2,500",
            "Salaries Expense decreases $2,500; Salaries Payable increases $2,500",
            "Neither account changes until payday",
        ),
        correct_effect="Salaries Expense increases $2,500; Salaries Payable increases $2,500",
        ending_a=13_500,
        ending_b=2_500,
        omission_options=(
            "Liabilities and expenses would be understated; net income would be overstated",
            "Liabilities and expenses would be overstated; net income would be understated",
            "Assets and revenue would be understated",
        ),
        correct_omission="Liabilities and expenses would be understated; net income would be overstated",
        explanation=(
            "The employee effort belongs to May. Omitting it hides both the expense "
            "and the amount owed, which makes May income look too high."
        ),
    ),
)


STATEMENT_FIELDS = (
    ("service_revenue", "Service Revenue"),
    ("total_expenses", "Total Expenses"),
    ("net_income", "Net Income"),
    ("ending_retained_earnings", "Ending Retained Earnings"),
    ("total_assets", "Total Assets"),
    ("total_liabilities", "Total Liabilities"),
    ("total_liabilities_equity", "Total Liabilities and Stockholders' Equity"),
)


INTEGRITY_SCENARIOS = (
    IntegrityScenario(
        id="delay_wages",
        title="Wait until payday",
        proposal=(
            "The manager suggests leaving the $2,500 of May wages out because the "
            "employees will not be paid until June."
        ),
        options=INTEGRITY_OPTIONS,
        correct="Not acceptable because it misstates May",
        explanation=(
            "The employees worked in May. Delaying the expense would not faithfully "
            "represent May performance."
        ),
        statement_effect="May expenses and liabilities would be too low, while net income would be too high.",
    ),
    IntegrityScenario(
        id="full_deposit",
        title="Recognize the entire client deposit",
        proposal=(
            "The manager wants all $9,000 of workshop deposits reported as May "
            "revenue even though one of the three workshops remains."
        ),
        options=INTEGRITY_OPTIONS,
        correct="Not acceptable because it misstates May",
        explanation=(
            "The studio still owes one workshop. Reporting the unearned $3,000 as "
            "revenue would accelerate revenue without completing the service."
        ),
        statement_effect="Revenue and net income would be too high, while liabilities would be too low.",
    ),
    IntegrityScenario(
        id="transparent_gain",
        title="Report a completed one-time sale",
        proposal=(
            "The studio completed a legitimate equipment sale on May 30 that "
            "created a $4,000 gain. The manager proposes reporting it separately "
            "and clearly describing that it will not recur."
        ),
        options=INTEGRITY_OPTIONS,
        correct="Acceptable if it is faithfully reported",
        explanation=(
            "A one-time item is not automatically improper. If the sale occurred, "
            "the amount is measured correctly, and its nature is transparent, May "
            "should include it."
        ),
        statement_effect="May income increases, but transparent presentation helps users distinguish recurring performance.",
    ),
    IntegrityScenario(
        id="capitalize_repair",
        title="Turn a repair into an asset",
        proposal=(
            "To reach the earnings target, the manager proposes treating a routine "
            "$7,000 repair as Equipment even though it creates no future benefit."
        ),
        options=INTEGRITY_OPTIONS,
        correct="Not acceptable because it misstates May",
        explanation=(
            "A routine repair that creates no future benefit is a current expense. "
            "Calling it an asset would conceal the expense."
        ),
        statement_effect="Assets and net income would be too high, while expenses would be too low.",
    ),
)
