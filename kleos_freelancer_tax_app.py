"""
Kleos — Freelancer Hiring & Tax Explorer
=========================================
Pick a country and the monthly amount paid to a freelancer (EUR), and see the
self-employed / sole-entrepreneur options available, the tax & social burden the
freelancer carries under each, their net take-home, and the misclassification rules.

Run locally:
    pip install streamlit pandas
    streamlit run kleos_freelancer_tax_app.py

Figures are 2025-2026, indicative, and checked against current sources.
Tax rates change yearly — confirm with the official authority before client-facing use.
This is operational reference material, not legal or tax advice.
"""

import streamlit as st
import pandas as pd

# --------------------------------------------------------------------------------------
# Page config & light styling
# --------------------------------------------------------------------------------------
st.set_page_config(page_title="Kleos — Freelancer Tax Explorer", page_icon="•", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1250px;}
      .kleos-title {font-size: 2rem; font-weight: 800; color: #1F3A5F; margin-bottom: .1rem;}
      .kleos-sub {color: #5b6b7e; font-size: .95rem; margin-bottom: 1rem;}
      .pill {display:inline-block; padding:2px 10px; border-radius:12px; font-size:.72rem;
             font-weight:700; letter-spacing:.02em;}
      .pill-self {background:#E3F0FB; color:#1F3A5F;}
      .pill-co {background:#FBF1E0; color:#8a5a00;}
      .card {border:1px solid #e3e8ee; border-radius:14px; padding:18px 20px; margin-bottom:14px;
             background:#ffffff;}
      .card-co {background:#FCF7EE;}
      .small {color:#5b6b7e; font-size:.85rem;}
      .auth a {margin-right:14px; font-size:.85rem;}
      .warn {background:#FFF3CD; border:1px solid #ffe08a; border-radius:8px; padding:8px 12px;
             color:#7a5b00; font-size:.85rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="kleos-title">Kleos — Freelancer Hiring &amp; Tax Explorer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="kleos-sub">Pick a country and the monthly amount paid to a freelancer. '
    'See each legal-entity / tax-regime option, the freelancer\'s tax &amp; social burden, '
    'net take-home, limits, and how to avoid misclassification as an employee.</div>',
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def progressive(x, brackets):
    """brackets = list of (lower, upper, rate); returns tax on x."""
    t = 0.0
    for lo, hi, rate in brackets:
        if x > lo:
            t += (min(x, hi) - lo) * rate
    return t


def eur(v):
    return f"€{v:,.0f}"


# Spain IRPF (combined state + avg regional) and RETA cuota -----------------------------
SPAIN_IRPF = [(0, 12450, .19), (12450, 20200, .24), (20200, 35200, .30),
              (35200, 60000, .37), (60000, 300000, .45), (300000, 1e12, .47)]


def spain_irpf(base):
    return max(0.0, progressive(base, SPAIN_IRPF) - progressive(5550, SPAIN_IRPF))


def spain_cuota_month(net_month, tarifa_plana):
    if tarifa_plana:
        return 88.64
    table = [(670, 205), (900, 220), (1166.7, 260), (1300, 291), (1500, 294),
             (1700, 300), (1850, 310), (2030, 315), (2330, 320), (2760, 330),
             (3190, 350), (3620, 370), (4050, 390), (6000, 430), (1e12, 590)]
    for cap, c in table:
        if net_month <= cap:
            return c
    return 590


# Portugal IRS (2026, 9 bands) ----------------------------------------------------------
PT_IRS = [(0, 8342, .125), (8342, 12587, .16), (12587, 17838, .215),
          (17838, 23089, .244), (23089, 29397, .314), (29397, 41952, .349),
          (41952, 44987, .431), (44987, 83696, .446), (83696, 1e12, .48)]


def pt_irs(base):
    t = progressive(base, PT_IRS)
    # solidarity surcharge
    if base > 80000:
        t += (min(base, 250000) - 80000) * 0.025
    if base > 250000:
        t += (base - 250000) * 0.05
    return t


# --------------------------------------------------------------------------------------
# Per-option calculators  ->  return dict(rows=[(label, annual_eur)], net, eff, kind, ...)
# Each takes annual gross EUR paid to the freelancer + params P.
# Assumption: entered amount = the freelancer's gross professional income (negligible expenses).
# --------------------------------------------------------------------------------------
def result(kind, gross, social, tax, notes, limit_note="", warning="", extra=None):
    deduct = social + tax
    net = gross - deduct
    rows = [("Gross paid by company", gross)]
    if extra:
        rows += extra
    rows += [("Social contributions", -social), ("Income / profit tax", -tax),
             ("Net to freelancer", net)]
    return dict(kind=kind, gross=gross, social=social, tax=tax, net=net,
                eff=(deduct / gross * 100 if gross else 0), rows=rows,
                notes=notes, limit_note=limit_note, warning=warning)


# ---- Spain --------------------------------------------------------------------------
def es_autonomo(gross, P, trade=False):
    profit = gross
    net_month = profit / 12
    cuota_m = spain_cuota_month(net_month, P["es_tarifa_plana"])
    social = cuota_m * 12
    tax = spain_irpf(max(0, profit - social))
    note = ("IRPF on profit minus deductible cuota; RETA cuota is income-based "
            f"(~€{cuota_m:,.0f}/mo here). VAT (IVA) 21% is charged on top and passed to the state — "
            "not a cost to the freelancer; exported B2B services are reverse-charge.")
    if trade:
        note = "Same tax as ordinary autónomo. TRADE is a status (≥75% from one client) granting some labour rights. " + note
    return result("self", gross, social, tax, note,
                  limit_note="No turnover cap; cuota regularised at year-end; VAT from the first euro.")


def es_sl(gross, P):
    profit = gross
    corp = 0.15 * min(profit, 50000) * 0 + (0.15 if P["es_new_co"] else 0.25) * profit  # simplified
    # new co: 15% flat first two profitable years; else 25% (23% if micro <1m, approximated as 25)
    corp = (0.15 if P["es_new_co"] else 0.25) * profit
    after = profit - corp
    div_tax = progressive(after, [(0, 6000, .19), (6000, 50000, .21), (50000, 200000, .23),
                                   (200000, 300000, .27), (300000, 1e12, .28)])
    social = 0.0
    tax = corp + div_tax
    return result("company", gross, social, tax,
                  "Indicative: corporate tax on profit, then dividend tax to extract it. "
                  "Ignores any director salary and the autónomo-societario RETA cuota (a real extra cost). "
                  "VAT applies from the first invoice.",
                  limit_note="No turnover cap; full accounting; 15% corporate rate applies only in the first two profitable years of a new company.")


# ---- Portugal -----------------------------------------------------------------------
def pt_simplificado(gross, P):
    taxable = 0.75 * gross
    tax = pt_irs(taxable)
    ss_m = min(max(0.214 * 0.70 * gross / 12, 20), 0.214 * 6445.56)
    social = 0 if P["pt_first_year"] else ss_m * 12
    return result("self", gross, social, tax,
                  "Taxable income = 75% of services revenue (coefficient 0.75); the other 25% is presumed expenses. "
                  "Social Security 21.4% on 70% of income"
                  + (" — waived in the first 12 months." if P["pt_first_year"] else ".")
                  + " IVA 23% above €15k turnover is passed to the state.",
                  limit_note="Regime simplificado cap €200,000/yr; VAT exemption ≤ €15,000; SS max base €6,445.56/mo.")


def pt_organizada(gross, P):
    taxable = gross  # assume negligible documented expenses
    tax = pt_irs(taxable)
    ss_m = min(max(0.214 * 0.70 * gross / 12, 20), 0.214 * 6445.56)
    social = 0 if P["pt_first_year"] else ss_m * 12
    return result("self", gross, social, tax,
                  "Taxed on actual net profit (revenue − documented expenses; here assumed negligible, so higher than "
                  "the simplified regime). Better only when real expenses are high. IVA 23% (no €15k exemption).",
                  limit_note="Mandatory above €200,000/yr; no upper cap.")


def pt_lda(gross, P):
    profit = gross
    corp = 0.15 * min(profit, 50000) + 0.19 * max(0, profit - 50000)
    after = profit - corp
    div_tax = 0.28 * after
    return result("company", gross, 0.0, corp + div_tax,
                  "Indicative: IRC 19% (15% on the first €50k for SMEs), then 28% on dividends extracted. "
                  "Ignores municipal derrama (≤1.5%) and any salary. Robustly B2B.",
                  limit_note="No turnover cap; full accounting; IVA from registration.")


# ---- Georgia ------------------------------------------------------------------------
def ge_sbs(gross, P):
    fx = P["fx"]["Georgia"]; rev = gross * fx
    tax_local = 0.01 * min(rev, 500000) + 0.03 * max(0, rev - 500000)
    tax = tax_local / fx
    warn = ""
    if rev > 500000:
        warn = "Turnover exceeds GEL 500,000 — the excess is taxed at 3% and SBS is lost if exceeded two years running."
    return result("self", gross, 0.0, tax,
                  "1% of gross turnover (3% above GEL 500,000). No personal social contributions for a solo IE. "
                  "VAT 18% only above GEL 100,000/12m (foreign-client services excluded).",
                  limit_note="1% up to GEL 500,000/yr; 3% above.", warning=warn)


def ge_micro(gross, P):
    fx = P["fx"]["Georgia"]; rev = gross * fx
    warn = ""
    if rev > 30000:
        warn = "Turnover exceeds GEL 30,000 — Micro Business Status does not apply at this income; use SBS (1%) instead."
    return result("self", gross, 0.0, 0.0,
                  "0% on business turnover. No personal social contributions.",
                  limit_note="Turnover < GEL 30,000/yr; no employees allowed.", warning=warn)


def ge_general(gross, P):
    return result("self", gross, 0.0, 0.20 * gross,
                  "20% income tax on net profit. This is the compliant home for consulting (excluded from SBS/Micro). "
                  "VAT 18% above GEL 100,000/12m (foreign B2B excluded).",
                  limit_note="No turnover cap.")


def ge_vz(gross, P):
    return result("company", gross, 0.0, 0.05 * gross,
                  "Virtual Zone LLC: 0% corporate tax on profit from IT services supplied abroad; 5% on dividends "
                  "distributed (shown here assuming full distribution). 0% VAT on those exports. IT activity only.",
                  limit_note="No turnover cap; IT services delivered to clients abroad; needs genuine operations.")


# ---- Serbia -------------------------------------------------------------------------
def rs_pausal(gross, P):
    fx = P["fx"]["Serbia"]; rev = gross * fx
    annual_local = P["rs_pausal_month"] * 12
    tax = annual_local / fx
    warn = ""
    if rev > 6000000:
        warn = "Turnover exceeds RSD 6,000,000 — the lump-sum (paušal) regime no longer applies; switch to books."
    return result("self", gross, 0.0, tax,
                  f"Paušal = a FIXED monthly obligation (tax + all social contributions), set by the Tax Administration "
                  f"by formula (activity, municipality, age). Editable in the sidebar — default RSD {P['rs_pausal_month']:,.0f}/mo. "
                  "Because it is fixed, the effective rate falls as income rises.",
                  limit_note="Annual income cap RSD 6,000,000; cannot be a VAT payer.", warning=warn)


def rs_books(gross, P):
    profit = gross
    tax = 0.10 * profit
    social = P["rs_books_social"] * profit
    return result("self", gross, social, tax,
                  f"Indicative: 10% income tax on net profit + social contributions (pension/health/unemployment). "
                  f"Real contributions are set on a chosen base with statutory min/max, so this uses an editable rate "
                  f"({P['rs_books_social']*100:.0f}% of profit). VAT 20% above RSD 8m.",
                  limit_note="No income cap; VAT registration at RSD 8m/12m.")


def rs_doo(gross, P):
    profit = gross
    corp = 0.15 * profit
    div = 0.15 * (profit - corp)
    return result("company", gross, 0.0, corp + div,
                  "Indicative: 15% corporate tax + 15% withholding on dividends extracted. Ignores the owner-director's "
                  "mandatory insurance (salary or founder contributions). Robustly B2B.",
                  limit_note="No income cap; full bookkeeping + VAT at RSD 8m.")


# ---- Kazakhstan ---------------------------------------------------------------------
MCI = 4325  # 2026


def kz_selfemp(gross, P):
    fx = P["fx"]["Kazakhstan"]; rev = gross * fx
    social = 0.04 * gross
    warn = ""
    if rev / 12 > 300 * MCI:
        warn = (f"Monthly income exceeds 300 MCI (~KZT {300*MCI:,.0f} ≈ €{300*MCI/fx:,.0f}) — "
                "above the self-employed STR cap; use the simplified-declaration IE instead.")
    return result("self", gross, social, 0.0,
                  "Self-employed STR: 0% individual income tax + ~4% social payments (≈1% each: pension, social, "
                  "health, employer-pension). App-based (e-Salyq Business), no filing.",
                  limit_note=f"Income ≤ 300 MCI/month (~KZT {300*MCI:,.0f}). Cannot register for VAT.", warning=warn)


def kz_simplified(gross, P):
    tax = 0.04 * gross
    social = P["kz_social"] * gross
    return result("self", gross, social, tax,
                  f"Simplified declaration: 4% of income, not a VAT payer, pays own monthly pension/social/health "
                  f"(editable, ~{P['kz_social']*100:.0f}% here). NOTE: a Kazakh payer can't deduct these payments for "
                  "corporate tax from 2026 — but a FOREIGN payer like Kleos is unaffected.",
                  limit_note="Annual cap 600,000 MCI from 2026; VAT at 10,000 MCI.")


def kz_general(gross, P):
    tax = 0.10 * (gross * 0.70)  # 10% after up to 30% deduction
    social = P["kz_social"] * gross
    return result("self", gross, social, tax,
                  f"General regime: 10% income tax on income after up to 30% deduction + pension/social/health "
                  f"(editable, ~{P['kz_social']*100:.0f}%). Payments remain CIT-deductible for local payers.",
                  limit_note="No simplified cap; VAT registration at 10,000 MCI (~KZT 40m).")


def kz_llp(gross, P):
    profit = gross
    corp = 0.20 * profit
    div = 0.05 * (profit - corp)
    return result("company", gross, 0.0, corp + div,
                  "Indicative: 20% corporate income tax + 5% on dividends extracted (dividends may be exempt if shares "
                  "held >3 years). VAT 12% if registered. Robustly B2B.",
                  limit_note="No turnover cap; full accounting; VAT at 10,000 MCI.")


# --------------------------------------------------------------------------------------
# Country registry
# --------------------------------------------------------------------------------------
def opt(name, fn, misclass):
    return dict(name=name, fn=fn, misclass=misclass)


COUNTRIES = {
    "Georgia": dict(
        rank="#1 by volume", currency="GEL",
        authorities=[("Revenue Service", "https://rs.ge"),
                     ("Public Registry", "https://napr.gov.ge"),
                     ("Work permits (from Mar 2026)", "https://labourmigration.moh.gov.ge")],
        options=[
            opt("Individual Entrepreneur + Small Business Status (1%)", ge_sbs,
                "Substance-over-form (Tax Code Art. 73): a 'freelance' deal that is really employment can be "
                "reclassified → 20% + penalties, up to 3 years back. Consulting is excluded from SBS. "
                "Mitigate: multiple clients, deliverable contracts, own tools, no exclusivity."),
            opt("Individual Entrepreneur + Micro Business Status (0%)", ge_micro,
                "Same substance-over-form risk; consulting also excluded from Micro. Single-client dependence can "
                "still be reclassified to 20% employment."),
            opt("Individual Entrepreneur — general (20% on profit)", ge_general,
                "The compliant home for consulting and high-expense work. Substance-over-form reclassification still "
                "applies; keep multi-client, deliverable contracts, own tools."),
            opt("LLC — Virtual Zone / International Company (IT)", ge_vz,
                "A company makes the engagement B2B — the strongest defence — but a sham one-person LLC under "
                "employee-like control can be looked through, and Virtual Zone needs genuine IT operations."),
        ],
    ),
    "Serbia": dict(
        rank="#2 by volume", currency="RSD",
        authorities=[("Tax Administration (ePorezi)", "https://purs.gov.rs"),
                     ("Business Registers Agency", "https://apr.gov.rs"),
                     ("Independence-test tool", "https://testsamostalnosti.rs")],
        options=[
            opt("Preduzetnik — paušal (lump-sum)", rs_pausal,
                "9-criterion Independence Test (Art. 85): meeting 5+ for one principal = 'dependent' (foreign "
                "principals included; the Serbian entrepreneur bears the back-tax). Criteria include >130 days/yr for "
                "one client, ≥70% income from one client, client's hours/premises/equipment, non-compete. "
                "Mitigate: diversify clients, own kit & space, deliverable contracts, carry risk, no exclusivity."),
            opt("Preduzetnik — self-taxation (books)", rs_books,
                "Same 9-criterion independence test applies. Mitigate: multiple clients, own equipment/workspace, "
                "deliverable contracts, carry real risk, no exclusivity."),
            opt("d.o.o. (LLC)", rs_doo,
                "A d.o.o. makes the relationship B2B — the strongest defence — but the independence test can still "
                "look through a one-person company that behaves like employment."),
        ],
    ),
    "Spain": dict(
        rank="#3 by volume", currency="EUR",
        authorities=[("Agencia Tributaria", "https://agenciatributaria.gob.es"),
                     ("Seguridad Social (RETA)", "https://seg-social.es")],
        options=[
            opt("Autónomo (ordinary self-employed)", es_autonomo,
                "'Falso autónomo': if it's really employment (fixed hours, employer's tools/premises, integration, no "
                "own risk, exclusivity), Inspección de Trabajo reclassifies → the engaging company owes back Social "
                "Security + fines. Mitigate: multiple clients, own tools/schedule, deliverable contracts, no exclusivity."),
            opt("Autónomo TRADE (economically dependent, ≥75% one client)",
                lambda g, P: es_autonomo(g, P, trade=True),
                "TRADE formalises heavy single-client dependence and grants some protections, but is NOT a shield "
                "against 'falso autónomo' — if control/integration look like employment it can be reclassified to full "
                "employment. Keep autonomy over HOW the work is done."),
            opt("Sociedad Limitada (SL) — company", es_sl,
                "An SL with real activity is robustly B2B. But a one-person SL invoicing a single client under "
                "employee-like control can be challenged — keep genuine substance and autonomy."),
        ],
    ),
    "Kazakhstan": dict(
        rank="#4 by volume", currency="KZT",
        authorities=[("State Revenue Committee", "https://kgd.gov.kz"),
                     ("e-Government", "https://egov.kz"),
                     ("e-Salyq Business", "https://kgd.gov.kz")],
        options=[
            opt("Self-employed STR (0% tax + ~4% social)", kz_selfemp,
                "No formal test; the Labour Code can reclassify a services contract that is really employment. "
                "A FOREIGN payer is not hit by the 2026 CIT-deductibility change. Mitigate: deliverable contracts, "
                "multiple clients, own tools."),
            opt("Individual Entrepreneur — simplified declaration (4%)", kz_simplified,
                "2026 trap for LOCAL payers: a Kazakh company's payments to a simplified-IE are not corporate-tax "
                "deductible — a foreign payer is unaffected. Still avoid employee-like control / PE."),
            opt("Individual Entrepreneur — general regime (10%)", kz_general,
                "Same Labour-Code reclassification risk; payments remain CIT-deductible for local payers. "
                "Mitigate with genuine independence."),
            opt("LLP / TOO — company", kz_llp,
                "B2B via your own LLP is the strongest defence; a sham one-person LLP under employee-like control can "
                "still be looked through."),
        ],
    ),
    "Portugal": dict(
        rank="#5 by volume", currency="EUR",
        authorities=[("Autoridade Tributária — Portal das Finanças", "https://portaldasfinancas.gov.pt"),
                     ("Segurança Social", "https://seg-social.pt")],
        options=[
            opt("Trabalhador independente — regime simplificado", pt_simplificado,
                "Presumption of employment (Código do Trabalho art. 12) if indicators met (client's premises/equipment, "
                "client-set schedule, fixed regular pay, subordination). Mitigate: multiple clients, own tools/space, "
                "deliverable contracts, no client-set schedule."),
            opt("Trabalhador independente — contabilidade organizada", pt_organizada,
                "Same art. 12 presumption, plus the 'entidade contratante' levy (7%/10%) where a PT entity takes >50% "
                "of your income (foreign clients without PT presence generally outside it)."),
            opt("Sociedade Unipessoal (Lda) — company", pt_lda,
                "An Lda is robustly B2B; but a one-person company serving a single client under employee-like control "
                "can be challenged, and the entidade-contratante rules look at single-client dependence."),
        ],
    ),
}

# --------------------------------------------------------------------------------------
# Sidebar controls
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.header("Inputs")
    country = st.selectbox("Country", list(COUNTRIES.keys()))
    monthly_eur = st.number_input("Monthly amount paid to freelancer (EUR)",
                                  min_value=100, max_value=100000, value=3000, step=100)
    annual_eur = monthly_eur * 12
    st.caption(f"= €{annual_eur:,.0f} per year")

    st.divider()
    with st.expander("Assumptions (editable)", expanded=False):
        st.caption("FX — local currency per €1 (approximate, June 2026):")
        fx = {
            "Georgia": st.number_input("GEL per EUR", value=3.05, step=0.05, format="%.2f"),
            "Serbia": st.number_input("RSD per EUR", value=117.2, step=0.5, format="%.1f"),
            "Kazakhstan": st.number_input("KZT per EUR", value=565.0, step=5.0, format="%.0f"),
        }
        st.caption("Country toggles & rates:")
        es_tarifa_plana = st.checkbox("Spain — first-year tarifa plana (€88.64/mo cuota)", value=False)
        es_new_co = st.checkbox("Spain — SL is a new company (15% IS, first 2 profitable yrs)", value=True)
        pt_first_year = st.checkbox("Portugal — first 12 months (Social Security exempt)", value=False)
        rs_pausal_month = st.number_input("Serbia — paušal monthly obligation (RSD)", value=55000, step=1000)
        rs_books_social = st.slider("Serbia — books: social as % of profit", 0.10, 0.40, 0.20, 0.01)
        kz_social = st.slider("Kazakhstan — IE social as % of income", 0.05, 0.20, 0.12, 0.01)

P = dict(fx=fx, es_tarifa_plana=es_tarifa_plana, es_new_co=es_new_co,
         pt_first_year=pt_first_year, rs_pausal_month=rs_pausal_month,
         rs_books_social=rs_books_social, kz_social=kz_social)

# --------------------------------------------------------------------------------------
# Header for selected country
# --------------------------------------------------------------------------------------
C = COUNTRIES[country]
left, right = st.columns([3, 2])
with left:
    st.subheader(f"{country}  ·  {C['rank']}  ·  local currency {C['currency']}")
    links = "  ".join(f'<a href="{u}" target="_blank">{n}</a>' for n, u in C["authorities"])
    st.markdown(f'<div class="auth small">Official authorities &nbsp; {links}</div>', unsafe_allow_html=True)
with right:
    st.markdown(
        '<div class="small">The amount entered is what the company <b>pays</b> the freelancer. '
        'As a contractor the company\'s cost is just this invoice — there are <b>no employer social charges</b> '
        '(the contractor advantage). The figures below are the <b>freelancer\'s</b> own tax &amp; social burden.</div>',
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------------------
# Compute all options
# --------------------------------------------------------------------------------------
computed = []
for o in C["options"]:
    r = o["fn"](annual_eur, P)
    r["name"] = o["name"]
    r["misclass"] = o["misclass"]
    computed.append(r)

# --------------------------------------------------------------------------------------
# Comparison summary
# --------------------------------------------------------------------------------------
st.markdown("### Compare options")
df = pd.DataFrame([{
    "Option": r["name"],
    "Type": "Company" if r["kind"] == "company" else "Self-employed",
    "Tax + social (€/yr)": round(r["tax"] + r["social"]),
    "Net to freelancer (€/yr)": round(r["net"]),
    "Net (€/mo)": round(r["net"] / 12),
    "Effective rate": r["eff"] / 100,
} for r in computed])

c1, c2 = st.columns([3, 2])
with c1:
    st.dataframe(
        df.style.format({"Tax + social (€/yr)": "€{:,.0f}", "Net to freelancer (€/yr)": "€{:,.0f}",
                         "Net (€/mo)": "€{:,.0f}", "Effective rate": "{:.1%}"})
                 .background_gradient(subset=["Net to freelancer (€/yr)"], cmap="Greens"),
        use_container_width=True, hide_index=True,
    )
with c2:
    st.caption("Net take-home to the freelancer (€/yr)")
    st.bar_chart(df.set_index("Option")["Net to freelancer (€/yr)"], height=260)

best = df.loc[df["Net to freelancer (€/yr)"].idxmax(), "Option"]
st.success(f"Most tax-efficient at €{monthly_eur:,.0f}/mo: **{best}** "
           f"(net €{df['Net to freelancer (€/yr)'].max():,.0f}/yr). Verify against the specific contractor's situation.")

# --------------------------------------------------------------------------------------
# Detail cards
# --------------------------------------------------------------------------------------
st.markdown("### Option details")
for r in computed:
    co = r["kind"] == "company"
    pill = '<span class="pill pill-co">COMPANY</span>' if co else '<span class="pill pill-self">SELF-EMPLOYED</span>'
    st.markdown(f'<div class="card {"card-co" if co else ""}">', unsafe_allow_html=True)
    st.markdown(f"**{r['name']}** &nbsp; {pill}", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net to freelancer", eur(r["net"]), f"{eur(r['net']/12)}/mo")
    m2.metric("Income / profit tax", eur(r["tax"]))
    m3.metric("Social contributions", eur(r["social"]))
    m4.metric("Effective rate", f"{r['eff']:.1f}%")

    if r["warning"]:
        st.markdown(f'<div class="warn">⚠ {r["warning"]}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="small" style="margin-top:8px;">{r["notes"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small"><b>Limits:</b> {r["limit_note"]}</div>', unsafe_allow_html=True)

    with st.expander("Breakdown & misclassification"):
        bd = pd.DataFrame(r["rows"], columns=["Item", "€ / yr"])
        st.dataframe(bd.style.format({"€ / yr": "€{:,.0f}"}), use_container_width=True, hide_index=True)
        st.markdown(f'**Avoiding misclassification:** {r["misclass"]}')
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------------------
st.divider()
st.caption(
    "Figures are 2025–2026 and indicative. Self-employment is taxed on turnover or profit per the country's rules; "
    "assumptions (negligible expenses, full dividend distribution for company forms, editable FX & social rates) are "
    "shown in the sidebar and in each note. Tax rates change yearly — confirm with the official authority before "
    "client-facing use. Operational reference only, not legal or tax advice."
)
