# Kleos — Freelancer Hiring & Tax Explorer

A Streamlit app: pick a country and the monthly amount paid to a freelancer (EUR, default €3,000),
and see every self-employed / sole-entrepreneur (and company) option, the freelancer's tax & social
burden under each, their net take-home, volume limits, and how to avoid misclassification as an employee.

Covers the top 5 Kleos volume corridors with a working tax engine: **Georgia, Serbia, Spain, Kazakhstan, Portugal.**

## Run
```bash
pip install -r requirements.txt
streamlit run kleos_freelancer_tax_app.py
```

## What it does
- Country selector + monthly EUR input (annual derived automatically).
- One card per legal-entity / tax-regime option (self-employed routes and the incorporated alternative).
- Per option: income/profit tax, social contributions, **net take-home**, effective rate, breakdown table, limits, misclassification guidance, and a warning when an income cap is exceeded.
- A comparison table + bar chart, and the most tax-efficient option highlighted.
- Sidebar "Assumptions": editable FX rates, Spain tarifa-plana / new-company toggles, Portugal first-year SS exemption, Serbia paušal monthly amount & books social rate, Kazakhstan IE social rate.

## Notes
- The amount entered is what the **company pays**. As a contractor the company's cost is just the invoice — no employer social charges. The figures are the **freelancer's** own burden.
- Assumes negligible business expenses; company forms assume full dividend distribution and ignore director salary/derrama (clearly labelled).
- 2025–2026 figures, indicative. Confirm with the official authority before client-facing use. Not legal or tax advice.
