"""Export unchanged Closing Time teaching screens and Python accounting oracles."""
from __future__ import annotations
import copy
import itertools
import json
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from browser.build import shared_source
from closing_time import case_data as case, engine, progress

class State(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key, value):
        self[key] = value


class Container:
    def __init__(self, recorder, node):
        self.recorder, self.node = recorder, node

    def __enter__(self):
        self.recorder.stack.append(self.node["children"])
        return self

    def __exit__(self, *args):
        self.recorder.stack.pop()

    def metric(self, label, value, **kwargs):
        self.node["children"].append({"kind": "metric", "label": label, "value": value})


class Recorder:
    def __init__(self):
        self.session_state = State()
        self.stack = [[]]

    def node(self, kind, **kwargs):
        node = {"kind": kind, **kwargs}
        self.stack[-1].append(node)
        return node

    def set_page_config(self, **kwargs):
        pass

    def markdown(self, text, unsafe_allow_html=False):
        self.node("html" if unsafe_allow_html else "markdown", text=text.strip())

    def __getattr__(self, kind):
        if kind in {"title", "header", "subheader", "write", "success", "warning", "info", "caption", "error"}:
            return lambda text: self.node(kind, text=text.replace(r"\$", "$"))
        raise AttributeError(kind)

    def radio(self, label, options, **kwargs):
        options = list(options)
        self.node("radio", label=label.replace(r"\$", "$"),
                  options=[x.replace(r"\$", "$") for x in options], key=kwargs["key"])
        index = kwargs.get("index", 0)
        value = self.session_state.get(kwargs["key"], options[index] if index is not None else None)
        self.session_state[kwargs["key"]] = value
        return value

    def selectbox(self, label, options, **kwargs):
        options = list(options)
        self.node("select", label=label, options=options, key=kwargs["key"])
        index = kwargs.get("index", 0)
        value = self.session_state.get(kwargs["key"], options[index] if index is not None else None)
        self.session_state[kwargs["key"]] = value
        return value

    def button(self, label, **kwargs):
        self.node("button", label=label, key=kwargs.get("key"),
                  disabled=kwargs.get("disabled", False),
                  action=kwargs.get("on_click").__name__ if kwargs.get("on_click") else None)
        return False

    def form_submit_button(self, label, **kwargs):
        self.node("button", label=label, action=kwargs["on_click"].__name__)
        return False

    def progress(self, value, **kwargs):
        self.node("progress", value=value, text=kwargs.get("text", ""))

    def columns(self, count, **kwargs):
        count = count if isinstance(count, int) else len(count)
        group = self.node("columns", children=[])
        columns = []
        for _ in range(count):
            node = {"kind": "column", "children": []}
            group["children"].append(node)
            columns.append(Container(self, node))
        return columns

    def tabs(self, labels):
        group = self.node("tabs", children=[])
        tabs = []
        for label in labels:
            node = {"kind": "tab", "label": label, "children": []}
            group["children"].append(node)
            tabs.append(Container(self, node))
        return tabs

    def form(self, key):
        return Container(self, self.node("form", key=key, children=[]))

    def expander(self, label, **kwargs):
        return Container(self, self.node("details", label=label,
                                        expanded=kwargs.get("expanded", False), children=[]))


    def number_input(self, label, **kwargs):
        self.node("number", label=label, key=kwargs["key"], value=kwargs.get("value"),
                  step=kwargs.get("step", 1), placeholder=kwargs.get("placeholder", ""))
        return self.session_state.get(kwargs["key"], kwargs.get("value"))

    def multiselect(self, label, options, **kwargs):
        self.node("many", label=label, options=list(options), key=kwargs["key"], help=kwargs.get("help"))
        return self.session_state.get(kwargs["key"], [])

    def text_area(self, label, **kwargs):
        self.node("text", label=label, key=kwargs["key"], placeholder=kwargs.get("placeholder"),
                  maxLength=kwargs.get("max_chars"), help=kwargs.get("help"))
        return self.session_state.get(kwargs["key"], "")

    def dataframe(self, rows, **kwargs):
        self.node("table", rows=rows)

    def divider(self):
        self.node("divider")

    @property
    def sidebar(self):
        return Container(self, self.node("sidebar", children=[]))

    @contextmanager
    def capture(self):
        self.stack = [[]]
        yield self.stack[0]


GROUPS = (
    (1, "recognition", "r", "ri", "rr", case.RECOGNITION_QUESTIONS),
    (2, "classification", "c", "ci", "cr", case.ADJUSTMENT_ITEMS),
    (3, "account", "a", "ai", "ar", case.ACCOUNT_CHALLENGES),
    (5, "integrity", "i", "ii", "ir", case.INTEGRITY_SCENARIOS),
)
RENDERERS = ("render_briefing", "render_recognition_stage", "render_classification_stage",
             "render_account_stage", "render_statement_stage", "render_integrity_stage")


def state_at(stage, index=0, status="unanswered", seed=0):
    state = State(progress.activity_defaults())
    state.ct_stage = stage
    state.ct_shuffle_seed = seed
    for group_stage, prefix, _draft, _index, _responses, items in GROUPS:
        state["ct_" + prefix + "_index"] = len(items) - 1 if group_stage < stage else index if group_stage == stage else 0
        answers = {}
        for i, item in enumerate(items):
            if group_stage < stage or group_stage == stage and (i < index or i == index and status != "unanswered"):
                correct = group_stage < stage or i < index or status == "correct"
                if prefix == "account":
                    answers[item.id] = {
                        "effect": item.correct_effect if correct else next(value for value in item.effect_options if value != item.correct_effect),
                        "omission": item.correct_omission if correct else next(value for value in item.omission_options if value != item.correct_omission)}
                else:
                    options = case.CLASSIFICATION_OPTIONS if prefix == "classification" else item.options
                    expected = item.classification if prefix == "classification" else item.correct
                    answers[item.id] = expected if correct else next(value for value in options if value != expected)
                progress.record_attempt(state, prefix + ":" + item.id, correct)
        state["ct_" + prefix + "_responses"] = answers
        state.ct_drafts[prefix] = copy.deepcopy(answers)
    if stage > 4 or stage == 4 and status != "unanswered":
        state.ct_statement_submitted = True
        state.ct_statement_responses = {
            item.id: item.correct if stage > 4 or status == "correct" else next(value for value in item.options if value != item.correct)
            for item in case.STATEMENT_QUESTIONS}
        state.ct_drafts["statement"] = dict(state.ct_statement_responses)
        for item in case.STATEMENT_QUESTIONS:
            progress.record_attempt(state, "statement:" + item.id, state.ct_statement_responses[item.id] == item.correct)
    progress.validate_snapshot(progress.snapshot_from_state(state))
    return state


def export():
    here = Path(__file__).resolve().parent
    recorder = Recorder()
    namespace = {}
    with patch.dict(sys.modules, {"streamlit": recorder}):
        exec(compile(shared_source(), "original_teaching_renderer", "exec"), namespace)
    def feedback(label, correct, detail, value=""):
        if recorder.session_state.ct_stage == 3:
            recorder.node("account-feedback", field="effect" if label == "Account directions" else "omission")
        elif recorder.session_state.ct_stage == 4:
            recorder.node("statement-feedback", index=int(label.split()[-1]) - 1)
        else:
            raise ValueError("Unexpected feedback renderer context")
    namespace["render_feedback_row"] = feedback
    positions = [{"stage": 0, "index": 0}]
    for stage in range(1, 6):
        items = next((group[-1] for group in GROUPS if group[0] == stage), [None])
        positions.extend({"stage": stage, "index": index} for index in range(len(items)))
    screens, links = [], []
    for position in positions:
        variants = {}
        for status in ("unanswered", "wrong", "correct"):
            recorder.session_state = state_at(**position, status=status)
            with recorder.capture() as nodes:
                namespace[RENDERERS[position["stage"]]]()
            variants[status] = nodes
            if status == "unanswered":
                payload = progress.snapshot_from_state(recorder.session_state)
                links.append({"position": position, "token": progress.encode_state(recorder.session_state),
                              "wire": json.dumps(payload, separators=(",", ":"), sort_keys=True)})
        screens.append({"position": position, "variants": variants})
    with recorder.capture() as hero:
        namespace["render_hero"]()
    data = {
        "title": "Closing Time", "company": case.COMPANY_NAME, "date": case.REPORTING_DATE,
        "stages": namespace["STAGE_LABELS"], "positions": positions, "screens": screens, "hero": hero,
        "groups": [{"stage": stage, "prefix": prefix, "draft": draft, "indexKey": idx, "responseKey": responses,
                    "items": [asdict(item) for item in items]}
                   for stage, prefix, draft, idx, responses, items in GROUPS],
        "statements": [asdict(item) for item in case.STATEMENT_QUESTIONS],
        "classificationOptions": case.CLASSIFICATION_OPTIONS,
        "unadjusted": case.UNADJUSTED_BALANCES, "adjustments": [asdict(item) for item in case.ADJUSTMENT_ITEMS],
        "accountSets": {"assets": sorted(engine.ASSET_ACCOUNTS), "liabilities": sorted(engine.LIABILITY_ACCOUNTS),
            "equity": sorted(engine.EQUITY_ACCOUNTS), "expenses": sorted(engine.EXPENSE_ACCOUNTS)},
    }
    (here / "content.js").write_text("// Generated from unchanged Python teaching renderers.\nexport const DATA="
        + json.dumps(data, ensure_ascii=True, separators=(",", ":")) + ";\n")
    (here / "original.css").write_text(namespace["APP_CSS"].replace("<style>", "").replace("</style>", "").strip() + "\n")
    (here / "tests/legacy-links.json").write_text(json.dumps(links, indent=2) + "\n")
    oracles = {"adjusted": engine.adjusted_balances(), "statements": engine.statement_values(),
        "before": engine.statement_values(case.UNADJUSTED_BALANCES), "rows": engine.balance_rows(),
        "equation": engine.equation_check(), "snapshots": [], "shuffles": [], "evaluations": []}
    for position in positions:
        for status in ("unanswered", "wrong", "correct"):
            state = state_at(**position, status=status, seed=2**63 - 1)
            oracles["snapshots"].append({"position": position, "status": status,
                "wire": json.dumps(progress.snapshot_from_state(state), sort_keys=True, separators=(",", ":")),
                "token": progress.encode_state(state), "score": progress.score_summary(state)})
    for seed in (0, 1, 42, 2**53 + 1, 2**63 - 1):
        recorder.session_state = state_at(0, seed=seed)
        for item in case.ACCOUNT_CHALLENGES:
            for kind in ("effect", "omission"):
                options = getattr(item, kind + "_options")
                salt = "account-" + kind + ":" + item.id
                oracles["shuffles"].append({"seed": str(seed), "salt": salt, "input": options,
                    "output": namespace["shuffled"](options, salt)})
    for item in case.RECOGNITION_QUESTIONS:
        for answer in item.options:
            oracles["evaluations"].append({"group": "recognition", "id": item.id, "answer": answer,
                "result": engine.evaluate_recognition(item.id, answer)})
    for item in case.ADJUSTMENT_ITEMS:
        for answer in case.CLASSIFICATION_OPTIONS:
            oracles["evaluations"].append({"group": "classification", "id": item.id, "answer": answer,
                "result": engine.evaluate_classification(item.id, answer)})
    for item in case.ACCOUNT_CHALLENGES:
        for effect, omission in itertools.product(item.effect_options, item.omission_options):
            oracles["evaluations"].append({"group": "account", "id": item.id, "answer": {"effect": effect, "omission": omission},
                "result": engine.evaluate_account_challenge(item.id, effect, omission)})
    for item in case.INTEGRITY_SCENARIOS:
        for answer in item.options:
            oracles["evaluations"].append({"group": "integrity", "id": item.id, "answer": answer,
                "result": engine.evaluate_integrity(item.id, answer)})
    (here / "tests/python-oracles.json").write_text(json.dumps(oracles, indent=2) + "\n")
    print(json.dumps({"pages": len(positions), "rendered_variants": len(positions) * 3,
        "first_pass_checkpoints": 21, "answer_evaluations": len(oracles["evaluations"]),
        "shuffle_cases": len(oracles["shuffles"]), "app_owned_assets": [], "curriculum_changes": []}, indent=2))


if __name__ == "__main__":
    export()
