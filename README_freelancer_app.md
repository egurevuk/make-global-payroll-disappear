# Kleos — Freelancer Tax Explorer

Pick a country and the monthly amount paid to a freelancer (EUR, default €3,000), and see every
self-employed / sole-entrepreneur (and company) option, the freelancer's tax & social burden,
net take-home, volume limits, and how to avoid misclassification as an employee.

Covers the top 5 Kleos volume corridors with a working tax engine: **Georgia, Serbia, Spain, Kazakhstan, Portugal.**
Styled to match **kleos.io** (green primary, cream background, dark-navy ink, Space Grotesk headings).

## Files
```
kleos_freelancer_tax_app.py     # the app
requirements.txt                # streamlit, pandas
.streamlit/config.toml          # Kleos brand theme (green/cream) — keep this path!
```
Put `config.toml` inside a folder named `.streamlit` at the repo root, so the path is
`.streamlit/config.toml`. Streamlit Cloud reads it automatically.

## Run
```bash
pip install -r requirements.txt
streamlit run kleos_freelancer_tax_app.py
```

## Notes
- The amount entered is what the **company pays**. As a contractor the company's cost is just the invoice — no employer social charges. The figures are the **freelancer's** own burden.
- Assumes negligible business expenses; company forms assume full dividend distribution and ignore director salary/derrama (clearly labelled).
- Sidebar "Assumptions" exposes editable FX rates and country toggles.
- 2025–2026 figures, indicative. Confirm with the official authority before client-facing use. Not legal or tax advice.
