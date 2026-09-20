import base64
import json
import unittest
import zlib

from closing_time.case_data import (
    ACCOUNT_CHALLENGES,
    ADJUSTMENT_ITEMS,
    INTEGRITY_SCENARIOS,
    RECOGNITION_QUESTIONS,
    STATEMENT_FIELDS,
)
from closing_time.engine import statement_values
from closing_time.progress import (
    SNAPSHOT_PARAM,
    activity_defaults,
    decode_snapshot,
    encode_state,
    record_attempt,
    reset_saved_progress,
    restore_session_state,
    score_summary,
    snapshot_from_state,
)


def encode_raw(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(zlib.compress(raw)).decode("ascii").rstrip("=")


def completed_state():
    state = activity_defaults()
    state["ct_stage"] = 5
    state["ct_recognition_index"] = len(RECOGNITION_QUESTIONS) - 1
    state["ct_recognition_responses"] = {item.id: item.correct for item in RECOGNITION_QUESTIONS}
    state["ct_classification_index"] = len(ADJUSTMENT_ITEMS) - 1
    state["ct_classification_responses"] = {item.id: item.classification for item in ADJUSTMENT_ITEMS}
    state["ct_account_index"] = len(ACCOUNT_CHALLENGES) - 1
    state["ct_account_responses"] = {
        item.id: {
            "effect": item.correct_effect,
            "ending_a": item.ending_a,
            "ending_b": item.ending_b,
            "omission": item.correct_omission,
        }
        for item in ACCOUNT_CHALLENGES
    }
    expected = statement_values()
    state["ct_statement_responses"] = {key: expected[key] for key, _ in STATEMENT_FIELDS}
    state["ct_statement_submitted"] = True
    state["ct_integrity_index"] = len(INTEGRITY_SCENARIOS) - 1
    state["ct_integrity_responses"] = {item.id: item.correct for item in INTEGRITY_SCENARIOS}
    return state


class ProgressSnapshotTests(unittest.TestCase):
    def test_round_trip_completed_progress(self):
        state = completed_state()
        for item in RECOGNITION_QUESTIONS:
            record_attempt(state, f"recognition:{item.id}", True)
        token = encode_state(state)
        restored = decode_snapshot(token)
        self.assertIsNotNone(restored)
        self.assertEqual(restored["ct_stage"], 5)
        self.assertEqual(restored["ct_statement_responses"]["net_income"], 17_100)
        self.assertNotIn("name", token.lower())
        self.assertNotIn("email", token.lower())

    def test_current_incorrect_response_can_be_restored_for_revision(self):
        state = activity_defaults()
        state["ct_stage"] = 1
        state["ct_recognition_responses"] = {
            RECOGNITION_QUESTIONS[0].id: RECOGNITION_QUESTIONS[0].options[0]
        }
        record_attempt(state, "recognition:insurance_month", False)
        restored = decode_snapshot(encode_state(state))
        self.assertIsNotNone(restored)
        self.assertEqual(restored["ct_attempts"]["recognition:insurance_month"], 1)
        self.assertFalse(restored["ct_first_pass"]["recognition:insurance_month"])

    def test_unsubmitted_drafts_survive_refresh(self):
        state = activity_defaults()
        state["ct_stage"] = 3
        state["ct_recognition_index"] = len(RECOGNITION_QUESTIONS) - 1
        state["ct_recognition_responses"] = {item.id: item.correct for item in RECOGNITION_QUESTIONS}
        state["ct_classification_index"] = len(ADJUSTMENT_ITEMS) - 1
        state["ct_classification_responses"] = {item.id: item.classification for item in ADJUSTMENT_ITEMS}
        current = ACCOUNT_CHALLENGES[0]
        state["ct_drafts"]["account"][current.id] = {
            "effect": current.correct_effect,
            "ending_a": current.ending_a,
        }

        restored = decode_snapshot(encode_state(state))

        self.assertIsNotNone(restored)
        self.assertEqual(restored["ct_drafts"]["account"][current.id]["effect"], current.correct_effect)
        self.assertEqual(restored["ct_drafts"]["account"][current.id]["ending_a"], current.ending_a)

    def test_skipping_a_required_stage_is_rejected(self):
        state = activity_defaults()
        state["ct_stage"] = 3
        token = encode_state(state)
        self.assertIsNone(decode_snapshot(token))

    def test_incorrect_completed_statement_stage_is_rejected(self):
        state = completed_state()
        raw_token = encode_state(state)
        restored = decode_snapshot(raw_token)
        self.assertIsNotNone(restored)

        raw = snapshot_from_state(state)
        raw["sr"] = dict(raw["sr"], net_income=12_800)
        self.assertIsNone(decode_snapshot(encode_raw(raw)))

    def test_malformed_or_oversized_tokens_are_rejected(self):
        self.assertIsNone(decode_snapshot("not-a-valid-token"))
        self.assertIsNone(decode_snapshot("x" * 12_001))

    def test_restore_and_reset(self):
        state = completed_state()
        destination = {}
        self.assertTrue(restore_session_state(destination, encode_state(state)))
        self.assertEqual(destination["ct_stage"], 5)

        query = {}
        reset_saved_progress(destination, query)
        self.assertEqual(destination["ct_stage"], 0)
        self.assertEqual(destination["ct_recognition_responses"], {})
        self.assertIn(SNAPSHOT_PARAM, query)
        self.assertIsNotNone(decode_snapshot(query[SNAPSHOT_PARAM]))

    def test_score_summary_tracks_first_pass_and_revisions(self):
        state = activity_defaults()
        record_attempt(state, "recognition:insurance_month", False)
        record_attempt(state, "recognition:insurance_month", True)
        record_attempt(state, "recognition:deposit_earned", True)
        score = score_summary(state)
        self.assertEqual(score["attempted"], 2)
        self.assertEqual(score["correct"], 1)
        self.assertEqual(score["revisions"], 1)


if __name__ == "__main__":
    unittest.main()
