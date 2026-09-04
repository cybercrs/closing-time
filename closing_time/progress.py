"""Compact, validated, non-identifying progress snapshots."""

from __future__ import annotations

import base64
import json
import zlib
from collections.abc import MutableMapping
from typing import Any

from closing_time.case_data import (
    ACCOUNT_CHALLENGES,
    ADJUSTMENT_ITEMS,
    CLASSIFICATION_OPTIONS,
    INTEGRITY_SCENARIOS,
    RECOGNITION_QUESTIONS,
    STATEMENT_FIELDS,
)


SNAPSHOT_PARAM = "progress"
SNAPSHOT_VERSION = 1
MAX_TOKEN_LENGTH = 12_000
MAX_JSON_BYTES = 24_000


def activity_defaults() -> dict[str, Any]:
    return {
        "ct_stage": 0,
        "ct_recognition_index": 0,
        "ct_recognition_responses": {},
        "ct_classification_index": 0,
        "ct_classification_responses": {},
        "ct_account_index": 0,
        "ct_account_responses": {},
        "ct_statement_responses": {},
        "ct_statement_submitted": False,
        "ct_integrity_index": 0,
        "ct_integrity_responses": {},
        "ct_attempts": {},
        "ct_first_pass": {},
    }


def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")


def _decode(token: str) -> object:
    padding = "=" * (-len(token) % 4)
    compressed = base64.b64decode(token + padding, altchars=b"-_", validate=True)
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(compressed, MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES or decompressor.unconsumed_tail:
        raise ValueError("Snapshot is too large")
    raw += decompressor.flush(MAX_JSON_BYTES + 1 - len(raw))
    if len(raw) > MAX_JSON_BYTES or decompressor.unused_data:
        raise ValueError("Snapshot is invalid")
    return json.loads(raw.decode("utf-8"))


def _answer_prefix(raw: object, items, valid_options) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Answers must be an object")
    ids = [item.id for item in items]
    if set(raw) != set(ids[: len(raw)]):
        raise ValueError("Answers must follow the activity order")
    normalized = {}
    for item in items[: len(raw)]:
        value = raw[item.id]
        options = valid_options(item)
        if not isinstance(value, str) or value not in options:
            raise ValueError("Unknown answer")
        normalized[item.id] = value
    return normalized


def _require_index(value: object, item_count: int) -> int:
    if type(value) is not int or not 0 <= value < item_count:
        raise ValueError("Invalid activity index")
    return value


def _validate_account_answers(raw: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw, dict):
        raise ValueError("Account answers must be an object")
    ids = [item.id for item in ACCOUNT_CHALLENGES]
    if set(raw) != set(ids[: len(raw)]):
        raise ValueError("Account answers must follow the activity order")
    normalized = {}
    for item in ACCOUNT_CHALLENGES[: len(raw)]:
        value = raw[item.id]
        if not isinstance(value, dict) or set(value) != {"effect", "ending_a", "ending_b", "omission"}:
            raise ValueError("Invalid account answer")
        if value["effect"] not in item.effect_options or value["omission"] not in item.omission_options:
            raise ValueError("Unknown account choice")
        if type(value["ending_a"]) is not int or type(value["ending_b"]) is not int:
            raise ValueError("Ending balances must be whole dollars")
        if not 0 <= value["ending_a"] <= 1_000_000 or not 0 <= value["ending_b"] <= 1_000_000:
            raise ValueError("Ending balance is out of range")
        normalized[item.id] = dict(value)
    return normalized


def _validate_statement_answers(raw: object, submitted: bool) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ValueError("Statement answers must be an object")
    valid_keys = [key for key, _ in STATEMENT_FIELDS]
    if set(raw) - set(valid_keys):
        raise ValueError("Unknown statement field")
    if submitted and set(raw) != set(valid_keys):
        raise ValueError("Submitted statement answers are incomplete")
    normalized = {}
    for key, value in raw.items():
        if type(value) is not int or not 0 <= value <= 10_000_000:
            raise ValueError("Invalid statement amount")
        normalized[key] = value
    return normalized


def _valid_score_keys() -> set[str]:
    keys = {f"recognition:{item.id}" for item in RECOGNITION_QUESTIONS}
    keys |= {f"classification:{item.id}" for item in ADJUSTMENT_ITEMS}
    keys |= {f"account:{item.id}" for item in ACCOUNT_CHALLENGES}
    keys |= {f"statement:{key}" for key, _ in STATEMENT_FIELDS}
    keys |= {f"integrity:{item.id}" for item in INTEGRITY_SCENARIOS}
    return keys


def validate_snapshot(raw: object) -> dict[str, Any]:
    expected_keys = {"v", "s", "ri", "rr", "ci", "cr", "ai", "ar", "sr", "ss", "ii", "ir", "at", "fp"}
    if not isinstance(raw, dict) or set(raw) != expected_keys or raw["v"] != SNAPSHOT_VERSION:
        raise ValueError("Unsupported snapshot")

    stage = raw["s"]
    if type(stage) is not int or not 0 <= stage <= 5:
        raise ValueError("Invalid stage")

    recognition = _answer_prefix(raw["rr"], RECOGNITION_QUESTIONS, lambda item: item.options)
    classification = _answer_prefix(raw["cr"], ADJUSTMENT_ITEMS, lambda _item: CLASSIFICATION_OPTIONS)
    account = _validate_account_answers(raw["ar"])
    integrity = _answer_prefix(raw["ir"], INTEGRITY_SCENARIOS, lambda item: item.options)

    recognition_index = _require_index(raw["ri"], len(RECOGNITION_QUESTIONS))
    classification_index = _require_index(raw["ci"], len(ADJUSTMENT_ITEMS))
    account_index = _require_index(raw["ai"], len(ACCOUNT_CHALLENGES))
    integrity_index = _require_index(raw["ii"], len(INTEGRITY_SCENARIOS))

    submitted = raw["ss"]
    if type(submitted) is not bool:
        raise ValueError("Invalid statement status")
    statements = _validate_statement_answers(raw["sr"], submitted)

    if not isinstance(raw["at"], dict) or not isinstance(raw["fp"], dict):
        raise ValueError("Invalid score history")
    valid_score_keys = _valid_score_keys()
    attempts = {}
    for key, value in raw["at"].items():
        if key not in valid_score_keys or type(value) is not int or not 1 <= value <= 99:
            raise ValueError("Invalid attempt history")
        attempts[key] = value
    first_pass = {}
    for key, value in raw["fp"].items():
        if key not in valid_score_keys or type(value) is not bool:
            raise ValueError("Invalid first-pass history")
        first_pass[key] = value

    if stage >= 2 and len(recognition) != len(RECOGNITION_QUESTIONS):
        raise ValueError("Recognition stage is incomplete")
    if stage >= 2 and any(recognition[item.id] != item.correct for item in RECOGNITION_QUESTIONS):
        raise ValueError("Recognition stage contains an unresolved answer")
    if stage >= 3 and len(classification) != len(ADJUSTMENT_ITEMS):
        raise ValueError("Classification stage is incomplete")
    if stage >= 3 and any(classification[item.id] != item.classification for item in ADJUSTMENT_ITEMS):
        raise ValueError("Classification stage contains an unresolved answer")
    if stage >= 4 and len(account) != len(ACCOUNT_CHALLENGES):
        raise ValueError("Account stage is incomplete")
    if stage >= 4:
        for item in ACCOUNT_CHALLENGES:
            answer = account[item.id]
            if not (
                answer["effect"] == item.correct_effect
                and answer["ending_a"] == item.ending_a
                and answer["ending_b"] == item.ending_b
                and answer["omission"] == item.correct_omission
            ):
                raise ValueError("Account stage contains an unresolved answer")
    if stage >= 5 and not submitted:
        raise ValueError("Statement stage is incomplete")
    if stage >= 5:
        from closing_time.engine import statement_values

        expected_statements = statement_values()
        if any(statements.get(key) != expected_statements[key] for key, _ in STATEMENT_FIELDS):
            raise ValueError("Statement stage contains an unresolved amount")

    for position, item in enumerate(RECOGNITION_QUESTIONS[: max(0, recognition_index)]):
        if recognition.get(item.id) != item.correct:
            raise ValueError("A prior recognition answer is unresolved")
    for position, item in enumerate(ADJUSTMENT_ITEMS[: max(0, classification_index)]):
        if classification.get(item.id) != item.classification:
            raise ValueError("A prior classification answer is unresolved")
    for position, item in enumerate(ACCOUNT_CHALLENGES[: max(0, account_index)]):
        answer = account.get(item.id)
        if answer is None or not (
            answer["effect"] == item.correct_effect
            and answer["ending_a"] == item.ending_a
            and answer["ending_b"] == item.ending_b
            and answer["omission"] == item.correct_omission
        ):
            raise ValueError("A prior account answer is unresolved")
    for position, item in enumerate(INTEGRITY_SCENARIOS[: max(0, integrity_index)]):
        if integrity.get(item.id) != item.correct:
            raise ValueError("A prior integrity answer is unresolved")

    if len(recognition) not in {recognition_index, recognition_index + 1} and len(recognition) != len(RECOGNITION_QUESTIONS):
        raise ValueError("Recognition position is inconsistent")
    if len(classification) not in {classification_index, classification_index + 1} and len(classification) != len(ADJUSTMENT_ITEMS):
        raise ValueError("Classification position is inconsistent")
    if len(account) not in {account_index, account_index + 1} and len(account) != len(ACCOUNT_CHALLENGES):
        raise ValueError("Account position is inconsistent")
    if len(integrity) not in {integrity_index, integrity_index + 1} and len(integrity) != len(INTEGRITY_SCENARIOS):
        raise ValueError("Integrity position is inconsistent")

    return {
        "ct_stage": stage,
        "ct_recognition_index": recognition_index,
        "ct_recognition_responses": recognition,
        "ct_classification_index": classification_index,
        "ct_classification_responses": classification,
        "ct_account_index": account_index,
        "ct_account_responses": account,
        "ct_statement_responses": statements,
        "ct_statement_submitted": submitted,
        "ct_integrity_index": integrity_index,
        "ct_integrity_responses": integrity,
        "ct_attempts": attempts,
        "ct_first_pass": first_pass,
    }


def snapshot_from_state(state: MutableMapping[str, Any]) -> dict[str, Any]:
    return {
        "v": SNAPSHOT_VERSION,
        "s": state["ct_stage"],
        "ri": state["ct_recognition_index"],
        "rr": state["ct_recognition_responses"],
        "ci": state["ct_classification_index"],
        "cr": state["ct_classification_responses"],
        "ai": state["ct_account_index"],
        "ar": state["ct_account_responses"],
        "sr": state["ct_statement_responses"],
        "ss": state["ct_statement_submitted"],
        "ii": state["ct_integrity_index"],
        "ir": state["ct_integrity_responses"],
        "at": state["ct_attempts"],
        "fp": state["ct_first_pass"],
    }


def encode_state(state: MutableMapping[str, Any]) -> str:
    return _encode(snapshot_from_state(state))


def decode_snapshot(token: object) -> dict[str, Any] | None:
    if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    try:
        return validate_snapshot(_decode(token))
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, zlib.error):
        return None


def restore_session_state(state: MutableMapping[str, Any], token: object) -> bool:
    restored = decode_snapshot(token)
    if restored is None:
        return False
    state.update(restored)
    return True


def sync_progress_query(state: MutableMapping[str, Any], query_params: MutableMapping[str, Any]) -> None:
    token = encode_state(state)
    current = query_params.get(SNAPSHOT_PARAM)
    if isinstance(current, list):
        current = current[0] if current else None
    if current != token:
        query_params[SNAPSHOT_PARAM] = token


def reset_saved_progress(state: MutableMapping[str, Any], query_params: MutableMapping[str, Any]) -> None:
    for key in list(state):
        if key.startswith("ct_") or key.startswith("widget_"):
            del state[key]
    state.update(activity_defaults())
    query_params[SNAPSHOT_PARAM] = encode_state(state)


def record_attempt(
    state: MutableMapping[str, Any],
    score_key: str,
    correct: bool,
) -> None:
    attempts = dict(state["ct_attempts"])
    first_pass = dict(state["ct_first_pass"])
    attempts[score_key] = attempts.get(score_key, 0) + 1
    if score_key not in first_pass:
        first_pass[score_key] = bool(correct)
    state["ct_attempts"] = attempts
    state["ct_first_pass"] = first_pass


def score_summary(state: MutableMapping[str, Any]) -> dict[str, int]:
    first_pass = state.get("ct_first_pass", {})
    total = len(_valid_score_keys())
    attempted = len(first_pass)
    correct = sum(1 for value in first_pass.values() if value)
    revisions = sum(max(0, value - 1) for value in state.get("ct_attempts", {}).values())
    return {
        "correct": correct,
        "attempted": attempted,
        "total": total,
        "revisions": revisions,
    }
