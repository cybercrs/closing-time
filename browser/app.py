"""Browser close; canonical progress retains the server's validation rules."""
import runpy
from pathlib import Path
import sys
# Stlite puts the entrypoint directory first; keep root packages authoritative.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from browser.common import LiveUI, ReviewUI, VIEW_KEY, restore_view, keep_widgets, navigation, save_view, scroll
from browser.navigation import frontier, position, PAGE_COUNT, INDEX_KEYS

app = runpy.run_path(str(Path(__file__).with_name('shared_app.py')))
g = app['set_stage'].__globals__
app['initialize_state']()
if VIEW_KEY not in st.session_state:
    restore_view(st.session_state, st.query_params.get('view'), frontier(st.session_state))
keep_widgets(st.session_state)


def transition(original, *args):
    if st.session_state[VIEW_KEY] != frontier(st.session_state):
        return
    original(*args)
    st.session_state[VIEW_KEY] = frontier(st.session_state)
    st.session_state['_browser_scroll'] = True


def restart():
    if st.session_state[VIEW_KEY] == frontier(st.session_state):
        app['restart_activity']()
        st.session_state[VIEW_KEY] = 0
        st.session_state['_browser_scroll'] = True


g.update(st=LiveUI(), set_stage=lambda stage: transition(app['set_stage'], stage),
         advance_item=lambda *args: transition(app['advance_item'], *args), restart_activity=restart)
# advance_item calls the patched set_stage. Its canonical mutation remains in
# the existing callback, then the viewed page follows the newly reached item.
st.markdown(app['APP_CSS'], unsafe_allow_html=True)
app['render_hero']()
reached = frontier(st.session_state)
with st.sidebar:
    st.header('Closing Time')
    st.write(f'Reporting date: {app["REPORTING_DATE"]}')
    st.button('Start over', on_click=restart, disabled=st.session_state[VIEW_KEY] < reached)
navigation(st.session_state, reached, PAGE_COUNT)
view = st.session_state[VIEW_KEY]
if view < reached:
    ui = ReviewUI(st.session_state)
    stage, index = position(view)
    ui.session_state.ct_stage = stage
    if INDEX_KEYS[stage]:
        ui.session_state[INDEX_KEYS[stage]] = index
    if stage == 5:
        # Later integrity answers must not make an earlier item's renderer
        # switch to the final debrief.
        ids = [item.id for item in app['INTEGRITY_SCENARIOS'][:index + 1]]
        ui.session_state.ct_integrity_responses = {key: value for key, value in ui.session_state.ct_integrity_responses.items() if key in ids}
    g['st'] = ui
else:
    stage, index = position(view)
app['render_stage_row']()
renderers = ('render_briefing','render_recognition_stage','render_classification_stage','render_account_stage','render_statement_stage','render_integrity_stage')
app[renderers[stage]]()
g['st'] = st
app['sync_progress_query'](st.session_state, st.query_params)
save_view(st.session_state)
scroll()
