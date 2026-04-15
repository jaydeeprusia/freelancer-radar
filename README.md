
# 🚀 Freelancer Alpha Dashboard

A powerful Streamlit dashboard to **find, score, and analyze Freelancer.com projects** before anyone else bids — giving you a real competitive edge.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)
![Stars](https://img.shields.io/github/stars/yourusername/freelancer-alpha-dashboard?style=social)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Live API Fetch** | Fetch active projects directly from Freelancer.com API with country, language, and budget filters |
| 🧠 **Smart Scoring** | 7-factor weighted scoring: skill match, budget, competition, client quality, urgency, freshness, complexity |
| ⚙️ **Dynamic Scoring Config** | Adjust weights with sliders, toggle factors on/off, save/load presets |
| 📊 **Interactive Table** | Click any row to instantly load project details |
| 🔎 **Advanced Filters** | Filter by budget (USD-normalised), bids, hours posted, client country, verified status, flags, skill count |
| 💡 **AI-Style Insights** | Per-project "Why this is good" and "Risk factors" analysis |
| 💾 **Daily Cache** | Avoid redundant API calls with automatic daily caching |

---

## 📸 Screenshots

> _Add screenshots here after first run_

---

## 🛠️ Installation

```bash
git clone https://github.com/yourusername/freelancer-alpha-dashboard.git
cd freelancer-alpha-dashboard
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔑 Getting Your Freelancer Auth Token

1. Log in to [freelancer.com](https://www.freelancer.com)
2. Open DevTools → Network tab
3. Make any API request (e.g. browse projects)
4. Find a request to `api/projects` and copy the `freelancer-auth-v2` header value

> ⚠️ Never commit your token. Use the password input in the UI — it is never stored.

---

## ⚙️ Scoring System

Each project is scored across 7 factors (0–100 each), combined as a weighted sum:

| Factor | Default Weight | What it measures |
|---|---|---|
| 🎯 Skill Match | 25% | How many of your keywords appear in project skills |
| 💰 Budget | 20% | USD-normalised average budget |
| ⚔️ Competition | 15% | Inverse of bid count |
| 👤 Client Quality | 15% | Verification + reputation + account age |
| 🔥 Urgency | 10% | Urgent / featured / premium flags |
| 🕐 Freshness | 10% | Hours since posted |
| 🧠 Complexity | 5% | Description length + technical keywords |

All weights are **auto-normalised** and fully adjustable via the UI. Presets can be saved and loaded as JSON.

**Decision thresholds:**
- `BID` → score ≥ 65
- `CONSIDER` → score ≥ 40
- `SKIP` → score < 40

---

## 📁 Project Structure

```
├── app.py          # Streamlit UI
├── fetcher.py      # Freelancer API client + caching
├── utils.py        # Data normalisation (extracts all JSON fields)
├── scoring.py      # 7-factor scoring engine + insights
├── filters.py      # Advanced filtering logic
├── requirements.txt
└── cache/          # Auto-generated daily cache (gitignored)
```

---

## 🧩 Advanced Usage

### Saving a Scoring Preset

1. Open **⚙️ Scoring Configuration**
2. Adjust sliders and toggles
3. Enter a preset name and click **💾 Save Preset**
4. A `.json` file is saved locally

### Loading a Preset

1. Click **📂 Load Preset** and upload your `.json` file
2. Click **📂 Apply Preset** — sliders update instantly

### Uploading a JSON File

Instead of fetching live, you can upload a raw Freelancer API JSON response directly via the file uploader.

---

## 🔒 Security

- Auth token is entered via a `type="password"` field and **never stored or logged**
- No credentials are hardcoded anywhere
- Cache files contain only project data (no tokens)
- Add `*.json` to `.gitignore` if you want to exclude cache from commits

---

## 📦 Key Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | UI framework |
| `pandas` | Data manipulation |
| `requests` | API calls |
| `forex-python` | Currency conversion |
| `pycountry` | ISO country/language data |

---

## 🤝 Contributing

Pull requests are welcome! For major changes, open an issue first.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push and open a PR

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## ⭐ Star History

If this tool saves you time finding freelance projects, please consider starring the repo!

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/freelancer-alpha-dashboard&type=Date)](https://star-history.com/#yourusername/freelancer-alpha-dashboard)
