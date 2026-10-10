"""Flatten the case's stage and item indexes into reached review pages."""
from closing_time.case_data import RECOGNITION_QUESTIONS, ADJUSTMENT_ITEMS, ACCOUNT_CHALLENGES, INTEGRITY_SCENARIOS

COUNTS = (1, len(RECOGNITION_QUESTIONS), len(ADJUSTMENT_ITEMS), len(ACCOUNT_CHALLENGES), 1, len(INTEGRITY_SCENARIOS))
INDEX_KEYS = (None,'ct_recognition_index','ct_classification_index','ct_account_index',None,'ct_integrity_index')
PAGE_COUNT = sum(COUNTS)


def frontier(state):
    stage = state['ct_stage']
    index = state[INDEX_KEYS[stage]] if INDEX_KEYS[stage] else 0
    return sum(COUNTS[:stage]) + index


def position(view):
    for stage, count in enumerate(COUNTS):
        if view < count:
            return stage, view
        view -= count
    raise ValueError('Unreachable view')
