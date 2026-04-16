# Contributing to Freelancer Radar

Thanks for your interest in contributing! Here's how to get started.

## Setup

```bash
git clone https://github.com/jaydeeprusia/freelancer-radar.git
cd freelancer-radar
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

| File | Responsibility |
|---|---|
| `app.py` | All Streamlit UI — fetch, filters, scoring config, table, detail view |
| `fetcher.py` | Freelancer API calls + daily file cache |
| `utils.py` | Raw JSON → normalised DataFrame (all field extraction) |
| `scoring.py` | 7 component scorers, weighted master score, insights generator |
| `filters.py` | DataFrame filtering logic |

## Guidelines

- Keep each file focused on its single responsibility
- No hardcoded credentials or tokens anywhere
- All new scoring factors should be added to `DEFAULT_WEIGHTS` in `scoring.py` and wired into the UI in `app.py`
- Cache files (`cache/`) and preset JSONs should not be committed

## Submitting a PR

1. Fork the repo and create a branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Open a pull request with a clear description of what changed and why

## Ideas for Contributions

- [ ] Streamlit Cloud deployment support
- [ ] Email/Telegram alerts for high-score projects
- [ ] Historical score tracking across sessions
- [ ] More scoring factors (e.g. client timezone, project type)
- [ ] Dark/light theme toggle
