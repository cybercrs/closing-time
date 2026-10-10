"""Native review navigation and isolated rendering of already reached work."""
from __future__ import annotations

import copy
from pathlib import Path
import streamlit as st

VIEW_KEY = '_browser_view'
VIEW_PARAM = 'view'
REVIEW_NOTICE = 'Review only. Return to your current page to continue the activity.'


class State(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as error:
            raise AttributeError(key) from error

    def __setattr__(self, key, value):
        self[key] = value


class LiveUI:
    """Keep native controls, with browser-safe draft transmission outside forms."""
    def __getattr__(self, name):
        command = getattr(st, name)
        if name in {'radio', 'selectbox', 'multiselect', 'number_input', 'text_area'}:
            def widget(*args, **kwargs):
                value = command(*args, **kwargs)
                key = kwargs.get('key')
                if key:
                    keys = set(st.session_state.get('_browser_widgets', []))
                    keys.add(key)
                    st.session_state['_browser_widgets'] = sorted(keys)
                return value
            return widget
        return command

    def form(self, key, **kwargs):
        # Each field reaches Python on change so Back and refresh retain drafts.
        # Submission remains an explicit action using the original validation.
        return st.container(key=key)

    def form_submit_button(self, label, **kwargs):
        return self.button(label, **kwargs)

    def button(self, label, **kwargs):
        if 'use_container_width' in kwargs:
            kwargs['width'] = 'stretch' if kwargs.pop('use_container_width') else 'content'
        return st.button(label, **kwargs)


class ReviewUI(LiveUI):
    """Render with a private state copy and no callbacks or interactive controls."""
    def __init__(self, state):
        self.session_state = State(copy.deepcopy(dict(state)))
        self.query_params = {}

    def button(self, *args, **kwargs):
        return False

    def radio(self, label, options, **kwargs):
        options = list(options)
        default = options[kwargs.get('index', 0)] if kwargs.get('index', 0) is not None else None
        value = self.session_state.get(kwargs.get('key'), default)
        if value not in options:
            value = default
        self._show(label, value)
        return value

    selectbox = radio

    def multiselect(self, label, options, **kwargs):
        value = self.session_state.get(kwargs.get('key'), kwargs.get('default', []))
        self._show(label, ', '.join(str(item) for item in value))
        return value

    def number_input(self, label, **kwargs):
        value = self.session_state.get(kwargs.get('key'), kwargs.get('value'))
        self._show(label, value)
        return value

    def text_area(self, label, **kwargs):
        value = self.session_state.get(kwargs.get('key'), kwargs.get('value', ''))
        self._show(label, value)
        return value

    def _show(self, label, value):
        st.write(f'{label}: {value if value is not None else "No saved selection"}')

    def rerun(self, *args, **kwargs):
        return None

    def iframe(self, *args, **kwargs):
        return None


def restore_view(state, raw, reached):
    try:
        view = int(raw) if isinstance(raw, str) else -1
    except ValueError:
        view = -1
    state[VIEW_KEY] = view if 0 <= view <= reached else reached


def move(state, direction, reached):
    if direction not in (-1, 1):
        raise ValueError('Direction must be Back or Forward')
    view = state[VIEW_KEY]
    target = view + direction
    if 0 <= target <= reached:
        state[VIEW_KEY] = target
        state['_browser_scroll'] = True
        return True
    return False


def keep_widgets(state):
    # Mark previously reached widget state as session-owned before rendering.
    # No post-render assignment and no new Streamlit persist_state API required.
    for key in state.get('_browser_widgets', []):
        if key in state:
            state[key] = state[key]


def navigation(state, reached, count):
    st.markdown(Path(__file__).with_name('navigation.css').read_text(), unsafe_allow_html=True)
    view = state[VIEW_KEY]
    with st.container(key='browser_navigation', horizontal=True,
                      horizontal_alignment='right', vertical_alignment='center', gap='xsmall'):
        st.caption(f'Page {view + 1} of {count}', width='content')
        st.button('Back', width=44, key='browser_back', disabled=view == 0,
                  help='Back: review the previous reached page. Earlier pages are read-only.',
                  on_click=move, args=(state, -1, reached))
        st.button('Forward', width=44, key='browser_forward', disabled=view >= reached,
                  help='Forward: review the next reached page. Use the activity controls on your current page.',
                  on_click=move, args=(state, 1, reached))
    if view < reached:
        st.info(REVIEW_NOTICE)


def save_view(state):
    if st.query_params.get(VIEW_PARAM) != str(state[VIEW_KEY]):
        st.query_params[VIEW_PARAM] = str(state[VIEW_KEY])


def scroll():
    if st.session_state.pop('_browser_scroll', False):
        st.iframe("<script>window.parent.document.querySelector('section[data-testid=stMain]')?.scrollTo(0,0)</script>",
                  height=1, tab_index=-1)
