import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest
from browser.build import shared_source


def browser_app():
    directory = Path(tempfile.mkdtemp(prefix='browser-apptest-'))
    (directory / 'app.py').write_text(Path('browser/app.py').read_text())
    (directory / 'shared_app.py').write_text(shared_source())
    return AppTest.from_file(directory / 'app.py', default_timeout=30)
