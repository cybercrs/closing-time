START = 'Begin the close'
import unittest
import copy
from browser.common import VIEW_KEY, restore_view, move
from browser_support import browser_app


def button(app, label):
    return next(item for item in app.button if item.label == label)


class BrowserNavigationTests(unittest.TestCase):
    def test_move_changes_only_view(self):
        state = {'earned': 2, 'answers': {'first':'wrong'}, 'attempts': 3, VIEW_KEY:2}
        before = copy.deepcopy(state)
        self.assertTrue(move(state, -1, 2))
        self.assertEqual(state['answers'], before['answers'])
        self.assertEqual(state['attempts'], before['attempts'])
        self.assertEqual(state['earned'], before['earned'])
        self.assertTrue(move(state, 1, 2))
        self.assertFalse(move(state, 1, 2))
        restore_view(state, '999', 2)
        self.assertEqual(state[VIEW_KEY], 2)
        restore_view(state, '-1', 2)
        self.assertEqual(state[VIEW_KEY], 2)

    def test_review_refresh_and_future_view(self):
        app = browser_app().run()
        self.assertFalse(app.exception)
        button(app, START).click().run()
        self.assertFalse(app.exception)
        before = copy.deepcopy(app.query_params)
        for _ in range(3):
            button(app, 'Back').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.radio) + len(app.selectbox) + len(app.number_input) + len(app.text_area), 0)
            self.assertEqual([b.label for b in app.main.button], ['Back','Forward'])
            self.assertEqual(app.query_params['progress'], before['progress'])
            button(app, 'Forward').click().run()
            self.assertEqual(app.query_params['progress'], before['progress'])
        self.assertTrue(button(app,'Forward').disabled)
        resumed = browser_app()
        for key,value in app.query_params.items():
            resumed.query_params[key] = value
        resumed.query_params['view'] = '999'
        resumed.run()
        self.assertFalse(resumed.exception)
        self.assertEqual(resumed.session_state[VIEW_KEY], 1)
        self.assertTrue(button(resumed,'Forward').disabled)
