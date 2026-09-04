"""Student-facing Streamlit application for Closing Time."""

from __future__ import annotations

from html import escape

import streamlit as st

from closing_time.case_data import (
    ACCOUNT_CHALLENGES,
    ADJUSTMENT_ITEMS,
    CLASSIFICATION_OPTIONS,
    COMPANY_NAME,
    INTEGRITY_SCENARIOS,
    RECOGNITION_QUESTIONS,
    REPORTING_DATE,
    STATEMENT_FIELDS,
    UNADJUSTED_BALANCES,
)
from closing_time.engine import (
    adjusted_balances,
    balance_rows,
    evaluate_account_challenge,
    evaluate_classification,
    evaluate_integrity,
    evaluate_recognition,
    evaluate_statement_responses,
    format_currency,
    statement_values,
)
from closing_time.progress import (
    SNAPSHOT_PARAM,
    activity_defaults,
    record_attempt,
    reset_saved_progress,
    restore_session_state,
    score_summary,
    sync_progress_query,
)


st.set_page_config(
    page_title="Closing Time",
    page_icon="🕔",
    layout="wide",
    initial_sidebar_state="collapsed",
)


UD_RED = "#CE0037"
UD_BLUE = "#003087"
INK = "#14213D"
MUTED = "#59677A"
SURFACE = "#FFFFFF"
BACKGROUND = "#F5F7FB"
SUCCESS = "#137A4B"
WARNING = "#986000"
GOLD = "#F3B61F"


APP_CSS = f"""
<style>
    :root {{
        --ud-red: {UD_RED};
        --ud-blue: {UD_BLUE};
        --ink: {INK};
        --muted: {MUTED};
        --surface: {SURFACE};
        --background: {BACKGROUND};
        --success: {SUCCESS};
        --warning: {WARNING};
        --gold: {GOLD};
    }}

    .stApp {{ background: var(--background); }}
    [data-testid="stHeaderActionElements"] {{ display: none; }}
    [data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}
    [data-testid="stDecoration"] {{ background: var(--ud-red); }}
    .block-container {{ max-width: 1160px; padding-top: 1.4rem; padding-bottom: 4rem; }}

    h1, h2, h3 {{ color: var(--ink); letter-spacing: -0.02em; }}
    p, li, label {{ color: var(--ink); }}

    .hero {{
        background:
            radial-gradient(circle at 92% 10%, rgba(243, 182, 31, 0.28), transparent 25%),
            linear-gradient(125deg, #001F55 0%, var(--ud-blue) 62%, #164E91 100%);
        border-top: 7px solid var(--ud-red);
        border-radius: 18px;
        box-shadow: 0 16px 38px rgba(0, 48, 135, 0.17);
        margin-bottom: 1.05rem;
        padding: 2rem 2.2rem 1.8rem;
    }}
    .hero-kicker {{ color: #FFFFFF; font-size: 0.8rem; font-weight: 850; letter-spacing: 0.13em; }}
    .hero h1 {{ color: #FFFFFF; font-size: clamp(2.2rem, 5vw, 3.7rem); margin: 0.15rem 0 0; }}
    .hero p {{ color: #F1F5FF; font-size: 1.08rem; margin: 0.65rem 0 0; max-width: 800px; }}
    .clock {{ color: var(--gold); font-weight: 900; }}

    .stage-row {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.4rem; margin: 0 0 1.3rem; }}
    .stage-pill {{
        background: #E6EAF1; border: 1px solid #D3D9E4; border-radius: 999px;
        color: #5C6879; font-size: 0.74rem; font-weight: 760; padding: 0.48rem 0.55rem; text-align: center;
    }}
    .stage-pill.complete {{ background: #E5F3EB; border-color: #A5D2B9; color: #0A653D; }}
    .stage-pill.active {{ background: var(--ud-red); border-color: var(--ud-red); color: #FFFFFF; }}

    .eyebrow {{ color: var(--ud-red); font-size: 0.78rem; font-weight: 850; letter-spacing: 0.1em; text-transform: uppercase; }}
    .lead {{ color: var(--muted); font-size: 1.06rem; max-width: 850px; }}
    .card {{
        background: var(--surface); border: 1px solid #D9E0EA; border-left: 7px solid var(--ud-blue);
        border-radius: 14px; box-shadow: 0 8px 22px rgba(20, 33, 61, 0.06);
        margin: 0.75rem 0 1rem; padding: 1.15rem 1.3rem;
    }}
    .card .document {{ color: var(--ud-blue); font-size: 0.78rem; font-weight: 850; letter-spacing: 0.06em; text-transform: uppercase; }}
    .card h3 {{ margin: 0.28rem 0 0.48rem; }}
    .card p {{ font-size: 1.04rem; margin: 0; }}

    .concept-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.72rem; margin: 1rem 0 1.3rem; }}
    .concept-card {{ background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 13px; padding: 1rem; }}
    .concept-card strong {{ color: var(--ud-blue); display: block; margin: 0.2rem 0; }}
    .concept-number {{ color: var(--ud-red); font-size: 1.15rem; font-weight: 900; }}
    .concept-card span {{ color: var(--muted); font-size: 0.9rem; }}

    .account-strip {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.7rem; margin: 0.75rem 0 1rem; }}
    .account-box {{ background: #EEF4FF; border: 1px solid #C6D7F2; border-radius: 12px; padding: 0.85rem 1rem; }}
    .account-box span {{ color: var(--muted); display: block; font-size: 0.8rem; font-weight: 700; }}
    .account-box strong {{ color: var(--ud-blue); display: block; font-size: 1.35rem; margin-top: 0.15rem; }}

    .feedback-row {{
        align-items: flex-start; background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 10px;
        display: flex; gap: 1rem; justify-content: space-between; margin: 0.42rem 0; padding: 0.7rem 0.82rem;
    }}
    .feedback-row.correct {{ border-left: 5px solid var(--success); }}
    .feedback-row.review {{ border-left: 5px solid var(--warning); }}
    .feedback-label {{ font-weight: 780; }}
    .feedback-detail {{ color: var(--muted); font-size: 0.9rem; margin-top: 0.12rem; }}
    .feedback-value {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}

    .statement {{ background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 13px; min-height: 100%; padding: 1rem; }}
    .statement-title {{ color: var(--ud-blue); font-size: 1.05rem; font-weight: 850; text-align: center; }}
    .statement-period {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 0.65rem; text-align: center; }}
    .statement-line {{ display: flex; gap: 0.7rem; justify-content: space-between; padding: 0.26rem 0; }}
    .statement-line.indent {{ padding-left: 0.85rem; }}
    .statement-line.total {{ border-top: 1px solid #7F8999; font-weight: 800; margin-top: 0.18rem; padding-top: 0.4rem; }}
    .statement-line.grand {{ border-bottom: 3px double var(--ink); border-top: 1px solid var(--ink); font-weight: 850; margin-top: 0.2rem; padding: 0.42rem 0 0.34rem; }}
    .statement-section {{ color: var(--ud-red); font-size: 0.78rem; font-weight: 850; letter-spacing: 0.05em; margin-top: 0.45rem; text-transform: uppercase; }}
    .amount {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}

    .score-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.65rem; margin: 1rem 0; }}
    .score-box {{ background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 12px; padding: 0.85rem; text-align: center; }}
    .score-box strong {{ color: var(--ud-blue); display: block; font-size: 1.45rem; }}
    .score-box span {{ color: var(--muted); font-size: 0.82rem; }}

    .principle {{ background: #FFF5F7; border-left: 5px solid var(--ud-red); border-radius: 9px; margin: 0.7rem 0; padding: 0.82rem 0.95rem; }}
    .principle strong {{ color: var(--ud-red); }}

    .stButton > button, .stFormSubmitButton > button {{ border-radius: 9px; font-weight: 760; min-height: 2.7rem; }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background: var(--ud-red); border-color: var(--ud-red); color: #FFFFFF; }}
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{ background: #A9002E; border-color: #A9002E; color: #FFFFFF; }}
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primaryFormSubmit"] {{ background: var(--ud-red); border-color: var(--ud-red); color: #FFFFFF; }}
    button[data-testid="stBaseButton-primary"] p,
    button[data-testid="stBaseButton-primaryFormSubmit"] p {{ color: #FFFFFF !important; }}

    @media (max-width: 780px) {{
        .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
        .hero {{ padding: 1.4rem 1.2rem; }}
        .stage-row {{ grid-template-columns: 1fr; }}
        .stage-pill {{ display: none; }}
        .stage-pill.active {{ display: block; }}
        .concept-grid, .account-strip, .score-grid {{ grid-template-columns: 1fr; }}
        .feedback-row {{ display: block; }}
        .feedback-value {{ display: block; margin-top: 0.3rem; }}
    }}
</style>
"""


STAGE_LABELS = ("Briefing", "Timing", "Evidence", "Account Ripple", "Statements", "Integrity")


def initialize_state() -> None:
    if "ct_restore_attempted" not in st.session_state:
        restore_session_state(st.session_state, st.query_params.get(SNAPSHOT_PARAM))
        st.session_state.ct_restore_attempted = True
    for key, value in activity_defaults().items():
        if key not in st.session_state:
            st.session_state[key] = value


def restart_activity() -> None:
    reset_saved_progress(st.session_state, st.query_params)


def set_stage(stage: int) -> None:
    st.session_state.ct_stage = stage


def advance_item(index_key: str, count: int, next_stage: int) -> None:
    index = int(st.session_state[index_key])
    if index >= count - 1:
        set_stage(next_stage)
    else:
        st.session_state[index_key] = index + 1


def remove_response(map_key: str, item_id: str) -> None:
    responses = dict(st.session_state[map_key])
    responses.pop(item_id, None)
    st.session_state[map_key] = responses


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="hero-kicker">CHAPTER 6 INTERACTIVE CASE</div>
          <h1>Closing Time</h1>
          <p><span class="clock">5:00 p.m. on May 31.</span> The reports are due tomorrow. Use the evidence to show what really happened this month.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_row() -> None:
    current = int(st.session_state.ct_stage)
    pills = []
    for index, label in enumerate(STAGE_LABELS):
        status = "complete" if index < current else "active" if index == current else ""
        pills.append(f'<div class="stage-pill {status}">{index + 1}. {escape(label)}</div>')
    st.markdown(f'<div class="stage-row">{"".join(pills)}</div>', unsafe_allow_html=True)


def render_card(document: str, title: str, story: str) -> None:
    st.markdown(
        f"""
        <div class="card">
          <div class="document">{escape(document)}</div>
          <h3>{escape(title)}</h3>
          <p>{escape(story)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feedback_row(label: str, correct: bool, detail: str, value: str = "") -> None:
    status = "correct" if correct else "review"
    symbol = "Correct" if correct else "Review"
    st.markdown(
        f"""
        <div class="feedback-row {status}">
          <div><div class="feedback-label">{escape(label)} - {symbol}</div><div class="feedback-detail">{escape(detail)}</div></div>
          <div class="feedback-value">{escape(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def store_simple_answer(map_key: str, item_id: str, selected: str, score_key: str, correct: bool) -> None:
    responses = dict(st.session_state[map_key])
    responses[item_id] = selected
    st.session_state[map_key] = responses
    record_attempt(st.session_state, score_key, correct)


def render_briefing() -> None:
    st.markdown('<div class="eyebrow">Your assignment</div>', unsafe_allow_html=True)
    st.header(f"Finish the May close for {COMPANY_NAME}")
    st.markdown(
        "The cash records are complete, but the reports are not. Some May activity has not yet been reflected, and some cash activity belongs partly to a later period. Your job is to make the accounts and financial statements faithfully describe May.",
    )
    st.markdown(
        """
        <div class="concept-grid">
          <div class="concept-card"><div class="concept-number">01</div><strong>Choose the period</strong><span>Decide when revenue and expense belong.</span></div>
          <div class="concept-card"><div class="concept-number">02</div><strong>Read the evidence</strong><span>Distinguish deferrals from accruals.</span></div>
          <div class="concept-card"><div class="concept-number">03</div><strong>Trace the ripple</strong><span>Calculate account changes and ending balances.</span></div>
          <div class="concept-card"><div class="concept-number">04</div><strong>Protect the story</strong><span>Prepare statements and resist misleading choices.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="principle"><strong>Working rule:</strong> Focus on the economic activity in May. A cash receipt or payment may occur before or after the related revenue or expense.</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Unadjusted assets", format_currency(66_000))
    col2.metric("Unadjusted liabilities", format_currency(13_200))
    col3.metric("Unadjusted net income", format_currency(12_800))
    st.caption("These numbers balance, but they are not yet complete or up to date.")
    st.button("Begin the close", type="primary", width="stretch", on_click=set_stage, args=(1,))


def render_recognition_stage() -> None:
    index = int(st.session_state.ct_recognition_index)
    item = RECOGNITION_QUESTIONS[index]
    st.markdown('<div class="eyebrow">Step 1 of the reasoning chain</div>', unsafe_allow_html=True)
    st.header("Which period tells the truth?")
    st.write("Begin with the recognition question. Cash timing is evidence, but it does not determine the answer by itself.")
    st.progress((index + 1) / len(RECOGNITION_QUESTIONS), text=f"Decision {index + 1} of {len(RECOGNITION_QUESTIONS)}")
    render_card(item.document, item.title, item.story)

    response = st.session_state.ct_recognition_responses.get(item.id)
    if response is None:
        with st.form(f"recognition_form_{item.id}"):
            selected = st.radio(item.prompt, item.options, index=None, key=f"widget_recognition_{item.id}")
            submitted = st.form_submit_button("Check the reporting period", type="primary", width="stretch")
        if submitted:
            if selected is None:
                st.warning("Choose a response before checking your reasoning.")
            else:
                result = evaluate_recognition(item.id, selected)
                store_simple_answer(
                    "ct_recognition_responses",
                    item.id,
                    selected,
                    f"recognition:{item.id}",
                    bool(result["correct"]),
                )
                st.rerun()

    if response is not None:
        result = evaluate_recognition(item.id, response)
        if result["correct"]:
            st.success(f"Correct. {result['explanation']}")
            st.button(
                "Continue",
                type="primary",
                width="stretch",
                on_click=advance_item,
                args=("ct_recognition_index", len(RECOGNITION_QUESTIONS), 2),
            )
        else:
            st.warning(f"Reconsider the timing. {result['explanation']}")
            st.caption(f"The amount or period that belongs in May is: {result['expected']}.")
            st.button(
                "Revise my answer",
                width="stretch",
                on_click=remove_response,
                args=("ct_recognition_responses", item.id),
            )


def render_classification_stage() -> None:
    index = int(st.session_state.ct_classification_index)
    item = ADJUSTMENT_ITEMS[index]
    st.markdown('<div class="eyebrow">Step 2 of the reasoning chain</div>', unsafe_allow_html=True)
    st.header("Sort the evidence")
    st.write("Each item changes one balance-sheet account and one income-statement account. Identify why the records need updating.")
    st.progress((index + 1) / len(ADJUSTMENT_ITEMS), text=f"Evidence item {index + 1} of {len(ADJUSTMENT_ITEMS)}")
    render_card(item.document, item.title, item.story)

    response = st.session_state.ct_classification_responses.get(item.id)
    if response is None:
        with st.form(f"classification_form_{item.id}"):
            selected = st.radio(
                "What type of adjustment is needed?",
                CLASSIFICATION_OPTIONS,
                index=None,
                key=f"widget_classification_{item.id}",
            )
            submitted = st.form_submit_button("Classify the evidence", type="primary", width="stretch")
        if submitted:
            if selected is None:
                st.warning("Choose a classification before checking your reasoning.")
            else:
                result = evaluate_classification(item.id, selected)
                store_simple_answer(
                    "ct_classification_responses",
                    item.id,
                    selected,
                    f"classification:{item.id}",
                    bool(result["correct"]),
                )
                st.rerun()

    if response is not None:
        result = evaluate_classification(item.id, response)
        if result["correct"]:
            st.success(f"Correct: {result['expected']}. {result['explanation']}")
            st.button(
                "Continue",
                type="primary",
                width="stretch",
                on_click=advance_item,
                args=("ct_classification_index", len(ADJUSTMENT_ITEMS), 3),
            )
        else:
            st.warning(f"Review the relationship between cash timing and recognition. {result['explanation']}")
            st.caption(f"This evidence is classified as: {result['expected']}.")
            st.button(
                "Revise my answer",
                width="stretch",
                on_click=remove_response,
                args=("ct_classification_responses", item.id),
            )


def render_account_stage() -> None:
    index = int(st.session_state.ct_account_index)
    item = ACCOUNT_CHALLENGES[index]
    source = next(adjustment for adjustment in ADJUSTMENT_ITEMS if adjustment.id == item.adjustment_id)
    st.markdown('<div class="eyebrow">Step 3 of the reasoning chain</div>', unsafe_allow_html=True)
    st.header("Trace the account ripple")
    st.write("Determine which accounts change, calculate their ending balances, and diagnose what would be wrong if the adjustment were omitted.")
    st.progress((index + 1) / len(ACCOUNT_CHALLENGES), text=f"Account ripple {index + 1} of {len(ACCOUNT_CHALLENGES)}")
    render_card(source.document, item.title, source.story)
    st.caption(item.instruction)
    st.markdown(
        f"""
        <div class="account-strip">
          <div class="account-box"><span>Unadjusted {escape(item.account_a)}</span><strong>{format_currency(UNADJUSTED_BALANCES[item.account_a])}</strong></div>
          <div class="account-box"><span>Unadjusted {escape(item.account_b)}</span><strong>{format_currency(UNADJUSTED_BALANCES[item.account_b])}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    response = st.session_state.ct_account_responses.get(item.id)
    if response is None:
        with st.form(f"account_form_{item.id}"):
            effect = st.radio(
                "How do the accounts change?",
                item.effect_options,
                index=None,
                key=f"widget_effect_{item.id}",
            )
            col1, col2 = st.columns(2)
            ending_a = int(
                col1.number_input(
                    f"Ending {item.account_a}",
                    min_value=0,
                    max_value=1_000_000,
                    step=100,
                    key=f"widget_ending_a_{item.id}",
                )
            )
            ending_b = int(
                col2.number_input(
                    f"Ending {item.account_b}",
                    min_value=0,
                    max_value=1_000_000,
                    step=100,
                    key=f"widget_ending_b_{item.id}",
                )
            )
            omission = st.radio(
                "If this adjustment were omitted, what would be misstated?",
                item.omission_options,
                index=None,
                key=f"widget_omission_{item.id}",
            )
            submitted = st.form_submit_button("Check the account ripple", type="primary", width="stretch")
        if submitted:
            if effect is None or omission is None:
                st.warning("Complete both choices before checking your reasoning.")
            else:
                result = evaluate_account_challenge(item.id, effect, ending_a, ending_b, omission)
                responses = dict(st.session_state.ct_account_responses)
                responses[item.id] = {
                    "effect": effect,
                    "ending_a": ending_a,
                    "ending_b": ending_b,
                    "omission": omission,
                }
                st.session_state.ct_account_responses = responses
                record_attempt(st.session_state, f"account:{item.id}", bool(result["correct"]))
                st.rerun()

    if response is not None:
        result = evaluate_account_challenge(
            item.id,
            str(response["effect"]),
            int(response["ending_a"]),
            int(response["ending_b"]),
            str(response["omission"]),
        )
        checks = result["checks"]
        expected = result["expected"]
        render_feedback_row("Account directions", bool(checks["effect"]), str(expected["effect"]))
        render_feedback_row(
            f"Ending {item.account_a}",
            bool(checks["ending_a"]),
            "Start with the unadjusted balance and apply the increase or decrease.",
            format_currency(int(expected["ending_a"])),
        )
        render_feedback_row(
            f"Ending {item.account_b}",
            bool(checks["ending_b"]),
            "Start with the unadjusted balance and apply the increase or decrease.",
            format_currency(int(expected["ending_b"])),
        )
        render_feedback_row("Omission effect", bool(checks["omission"]), str(expected["omission"]))
        st.info(str(result["explanation"]))
        if result["correct"]:
            st.button(
                "Continue",
                type="primary",
                width="stretch",
                on_click=advance_item,
                args=("ct_account_index", len(ACCOUNT_CHALLENGES), 4),
            )
        else:
            st.button(
                "Revise my account analysis",
                width="stretch",
                on_click=remove_response,
                args=("ct_account_responses", item.id),
            )


def render_statement_cards() -> None:
    balances = adjusted_balances()
    values = statement_values(balances)
    income, retained, position = st.columns(3)
    with income:
        st.markdown(
            f"""
            <div class="statement">
              <div class="statement-title">Income Statement</div><div class="statement-period">Month ended May 31</div>
              <div class="statement-line"><span>Service Revenue</span><span class="amount">{format_currency(balances['Service Revenue'])}</span></div>
              <div class="statement-section">Expenses</div>
              <div class="statement-line indent"><span>Salaries</span><span class="amount">{format_currency(balances['Salaries Expense'])}</span></div>
              <div class="statement-line indent"><span>Rent</span><span class="amount">{format_currency(balances['Rent Expense'])}</span></div>
              <div class="statement-line indent"><span>Supplies</span><span class="amount">{format_currency(balances['Supplies Expense'])}</span></div>
              <div class="statement-line indent"><span>Insurance</span><span class="amount">{format_currency(balances['Insurance Expense'])}</span></div>
              <div class="statement-line indent"><span>Interest</span><span class="amount">{format_currency(balances['Interest Expense'])}</span></div>
              <div class="statement-line total"><span>Total expenses</span><span class="amount">{format_currency(values['total_expenses'])}</span></div>
              <div class="statement-line grand"><span>Net income</span><span class="amount">{format_currency(values['net_income'])}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with retained:
        st.markdown(
            f"""
            <div class="statement">
              <div class="statement-title">Retained Earnings Statement</div><div class="statement-period">Month ended May 31</div>
              <div class="statement-line"><span>Beginning retained earnings</span><span class="amount">{format_currency(0)}</span></div>
              <div class="statement-line"><span>Add: Net income</span><span class="amount">{format_currency(values['net_income'])}</span></div>
              <div class="statement-line"><span>Less: Dividends</span><span class="amount">{format_currency(0)}</span></div>
              <div class="statement-line grand"><span>Ending retained earnings</span><span class="amount">{format_currency(values['ending_retained_earnings'])}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with position:
        st.markdown(
            f"""
            <div class="statement">
              <div class="statement-title">Balance Sheet</div><div class="statement-period">May 31</div>
              <div class="statement-line total"><span>Total assets</span><span class="amount">{format_currency(values['total_assets'])}</span></div>
              <div class="statement-line total"><span>Total liabilities</span><span class="amount">{format_currency(values['total_liabilities'])}</span></div>
              <div class="statement-line"><span>Common Stock</span><span class="amount">{format_currency(balances['Common Stock'])}</span></div>
              <div class="statement-line"><span>Retained Earnings</span><span class="amount">{format_currency(values['ending_retained_earnings'])}</span></div>
              <div class="statement-line grand"><span>Total liabilities and equity</span><span class="amount">{format_currency(values['total_liabilities_equity'])}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_statement_stage() -> None:
    st.markdown('<div class="eyebrow">Step 4 of the reasoning chain</div>', unsafe_allow_html=True)
    st.header("Turn the adjusted accounts into statements")
    st.write("Use the unadjusted balances and the net changes below. Calculate the adjusted totals that flow through the three financial statements.")
    worksheet = [{key: value for key, value in row.items() if key != "Adjusted"} for row in balance_rows()]
    st.dataframe(worksheet, width="stretch", hide_index=True)
    st.caption("A positive change increases the account. A negative change decreases it.")

    if not st.session_state.ct_statement_submitted:
        prior = dict(st.session_state.ct_statement_responses)
        with st.form("statement_form"):
            responses = {}
            cols = st.columns(2)
            for index, (key, label) in enumerate(STATEMENT_FIELDS):
                responses[key] = int(
                    cols[index % 2].number_input(
                        label,
                        min_value=0,
                        max_value=10_000_000,
                        value=int(prior.get(key, 0)),
                        step=100,
                        key=f"widget_statement_{key}",
                    )
                )
            submitted = st.form_submit_button("Check the financial statements", type="primary", width="stretch")
        if submitted:
            results = evaluate_statement_responses(responses)
            previous = dict(st.session_state.ct_statement_responses)
            for key, result in results.items():
                score_key = f"statement:{key}"
                if score_key not in st.session_state.ct_first_pass or previous.get(key) != responses[key]:
                    record_attempt(st.session_state, score_key, bool(result["correct"]))
            st.session_state.ct_statement_responses = responses
            st.session_state.ct_statement_submitted = True
            st.rerun()

    if st.session_state.ct_statement_submitted:
        results = evaluate_statement_responses(st.session_state.ct_statement_responses)
        all_correct = all(bool(result["correct"]) for result in results.values())
        for result in results.values():
            render_feedback_row(
                str(result["label"]),
                bool(result["correct"]),
                "Use the adjusted account balances and the statement flow.",
                format_currency(int(result["expected"])),
            )
        if all_correct:
            st.success("The May statements now tell one consistent story. Net income flows into retained earnings, and the balance sheet balances.")
            st.subheader("Completed statements")
            render_statement_cards()
            with st.expander("See every adjusted account balance"):
                st.dataframe(balance_rows(), width="stretch", hide_index=True)
            st.button("Continue to the integrity review", type="primary", width="stretch", on_click=set_stage, args=(5,))
        else:
            st.warning("Some totals still reflect the unadjusted records or an incomplete statement flow. Review the highlighted amounts and try again.")
            if st.button("Revise the statement totals", width="stretch"):
                st.session_state.ct_statement_submitted = False


def category_score(prefix: str, count: int) -> str:
    first_pass = st.session_state.ct_first_pass
    correct = sum(1 for key, value in first_pass.items() if key.startswith(prefix) and value)
    return f"{correct}/{count}"


def render_completion() -> None:
    score = score_summary(st.session_state)
    st.success("Close complete. Every recognition decision, account change, ending balance, and financial-statement total has been resolved.")
    st.markdown(
        f"""
        <div class="score-grid">
          <div class="score-box"><strong>{category_score('recognition:', len(RECOGNITION_QUESTIONS))}</strong><span>Timing first pass</span></div>
          <div class="score-box"><strong>{category_score('classification:', len(ADJUSTMENT_ITEMS))}</strong><span>Classification first pass</span></div>
          <div class="score-box"><strong>{category_score('account:', len(ACCOUNT_CHALLENGES))}</strong><span>Account ripple first pass</span></div>
          <div class="score-box"><strong>{category_score('statement:', len(STATEMENT_FIELDS))}</strong><span>Statement totals first pass</span></div>
          <div class="score-box"><strong>{category_score('integrity:', len(INTEGRITY_SCENARIOS))}</strong><span>Integrity first pass</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"First-pass decisions: {score['correct']} of {score['total']} | Practice revisions used: {score['revisions']} | Final mastery: complete"
    )
    st.subheader("The complete Chapter 6 chain")
    st.markdown(
        """
        1. Identify when the economic activity occurred.
        2. Decide whether cash came before or after recognition.
        3. Classify the needed adjustment.
        4. Increase or decrease the affected accounts and calculate ending balances.
        5. Trace the effect through net income, retained earnings, and the balance sheet.
        6. Reject changes that make the reporting period look better by making it less faithful.
        """
    )
    st.subheader("Debrief with your team")
    st.markdown(
        """
        - Which item was most tempting to treat as a cash-basis event?
        - Which omitted adjustment changed the financial story most dramatically?
        - Why can a company have balanced financial statements that are still incomplete or misleading?
        """
    )
    st.button("Start over", width="stretch", on_click=restart_activity)


def render_integrity_stage() -> None:
    st.markdown('<div class="eyebrow">Step 5 of the reasoning chain</div>', unsafe_allow_html=True)
    st.header("Protect the financial story")
    st.write("Management wants strong results. Decide whether each proposal still gives users a faithful picture of May.")
    index = int(st.session_state.ct_integrity_index)

    if len(st.session_state.ct_integrity_responses) == len(INTEGRITY_SCENARIOS):
        last = INTEGRITY_SCENARIOS[-1]
        last_result = evaluate_integrity(last.id, st.session_state.ct_integrity_responses[last.id])
        if last_result["correct"]:
            render_completion()
            return

    item = INTEGRITY_SCENARIOS[index]
    st.progress((index + 1) / len(INTEGRITY_SCENARIOS), text=f"Integrity decision {index + 1} of {len(INTEGRITY_SCENARIOS)}")
    render_card("Manager proposal", item.title, item.proposal)
    response = st.session_state.ct_integrity_responses.get(item.id)
    if response is None:
        with st.form(f"integrity_form_{item.id}"):
            selected = st.radio(
                "Would you approve this reporting choice?",
                item.options,
                index=None,
                key=f"widget_integrity_{item.id}",
            )
            submitted = st.form_submit_button("Evaluate the proposal", type="primary", width="stretch")
        if submitted:
            if selected is None:
                st.warning("Choose a response before evaluating the proposal.")
            else:
                result = evaluate_integrity(item.id, selected)
                store_simple_answer(
                    "ct_integrity_responses",
                    item.id,
                    selected,
                    f"integrity:{item.id}",
                    bool(result["correct"]),
                )
                st.rerun()

    if response is not None:
        result = evaluate_integrity(item.id, response)
        if result["correct"]:
            st.success(f"Sound judgment. {result['explanation']}")
        else:
            st.warning(f"This conclusion needs another look. {result['explanation']}")
        st.info(f"Financial-statement effect: {result['statement_effect']}")
        if result["correct"]:
            if index == len(INTEGRITY_SCENARIOS) - 1:
                st.button(
                    "Complete the close",
                    type="primary",
                    width="stretch",
                    on_click=advance_item,
                    args=("ct_integrity_index", len(INTEGRITY_SCENARIOS), 5),
                )
            else:
                st.button(
                    "Continue",
                    type="primary",
                    width="stretch",
                    on_click=advance_item,
                    args=("ct_integrity_index", len(INTEGRITY_SCENARIOS), 5),
                )
        else:
            st.button(
                "Revise my judgment",
                width="stretch",
                on_click=remove_response,
                args=("ct_integrity_responses", item.id),
            )


initialize_state()
st.markdown(APP_CSS, unsafe_allow_html=True)
render_hero()
render_stage_row()

with st.sidebar:
    st.header("Closing Time")
    st.write(f"Reporting date: {REPORTING_DATE}")
    st.write("Your progress is saved anonymously in this page's address so a refresh does not erase your work.")
    st.button("Start over", width="stretch", on_click=restart_activity)

stage = int(st.session_state.ct_stage)
if stage == 0:
    render_briefing()
elif stage == 1:
    render_recognition_stage()
elif stage == 2:
    render_classification_stage()
elif stage == 3:
    render_account_stage()
elif stage == 4:
    render_statement_stage()
else:
    render_integrity_stage()

sync_progress_query(st.session_state, st.query_params)
