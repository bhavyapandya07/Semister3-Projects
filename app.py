# =============================================================================
# FILE: app.py
# PURPOSE: Streamlit UI - Clinical Intelligence Dashboard for
#          Probabilistic Diabetes Risk Assessment (Pima Indians Dataset).
# =============================================================================

import time
import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import torch

from database import load_pima_data_into_db, get_clinical_data_as_dataframe, get_feature_array
from model import ProbabilisticDiagnosticNN, train_model
from inference import predict_with_uncertainty, classify_risk_tier, prepare_input_tensor, UNCERTAINTY_THRESHOLD


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="DiabRisk · Clinical Assessment",
    page_icon="⚕",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# GLOBAL CSS — Clinical Intelligence Dashboard
# Palette: Off-white background, Slate sidebar, Teal accent, Amber highlight
# Fonts: Sora (headings) + DM Sans (body)
# =============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap');

/* ── Root tokens ─────────────────────────────────────────── */
:root {
  --bg:          #f7f6f3;
  --surface:     #ffffff;
  --sidebar-bg:  #1c2535;
  --sidebar-txt: #c8d0de;
  --teal:        #0d7377;
  --teal-light:  #14a085;
  --teal-pale:   #e6f5f4;
  --amber:       #d97706;
  --amber-pale:  #fef3c7;
  --red:         #c0392b;
  --red-pale:    #fde8e4;
  --slate-600:   #475569;
  --slate-400:   #94a3b8;
  --slate-200:   #e2e8f0;
  --slate-100:   #f1f5f9;
  --text-h:      #1a202c;
  --text-b:      #374151;
  --border:      #dde3ec;
  --radius-lg:   14px;
  --radius-md:   10px;
  --radius-sm:   7px;
  --shadow-sm:   0 1px 4px rgba(0,0,0,.07), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md:   0 4px 16px rgba(0,0,0,.09), 0 1px 4px rgba(0,0,0,.05);
}

/* ── Base ────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {
  font-family: 'DM Sans', system-ui, sans-serif;
  background-color: var(--bg) !important;
  color: var(--text-b);
}

/* ── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: var(--sidebar-bg) !important;
  border-right: none !important;
}
section[data-testid="stSidebar"] * {
  color: var(--sidebar-txt) !important;
}
section[data-testid="stSidebar"] .stNumberInput input {
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.13) !important;
  color: #e8edf4 !important;
  border-radius: var(--radius-sm) !important;
  font-family: 'DM Sans', sans-serif !important;
}
section[data-testid="stSidebar"] label {
  color: #9baec2 !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  letter-spacing: .03em !important;
  text-transform: uppercase !important;
}
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] .stCaption {
  color: #6b7e99 !important;
  font-size: 0.74rem !important;
}
section[data-testid="stSidebar"] hr {
  border-color: rgba(255,255,255,.08) !important;
}

/* ── Main area scrollbar ──────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c4cdd8; border-radius: 99px; }

/* ── Streamlit chrome overrides ──────────────────────────── */
.stApp > header { background: transparent !important; }
.block-container { padding-top: 1.8rem !important; padding-bottom: 3rem !important; }
div[data-testid="stDecoration"] { display: none; }

/* ── Dataframe ───────────────────────────────────────────── */
.stDataFrame { border-radius: var(--radius-md); overflow: hidden; border: 1px solid var(--border); }

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
  background: var(--teal) !important;
  color: #fff !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  padding: 0.72rem 1.8rem !important;
  font-family: 'Sora', sans-serif !important;
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  letter-spacing: .02em !important;
  width: 100% !important;
  transition: background .2s ease, box-shadow .2s ease !important;
  box-shadow: 0 2px 8px rgba(13,115,119,.35) !important;
}
.stButton > button:hover {
  background: var(--teal-light) !important;
  box-shadow: 0 4px 16px rgba(13,115,119,.45) !important;
}

/* ── Spinner text ────────────────────────────────────────── */
.stSpinner > div { border-top-color: var(--teal) !important; }

/* ── Expander ────────────────────────────────────────────── */
details summary {
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  color: var(--teal) !important;
}

/* ── ─────── CUSTOM COMPONENTS ─────── ──────────────────── */

/* Wordmark / logo */
.logo-wrap {
  display: flex; align-items: center; gap: 10px;
  padding: 1.4rem 0 1rem 0;
}
.logo-icon {
  width: 36px; height: 36px; border-radius: 9px;
  background: linear-gradient(135deg, #0d7377 0%, #14a085 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; flex-shrink: 0;
}
.logo-name {
  font-family: 'Sora', sans-serif;
  font-size: 1.2rem; font-weight: 700;
  color: #dce6f0 !important;
  letter-spacing: -.01em;
}
.logo-tag {
  font-size: 0.65rem; font-weight: 500;
  color: #5c7a99 !important;
  text-transform: uppercase; letter-spacing: .07em;
  margin-top: -2px;
}

/* Sidebar section label */
.sb-section {
  font-family: 'Sora', sans-serif;
  font-size: 0.62rem; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase;
  color: #4e6580 !important;
  padding: 1.1rem 0 0.45rem 0;
  border-top: 1px solid rgba(255,255,255,.06);
  margin-top: 0.5rem;
}
.sb-section:first-of-type { border-top: none; margin-top: 0; }

/* Page header */
.page-header {
  margin-bottom: 1.6rem;
}
.page-eyebrow {
  font-size: 0.72rem; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: var(--teal);
  margin-bottom: 4px;
}
.page-title {
  font-family: 'Sora', sans-serif;
  font-size: 1.9rem; font-weight: 700;
  color: var(--text-h); line-height: 1.2;
  letter-spacing: -.02em;
}
.page-desc {
  font-size: 0.88rem; color: var(--slate-600);
  margin-top: 6px; line-height: 1.55;
}

/* Divider */
.divider {
  height: 1px; background: var(--border);
  margin: 1.4rem 0;
}

/* Card base */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.4rem 1.5rem;
  box-shadow: var(--shadow-sm);
}
.card-title {
  font-family: 'Sora', sans-serif;
  font-size: 0.82rem; font-weight: 700;
  letter-spacing: .05em; text-transform: uppercase;
  color: var(--slate-400);
  margin-bottom: 0.9rem;
}

/* KPI metric tiles */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 1.4rem;
}
.kpi-tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.2rem 1.4rem;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}
.kpi-tile::before {
  content: '';
  position: absolute; top: 0; left: 0;
  width: 4px; height: 100%;
  background: var(--teal);
  border-radius: 2px 0 0 2px;
}
.kpi-tile.amber::before { background: var(--amber); }
.kpi-tile.slate::before { background: var(--slate-400); }
.kpi-label {
  font-size: 0.7rem; font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase;
  color: var(--slate-400); margin-bottom: 6px;
}
.kpi-value {
  font-family: 'Sora', sans-serif;
  font-size: 2rem; font-weight: 700;
  color: var(--text-h); line-height: 1.1;
}
.kpi-sub {
  font-size: 0.73rem; color: var(--slate-400);
  margin-top: 4px;
}

/* Risk gauge bar */
.gauge-wrap { margin: 0.3rem 0 1.1rem 0; }
.gauge-label {
  display: flex; justify-content: space-between;
  font-size: 0.73rem; color: var(--slate-400);
  margin-bottom: 5px;
}
.gauge-track {
  height: 10px; border-radius: 99px;
  background: var(--slate-200);
  overflow: hidden;
}
.gauge-fill {
  height: 100%; border-radius: 99px;
  transition: width 1s cubic-bezier(.4,0,.2,1);
}
.gauge-fill.low    { background: linear-gradient(90deg, #059669, #10b981); }
.gauge-fill.medium { background: linear-gradient(90deg, #d97706, #f59e0b); }
.gauge-fill.high   { background: linear-gradient(90deg, #dc2626, #ef4444); }

/* Clinical verdict banner */
.verdict {
  border-radius: var(--radius-lg);
  padding: 1.3rem 1.5rem;
  margin-bottom: 1.4rem;
  display: flex; gap: 14px; align-items: flex-start;
}
.verdict.positive {
  background: var(--red-pale);
  border: 1px solid #f5c6c2;
}
.verdict.negative {
  background: var(--teal-pale);
  border: 1px solid #b2dfdb;
}
.verdict.uncertain {
  background: var(--amber-pale);
  border: 1px solid #fde68a;
}
.verdict-icon {
  font-size: 1.6rem; flex-shrink: 0; margin-top: 2px;
}
.verdict-title {
  font-family: 'Sora', sans-serif;
  font-size: 1rem; font-weight: 700;
  color: var(--text-h); margin-bottom: 4px;
}
.verdict-body {
  font-size: 0.84rem; color: var(--slate-600);
  line-height: 1.6;
}
.verdict-badge {
  display: inline-block;
  font-size: 0.7rem; font-weight: 700;
  letter-spacing: .06em; text-transform: uppercase;
  border-radius: 99px; padding: 2px 10px;
  margin-top: 8px;
}
.verdict.positive .verdict-badge {
  background: #f5c6c2; color: var(--red);
}
.verdict.negative .verdict-badge {
  background: #b2dfdb; color: var(--teal);
}
.verdict.uncertain .verdict-badge {
  background: #fde68a; color: var(--amber);
}

/* How-it-works steps */
.step-list { display: flex; flex-direction: column; gap: 12px; }
.step-item {
  display: flex; gap: 12px; align-items: flex-start;
}
.step-num {
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--teal-pale);
  border: 1.5px solid #b2dfdb;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Sora', sans-serif;
  font-size: 0.72rem; font-weight: 700;
  color: var(--teal); flex-shrink: 0; margin-top: 1px;
}
.step-body { font-size: 0.84rem; line-height: 1.55; color: var(--slate-600); }
.step-body strong { color: var(--text-b); font-weight: 600; }

/* Dataset info chip */
.info-chip {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 99px; padding: 4px 12px;
  font-size: 0.72rem; font-weight: 500; color: var(--slate-600);
}
.info-chip span { color: var(--teal); font-weight: 700; }

/* Footer */
.footer {
  text-align: center;
  font-size: 0.76rem; color: var(--slate-400);
  padding: 2rem 0 1rem 0;
  line-height: 1.8;
}
.footer a { color: var(--teal); text-decoration: none; }
.footer-warn {
  display: inline-block;
  background: var(--amber-pale);
  border: 1px solid #fde68a;
  color: #92400e;
  border-radius: var(--radius-sm);
  padding: 4px 14px;
  font-size: 0.72rem; font-weight: 500;
  margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SYSTEM INITIALIZATION
# =============================================================================

@st.cache_resource
def initialize_system():
    load_pima_data_into_db()
    model = ProbabilisticDiagnosticNN(input_dim=8)
    X_raw, y = get_feature_array()
    model, scaler = train_model(model, X_raw, y, epochs=200, lr=0.005)
    return model, scaler

model, scaler = initialize_system()


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    # Wordmark
    st.markdown("""
    <div class="logo-wrap">
      <div class="logo-icon">⚕</div>
      <div>
        <div class="logo-name">DiabRisk</div>
        <div class="logo-tag">Clinical Decision Tool</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Patient Vitals ────────────────────────────────────────
    st.markdown('<div class="sb-section">Patient Vitals</div>', unsafe_allow_html=True)

    pregnancies_input = st.number_input(
        "Pregnancies",
        min_value=0, max_value=17, value=3, step=1,
        help="Number of times pregnant (Dataset range: 0–17)",
    )

    glucose_input = st.number_input(
        "Plasma Glucose (mg/dL)",
        min_value=44, max_value=199, value=120, step=1,
        help="2-hour plasma glucose. Diabetic threshold ≥ 126 mg/dL",
    )
    if glucose_input >= 126:
        st.caption("⚠ Elevated — above diabetic threshold")
    else:
        st.caption("✓ Within normal range")

    bp_input = st.number_input(
        "Diastolic BP (mm Hg)",
        min_value=24, max_value=122, value=70, step=1,
        help="Normal: 60–80 mm Hg",
    )
    if bp_input > 90:
        st.caption("⚠ Elevated diastolic pressure")
    else:
        st.caption("✓ Normal range")

    # ── Anthropometrics ───────────────────────────────────────
    st.markdown('<div class="sb-section">Anthropometrics</div>', unsafe_allow_html=True)

    skin_input = st.number_input(
        "Triceps Skinfold (mm)",
        min_value=0, max_value=99, value=20, step=1,
        help="Triceps skin fold thickness — proxy for body fat",
    )

    bmi_input = st.number_input(
        "BMI (kg/m²)",
        min_value=10.0, max_value=68.0, value=32.0, step=0.1, format="%.1f",
        help="Normal 18.5–24.9 | Overweight 25–29.9 | Obese 30+",
    )
    bmi_label = (
        "✓ Healthy weight" if bmi_input < 25 else
        "⚠ Overweight" if bmi_input < 30 else
        "⚠ Obese class"
    )
    st.caption(bmi_label)

    # ── Lab Results ───────────────────────────────────────────
    st.markdown('<div class="sb-section">Lab Results</div>', unsafe_allow_html=True)

    insulin_input = st.number_input(
        "Serum Insulin (μU/mL)",
        min_value=0, max_value=846, value=80, step=1,
        help="2-hour serum insulin. Normal fasting: 16–166 μU/mL",
    )

    pedigree_input = st.number_input(
        "Diabetes Pedigree Score",
        min_value=0.000, max_value=2.420, value=0.470, step=0.001, format="%.3f",
        help="Genetic risk function based on family history. Higher = greater hereditary risk.",
    )
    if pedigree_input > 1.0:
        st.caption("⚠ High hereditary risk factor")
    else:
        st.caption("✓ Moderate hereditary risk")

    # ── Demographics ──────────────────────────────────────────
    st.markdown('<div class="sb-section">Demographics</div>', unsafe_allow_html=True)

    age_input = st.number_input(
        "Age (years)",
        min_value=21, max_value=81, value=33, step=1,
        help="Pima study enrolled women aged 21+",
    )

    # ── Model Settings ────────────────────────────────────────
    st.markdown('<div class="sb-section">Model Settings</div>', unsafe_allow_html=True)

    num_mc_samples = st.number_input(
        "MC Dropout Passes",
        min_value=10, max_value=200, value=50, step=10,
        help="More passes = better uncertainty estimate, slightly slower.",
    )
    st.caption(f"Running {int(num_mc_samples)} stochastic forward passes per inference.")


# =============================================================================
# MAIN AREA
# =============================================================================

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <div class="page-eyebrow">Pima Indians Diabetes Dataset · Monte Carlo Dropout · PyTorch</div>
  <div class="page-title">Probabilistic Diabetes Risk Assessment</div>
  <div class="page-desc">
    Enter patient measurements in the sidebar, then run the assessment.<br>
    The model performs <strong>multiple stochastic forward passes</strong> to quantify prediction uncertainty
    alongside the risk estimate.
  </div>
</div>
""", unsafe_allow_html=True)

# Dataset chips
st.markdown("""
<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:1.4rem;">
  <span class="info-chip">👥 <span>768</span> patient records</span>
  <span class="info-chip">📊 <span>8</span> clinical features</span>
  <span class="info-chip">🎯 <span>35%</span> positive prevalence</span>
  <span class="info-chip">🔬 MC Dropout uncertainty</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Two-column layout ─────────────────────────────────────────────────────────
col_left, col_right = st.columns([1.1, 1], gap="large")

with col_left:
    # Patient summary card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Patient at a Glance</div>', unsafe_allow_html=True)

    summary_df = pd.DataFrame({
        "Clinical Measure": [
            "Pregnancies", "Plasma Glucose", "Diastolic BP", "Triceps Skinfold",
            "Serum Insulin", "BMI", "Pedigree Score", "Age",
        ],
        "Patient": [
            str(pregnancies_input),
            f"{glucose_input} mg/dL",
            f"{bp_input} mm Hg",
            f"{skin_input} mm",
            f"{insulin_input} μU/mL",
            f"{bmi_input:.1f} kg/m²",
            f"{pedigree_input:.3f}",
            f"{age_input} yrs",
        ],
        "Dataset Avg": [
            "3.8", "120.9 mg/dL", "69.1 mm Hg", "20.5 mm",
            "79.8 μU/mL", "32.0 kg/m²", "0.472", "33.2 yrs",
        ],
    })

    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    run_button = st.button(
        "⚕  Run Diagnostic Assessment",
        type="primary",
        use_container_width=True,
    )

with col_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">How the Model Works</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="step-list">
      <div class="step-item">
        <div class="step-num">1</div>
        <div class="step-body"><strong>Normalisation</strong> — Raw measurements are Z-score scaled to the training distribution so all 8 features contribute equally.</div>
      </div>
      <div class="step-item">
        <div class="step-num">2</div>
        <div class="step-body"><strong>Stochastic Inference</strong> — Dropout stays active during inference. The network is run N times; each run drops different neurons, producing slightly different outputs.</div>
      </div>
      <div class="step-item">
        <div class="step-num">3</div>
        <div class="step-body"><strong>Uncertainty Quantification</strong> — The <em>variance</em> of all N outputs measures disagreement. High variance → flag for physician review.</div>
      </div>
      <div class="step-item">
        <div class="step-num">4</div>
        <div class="step-body"><strong>Triage</strong> — If variance ≥ threshold: escalate. Otherwise classify by mean probability (> 0.5 = positive, ≤ 0.5 = negative).</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# INFERENCE RESULTS
# =============================================================================

if run_button:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    with st.spinner(f"Running {int(num_mc_samples)} Monte Carlo forward passes…"):
        time.sleep(0.35)

        input_tensor = prepare_input_tensor(
            pregnancies=pregnancies_input,
            glucose=glucose_input,
            blood_pressure=bp_input,
            skin_thickness=skin_input,
            insulin=insulin_input,
            bmi=bmi_input,
            diabetes_pedigree=pedigree_input,
            age=age_input,
            scaler=scaler,
        )

        results = predict_with_uncertainty(
            model=model,
            input_tensor=input_tensor,
            num_samples=num_mc_samples,
        )

        risk_tier = classify_risk_tier(results["mean"], results["variance"])

    mean_pct = results["mean"] * 100
    std_dev   = float(np.std(results["all_samples"]))

    # ── KPI Tiles ─────────────────────────────────────────────
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-tile">
        <div class="kpi-label">Mean Risk Probability</div>
        <div class="kpi-value">{mean_pct:.1f}<span style="font-size:1.1rem;font-weight:500;color:var(--slate-400)">%</span></div>
        <div class="kpi-sub">Averaged across {int(num_mc_samples)} passes</div>
      </div>
      <div class="kpi-tile amber">
        <div class="kpi-label">Epistemic Uncertainty (σ²)</div>
        <div class="kpi-value" style="font-size:1.55rem;">{results['variance']:.5f}</div>
        <div class="kpi-sub">Threshold: {UNCERTAINTY_THRESHOLD}</div>
      </div>
      <div class="kpi-tile slate">
        <div class="kpi-label">Standard Deviation (σ)</div>
        <div class="kpi-value" style="font-size:1.55rem;">±{std_dev:.4f}</div>
        <div class="kpi-sub">Spread of MC predictions</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Risk gauge bar ─────────────────────────────────────────
    gauge_class = "high" if mean_pct >= 60 else ("medium" if mean_pct >= 35 else "low")
    st.markdown(f"""
    <div class="gauge-wrap">
      <div class="gauge-label"><span>Low risk</span><span>High risk</span></div>
      <div class="gauge-track">
        <div class="gauge-fill {gauge_class}" style="width:{min(mean_pct,100):.1f}%"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Clinical Verdict ──────────────────────────────────────
    if risk_tier == "FLAG_FOR_DOCTOR":
        st.markdown(f"""
        <div class="verdict uncertain">
          <div class="verdict-icon">🟡</div>
          <div>
            <div class="verdict-title">Inconclusive — Physician Review Required</div>
            <div class="verdict-body">
              The {int(num_mc_samples)} stochastic samples produced a prediction variance of
              <strong>{results['variance']:.5f}</strong>, exceeding the uncertainty threshold of
              <strong>{UNCERTAINTY_THRESHOLD}</strong>. The model's internal masked variants could not
              reach consensus on this clinical profile. This may indicate a borderline presentation
              or an atypical feature combination outside the training distribution.
              <br><br>
              <em>Mean estimate: {mean_pct:.1f}% · σ = ±{std_dev:.4f}</em>
            </div>
            <span class="verdict-badge">Escalate · Ref. Physician</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    elif risk_tier == "HIGH_CONFIDENCE_POSITIVE":
        st.markdown(f"""
        <div class="verdict positive">
          <div class="verdict-icon">🔴</div>
          <div>
            <div class="verdict-title">High Risk — Positive Classification</div>
            <div class="verdict-body">
              Model confidence is high (σ² = <strong>{results['variance']:.5f}</strong> &lt; {UNCERTAINTY_THRESHOLD}).
              The mean risk estimate is <strong>{mean_pct:.1f}%</strong>, above the 50% decision boundary.
              All {int(num_mc_samples)} Monte Carlo samples were in close agreement on a positive classification.
              <br><br>
              Clinical follow-up is recommended, including fasting glucose confirmation and HbA1c testing.
            </div>
            <span class="verdict-badge">High Risk · Follow Up</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown(f"""
        <div class="verdict negative">
          <div class="verdict-icon">🟢</div>
          <div>
            <div class="verdict-title">Low Risk — Negative Classification</div>
            <div class="verdict-body">
              Model confidence is high (σ² = <strong>{results['variance']:.5f}</strong> &lt; {UNCERTAINTY_THRESHOLD}).
              The mean risk estimate is <strong>{mean_pct:.1f}%</strong>, below the 50% decision boundary.
              All {int(num_mc_samples)} Monte Carlo samples were in close agreement on a negative classification.
              <br><br>
              Standard periodic health monitoring is recommended.
            </div>
            <span class="verdict-badge">Low Risk · Monitor</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── MC Distribution Chart ─────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Monte Carlo Dropout Distribution</div>', unsafe_allow_html=True)
    st.markdown(
        f"Each bar represents predictions from individual stochastic forward passes. "
        f"**Narrow spread = confident model. Wide spread = uncertain model.**",
    )

    # Styled matplotlib chart — warm clinical palette
    fig, ax = plt.subplots(figsize=(10, 3.6))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f7f6f3")

    # Determine fill colour from risk
    bar_color = "#dc2626" if gauge_class == "high" else ("#d97706" if gauge_class == "medium" else "#059669")
    bar_edge  = "#ffffff"

    ax.hist(
        results["all_samples"],
        bins=min(22, num_mc_samples),
        color=bar_color,
        edgecolor=bar_edge,
        linewidth=0.7,
        alpha=0.75,
    )

    ax.axvline(results["mean"], color="#1a202c", linestyle="--", linewidth=1.8,
               label=f"Mean μ = {results['mean']:.4f}")

    ax.axvspan(
        max(0.0, results["mean"] - std_dev),
        min(1.0, results["mean"] + std_dev),
        alpha=0.12, color="#1a202c",
        label=f"±1σ = ±{std_dev:.4f}",
    )

    ax.axvline(0.5, color="#d97706", linestyle=":", linewidth=1.5,
               label="Decision threshold = 0.50")

    ax.set_xlabel("P(Diabetes)", color="#475569", fontsize=10, fontfamily="sans-serif")
    ax.set_ylabel(f"Count / {int(num_mc_samples)}", color="#475569", fontsize=10)
    ax.set_title(
        f"MC Dropout  ·  μ = {results['mean']:.4f}  ·  σ² = {results['variance']:.5f}  ·  {risk_tier.replace('_', ' ')}",
        color="#1a202c", fontsize=10.5, fontweight="bold", pad=10,
    )
    ax.tick_params(colors="#94a3b8", labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#dde3ec")
    ax.set_xlim(0, 1)
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)

    legend = ax.legend(
        facecolor="#ffffff", edgecolor="#dde3ec",
        labelcolor="#374151", fontsize=8.5,
    )

    plt.tight_layout(pad=1.0)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Raw samples expander ──────────────────────────────────
    with st.expander(f"View all {int(num_mc_samples)} individual MC pass predictions"):
        st.caption(
            "Each row is the output of one stochastic forward pass. "
            "The variation between rows is Monte Carlo Dropout at work."
        )
        raw_df = pd.DataFrame({
            "Pass #": list(range(1, int(num_mc_samples) + 1)),
            "P(Diabetes)": [round(s, 6) for s in results["all_samples"]],
        })
        st.dataframe(raw_df, use_container_width=True, hide_index=True)


# =============================================================================
# DATASET EXPLORER
# =============================================================================

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Pima Indians Diabetes Dataset</div>', unsafe_allow_html=True)

with st.expander("Browse the full 768-row clinical dataset"):
    clinical_df = get_clinical_data_as_dataframe()
    total     = len(clinical_df)
    positives = int(clinical_df["actual_diagnosis"].sum())
    negatives = total - positives

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Records", total)
    c2.metric("Positive (Diabetic)", f"{positives} ({positives/total*100:.1f}%)")
    c3.metric("Negative (Non-Diabetic)", f"{negatives} ({negatives/total*100:.1f}%)")

    st.markdown("<br>", unsafe_allow_html=True)
    col_stat, col_dist = st.columns(2)

    with col_stat:
        st.markdown("**Feature Statistics**")
        feature_cols = ["pregnancies", "glucose", "blood_pressure",
                        "skin_thickness", "insulin", "bmi", "diabetes_pedigree"]
        stats_df = clinical_df[feature_cols].describe().round(2).T
        stats_df.index = ["Pregnancies", "Glucose", "Blood Pressure",
                          "Skin Thickness", "Insulin", "BMI", "Pedigree Score"]
        st.dataframe(stats_df[["mean", "std", "min", "max"]], use_container_width=True)

    with col_dist:
        st.markdown("**Outcome Distribution**")
        dist_df = pd.DataFrame({
            "Outcome": ["Negative (0)", "Positive (1)"],
            "Count": [negatives, positives],
            "Share": [f"{negatives/total*100:.1f}%", f"{positives/total*100:.1f}%"],
        })
        st.dataframe(dist_df, use_container_width=True, hide_index=True)

    st.markdown("**Full Patient Records**")
    display_df = clinical_df.rename(columns={
        "record_id": "Record ID", "patient_id": "Patient ID",
        "age": "Age", "gender": "Gender",
        "pregnancies": "Pregnancies", "glucose": "Glucose",
        "blood_pressure": "Blood Pressure", "skin_thickness": "Skin Thickness",
        "insulin": "Insulin", "bmi": "BMI",
        "diabetes_pedigree": "Pedigree Score", "actual_diagnosis": "Diagnosis",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("""
<div class="footer">
  <strong>DiabRisk</strong> · Probabilistic Diabetes Risk Assessment ·
  Deep Learning Mini-Project<br>
  Pima Indians Diabetes Dataset &nbsp;·&nbsp; Monte Carlo Dropout &nbsp;·&nbsp;
  PyTorch &nbsp;·&nbsp; Streamlit
  <br>
  <span class="footer-warn">⚠ For academic and educational use only — not validated for clinical practice.</span>
</div>
""", unsafe_allow_html=True)
