# Closing Time

Closing Time is a Chapter 6 Streamlit learning activity for introductory accounting. Students complete the May close for a fictional service business by deciding when revenue and expense belong, classifying adjustment evidence, calculating account increases or decreases and ending balances, preparing linked financial-statement totals, and evaluating reporting-integrity choices.

The activity deliberately avoids journal mechanics. Student work is framed through recognition timing, account direction, ending account balances, and financial-statement effects.

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

The app requires no login, database, or student name. It stores only compact answer selections, numeric responses, stage position, and scoring flags in a validated URL parameter so browser refreshes can restore progress. No written response or identifying information is included.

## Deployment

The repository is ready for GitHub-based Streamlit Community Cloud deployment with `streamlit_app.py` as the application file. Public deployment should occur only after local interaction testing and instructor approval.

