# Closing Time

Closing Time is a Streamlit learning experience for introductory accounting. Students complete the May close for a fictional service business by deciding when revenue and expense belong, identifying accrual accounting transactions, determining account increases and decreases, comparing unadjusted and adjusted financial statements, and evaluating reporting-integrity choices.

The activity deliberately avoids journal mechanics. Student work is framed through recognition timing, account direction, financial-statement effects, and the connections among net income, retained earnings, and the accounting equation.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Test

```bash
python -m unittest discover -s tests -v
python -m py_compile streamlit_app.py closing_time/*.py
```

## Privacy and progress

The app requires no login, database, or student name. It stores only compact draft selections, numeric responses, stage position, and scoring flags in a validated URL parameter so browser refreshes can restore in-progress work. No written response or identifying information is included.

## Deployment

The repository is ready for GitHub-based Streamlit Community Cloud deployment with `streamlit_app.py` as the application file. Public deployment should occur only after local interaction testing and instructor approval.
