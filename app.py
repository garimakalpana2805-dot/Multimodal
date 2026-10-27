"""
Multimodal Construction Intelligence Platform
Skill Wallet Capstone Project 1 - Streamlit application.

Run:  streamlit run app.py
Deploy: push app.py + requirements.txt to GitHub -> Streamlit Community Cloud.
"""
import json
import re
import urllib.parse
from datetime import datetime

import streamlit as st
from PIL import Image

# ------------------------------------------------------------------ #
# Page config & CSS
# ------------------------------------------------------------------ #
st.set_page_config(page_title="Construction Intelligence Platform",
                   page_icon="🏗️", layout="wide")

st.markdown("""
<style>
.hero{background:linear-gradient(120deg,#1f3a5f,#e07a1f);padding:1.4rem 1.6rem;
      border-radius:14px;color:#fff;margin-bottom:1rem}
.hero h1{margin:0;font-size:1.8rem;color:#fff}
.hero p{margin:.3rem 0 0;opacity:.9}
.card{background:#ffffff0d;border:1px solid #8884;border-radius:12px;padding:.9rem 1.1rem;
      text-align:center}
.card .v{font-size:1.7rem;font-weight:700}
.card .l{font-size:.8rem;opacity:.7;text-transform:uppercase;letter-spacing:.05em}
.pill{display:inline-block;padding:.2rem .75rem;border-radius:999px;font-weight:600;
      font-size:.82rem;color:#fff}
.p-ok{background:#2e9e5b}.p-low{background:#3b82c4}.p-med{background:#d9a21b}
.p-high{background:#e06b1f}.p-crit{background:#c0392b}
.alert{border-left:5px solid #e07a1f;background:#e07a1f18;padding:.8rem 1rem;
       border-radius:6px;margin:.5rem 0}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero"><h1>🏗️ Multimodal Construction Intelligence Platform</h1>
<p>AI-powered safety audits, structural diagnostics, valuation and site advisory.</p></div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
SEVERITY_CLASS = {"low": "p-low", "medium": "p-med", "high": "p-high",
                  "critical": "p-crit", "ok": "p-ok"}


def pill(text: str, level: str = "ok") -> str:
    cls = SEVERITY_CLASS.get(str(level).lower(), "p-ok")
    return f'<span class="pill {cls}">{text}</span>'


def metric_card(label: str, value: str) -> str:
    return f'<div class="card"><div class="v">{value}</div><div class="l">{label}</div></div>'


def fmt_inr(amount: float) -> str:
    if amount >= 1e7:
        return f"₹{amount / 1e7:,.2f} Cr"
    return f"₹{amount / 1e5:,.2f} Lakh"


def parse_json(text: str) -> dict:
    """Extract a JSON object from a model response (tolerates code fences)."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response.")
    return json.loads(text[start:end + 1])


def get_client():
    key = st.session_state.get("api_key", "").strip()
    if not key:
        return None
    from google import genai
    return genai.Client(api_key=key)


def call_gemini_vision(prompt: str, image: Image.Image) -> dict:
    from google.genai import types
    client = get_client()
    resp = client.models.generate_content(
        model=st.session_state["model_name"],
        contents=[prompt, image],
        config=types.GenerateContentConfig(response_mime_type="application/json",
                                           temperature=0.2),
    )
    return parse_json(resp.text)


def load_image(uploaded) -> Image.Image:
    img = Image.open(uploaded)
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    return img


def download_report(data: dict, name: str):
    st.download_button("⬇️ Download JSON report",
                       json.dumps(data, indent=2),
                       file_name=f"{name}_{datetime.now():%Y%m%d_%H%M%S}.json",
                       mime="application/json")


# ------------------------------------------------------------------ #
# Prompts
# ------------------------------------------------------------------ #
SAFETY_PROMPT = """You are a certified construction safety officer. Analyze this construction
site photo for worker PPE compliance and site hazards under OSHA 1926 and relevant Indian
standards (IS 456 for concrete works, IS 3764 for excavation safety, BOCW Act).
Check: helmets, high-visibility vests, steel-toe boots, safety harnesses.
Respond ONLY with JSON in this exact schema:
{
 "safety_score": <int 0-100>,
 "overall_status": "Compliant" | "Needs Improvement" | "Non-Compliant",
 "workers_detected": <int>,
 "ppe_detection": {"helmet": "Yes|No|Partial|Not Visible", "high_vis_vest": "...",
                   "steel_toe_boots": "...", "safety_harness": "..."},
 "hazards": [{"hazard": "...", "severity": "Low|Medium|High|Critical",
              "standard": "...", "remedy": "..."}],
 "summary": "..."
}
If something is not determinable from the image, say "Not Visible" rather than guessing."""

CRACK_PROMPT = """You are a senior structural engineer. Examine this concrete/wall surface image.
Classify the defect as one of: Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling
(or "No Defect"). Estimate crack width in mm (state it is an estimate from the image).
Respond ONLY with JSON:
{
 "defect_type": "...",
 "estimated_width_mm": <number>,
 "confidence": <int 0-100>,
 "urgency": "Low|Medium|High|Critical",
 "root_causes": ["..."],
 "recommended_repairs": [{"method": "e.g. Epoxy injection, structural re-grouting, ...",
                          "details": "..."}],
 "monitoring_advice": "...",
 "summary": "..."
}"""

# ------------------------------------------------------------------ #
# Demo-mode data
# ------------------------------------------------------------------ #
DEMO_SAFETY = {
    "safety_score": 62, "overall_status": "Needs Improvement", "workers_detected": 3,
    "ppe_detection": {"helmet": "Yes", "high_vis_vest": "Partial",
                      "steel_toe_boots": "Not Visible", "safety_harness": "No"},
    "hazards": [
        {"hazard": "Worker at height without harness", "severity": "Critical",
         "standard": "OSHA 1926.501", "remedy": "Stop work; provide full-body harness anchored to a rated point."},
        {"hazard": "Loose material at slab edge", "severity": "High",
         "standard": "OSHA 1926.502", "remedy": "Install toe boards and secure/stack materials."},
        {"hazard": "Poor housekeeping near walkway", "severity": "Medium",
         "standard": "BOCW Rules", "remedy": "Clear debris; mark and barricade walkways."}],
    "summary": "DEMO MODE: sample output. Add a Gemini API key for real image analysis."}

DEMO_CRACK = {
    "defect_type": "Settlement", "estimated_width_mm": 2.5, "confidence": 70,
    "urgency": "High",
    "root_causes": ["Differential foundation settlement", "Poor soil compaction",
                    "Water ingress softening sub-base"],
    "recommended_repairs": [
        {"method": "Epoxy injection", "details": "Seal active cracks after settlement stabilizes."},
        {"method": "Structural re-grouting", "details": "Pressure-grout voids beneath footing."}],
    "monitoring_advice": "Install crack gauges and record readings fortnightly for 3 months.",
    "summary": "DEMO MODE: sample output. Add a Gemini API key for real analysis."}

# ------------------------------------------------------------------ #
# Sidebar
# ------------------------------------------------------------------ #
with st.sidebar:
    st.header("🔐 Configuration")
    st.session_state["api_key"] = st.text_input(
        "Google Gemini API key", type="password",
        value=st.session_state.get("api_key", ""),
        help="Get a free key at aistudio.google.com. Never share or commit it.")
    st.session_state["model_name"] = st.text_input(
        "Model", value=st.session_state.get("model_name", "gemini-2.5-flash"))
    LIVE = bool(st.session_state["api_key"].strip())
    if LIVE:
        st.success("Live mode: Gemini connected")
    else:
        st.info("Demonstration mode: sample outputs are shown. Enter a key for live AI.")

    st.divider()
    st.subheader("🧭 Features")
    st.markdown("""
- 🦺 **Safety & PPE Audit**
- 🧱 **Crack Diagnostics**
- 💰 **Planning & Valuation**
- 🌦️ **Site Assistant & Weather**
""")
    st.divider()
    st.subheader("🏛️ Architecture")
    st.markdown("""
`Streamlit UI` → `Image preprocessing (Pillow)` → `Gemini multimodal API`
→ `JSON parser/validator` → `Cards, pills, reports`

No database. State lives in `st.session_state`.
""")

tab1, tab2, tab3, tab4 = st.tabs([
    "🦺 Safety & PPE Audit", "🧱 Crack Diagnostics",
    "💰 Planning & Valuation", "🌦️ Site Assistant"])

# ------------------------------------------------------------------ #
# Tab 1: Safety
# ------------------------------------------------------------------ #
with tab1:
    st.subheader("Site Safety & PPE Audit")
    up = st.file_uploader("Upload a construction site photo", type=["jpg", "jpeg", "png"],
                          key="safety_up")
    if up:
        try:
            img = load_image(up)
        except Exception as e:
            st.error(f"Could not read image: {e}")
            img = None
        if img:
            left, right = st.columns([1, 1.2])
            left.image(img, caption="Uploaded site photo", use_container_width=True)
            if left.button("Run safety audit", type="primary", key="run_safety"):
                with st.spinner("Analyzing site..."):
                    try:
                        st.session_state["safety"] = (call_gemini_vision(SAFETY_PROMPT, img)
                                                      if LIVE else DEMO_SAFETY)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
            res = st.session_state.get("safety")
            if res:
                with right:
                    score = int(res.get("safety_score", 0))
                    level = "ok" if score >= 80 else "medium" if score >= 55 else "crit"
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(metric_card("Safety score", f"{score}/100"), unsafe_allow_html=True)
                    c2.markdown(metric_card("Workers", str(res.get("workers_detected", "-"))),
                                unsafe_allow_html=True)
                    c3.markdown(metric_card("Hazards", str(len(res.get("hazards", [])))),
                                unsafe_allow_html=True)
                    st.markdown(f"**Status:** {pill(res.get('overall_status', 'Unknown'), level)}",
                                unsafe_allow_html=True)
                    st.progress(max(0, min(score, 100)) / 100)
                    st.markdown("**PPE checklist**")
                    for item, val in res.get("ppe_detection", {}).items():
                        lv = {"yes": "ok", "partial": "medium", "no": "crit"}.get(
                            str(val).lower(), "low")
                        st.markdown(f"- {item.replace('_', ' ').title()}: {pill(val, lv)}",
                                    unsafe_allow_html=True)
                st.markdown("### Identified hazards")
                for h in res.get("hazards", []):
                    with st.expander(f"{h.get('hazard')}  ·  {h.get('severity')}"):
                        st.markdown(pill(h.get("severity", "Low"), h.get("severity", "low")),
                                    unsafe_allow_html=True)
                        st.write(f"**Standard:** {h.get('standard', '-')}")
                        st.write(f"**Remedy:** {h.get('remedy', '-')}")
                st.info(res.get("summary", ""))
                download_report(res, "safety_report")
    else:
        st.caption("Upload a photo to begin.")

# ------------------------------------------------------------------ #
# Tab 2: Cracks
# ------------------------------------------------------------------ #
with tab2:
    st.subheader("Crack Diagnostics & Structural Integrity")
    up2 = st.file_uploader("Upload a concrete / wall surface image",
                           type=["jpg", "jpeg", "png"], key="crack_up")
    if up2:
        try:
            img2 = load_image(up2)
        except Exception as e:
            st.error(f"Could not read image: {e}")
            img2 = None
        if img2:
            left, right = st.columns([1, 1.2])
            left.image(img2, caption="Surface under inspection", use_container_width=True)
            if left.button("Diagnose defect", type="primary", key="run_crack"):
                with st.spinner("Inspecting..."):
                    try:
                        st.session_state["crack"] = (call_gemini_vision(CRACK_PROMPT, img2)
                                                     if LIVE else DEMO_CRACK)
                    except Exception as e:
                        st.error(f"Diagnosis failed: {e}")
            r = st.session_state.get("crack")
            if r:
                with right:
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(metric_card("Defect", r.get("defect_type", "-")), unsafe_allow_html=True)
                    c2.markdown(metric_card("Width (est.)", f"{r.get('estimated_width_mm', '-')} mm"),
                                unsafe_allow_html=True)
                    c3.markdown(metric_card("Confidence", f"{r.get('confidence', '-')}%"),
                                unsafe_allow_html=True)
                    urg = r.get("urgency", "Low")
                    st.markdown(f"**Urgency:** {pill(urg, urg)}", unsafe_allow_html=True)
                    st.markdown("**Root causes**")
                    for c in r.get("root_causes", []):
                        st.markdown(f"- {c}")
                st.markdown("### Recommended repairs")
                for rep in r.get("recommended_repairs", []):
                    st.markdown(f"**🔧 {rep.get('method')}**: {rep.get('details')}")
                st.warning(f"**Monitoring:** {r.get('monitoring_advice', '-')}")
                st.info(r.get("summary", ""))
                st.caption("Width is a visual estimate. A licensed structural engineer must "
                           "verify on site before any repair decision.")
                download_report(r, "crack_report")
    else:
        st.caption("Upload a photo to begin.")

# ------------------------------------------------------------------ #
# Tab 3: Planning & valuation
# ------------------------------------------------------------------ #
COST_PER_SQFT = {"Residential (RCC framed)": 1800, "Commercial building": 2400,
                 "Industrial shed (PEB)": 1500, "Villa / premium finish": 3200,
                 "Load-bearing masonry": 1400}
TIER_MULT = {"Tier 1 (Mumbai, Delhi, Bengaluru)": 1.30, "Tier 2 (Indore, Jaipur, Pune)": 1.00,
             "Tier 3 (smaller cities)": 0.80}
MARKET_RATE = {"Tier 1 (Mumbai, Delhi, Bengaluru)": 9000, "Tier 2 (Indore, Jaipur, Pune)": 5000,
               "Tier 3 (smaller cities)": 3000}
STEEL_KG_PER_SQFT = {"Residential (RCC framed)": 4.0, "Commercial building": 5.0,
                     "Industrial shed (PEB)": 8.0, "Villa / premium finish": 4.5,
                     "Load-bearing masonry": 2.0}
CEMENT_BAGS_PER_SQFT = 0.40

MILESTONES = [(0, "Site prep"), (10, "Foundation"), (30, "Plinth & columns"),
              (50, "Slab & structure"), (70, "Masonry & services"),
              (85, "Finishing"), (100, "Handover")]

with tab3:
    st.subheader("Planning & Real Estate Valuation")
    c1, c2 = st.columns(2)
    stype = c1.selectbox("Structure type", list(COST_PER_SQFT))
    tier = c2.selectbox("Location tier", list(TIER_MULT))
    area = c1.number_input("Built-up area (sq ft)", min_value=100, max_value=500000,
                           value=2000, step=100)
    pct = c2.slider("Completion %", 0, 100, 40)

    budget = area * COST_PER_SQFT[stype] * TIER_MULT[tier]
    capex = budget * pct / 100
    # Market value: land+building market rate, scaled by completion (floor 35% for land/approvals)
    full_value = area * MARKET_RATE[tier] * (1.15 if "premium" in stype.lower() or "Villa" in stype else 1.0)
    value_now = full_value * (0.35 + 0.65 * pct / 100)
    steel_t = area * STEEL_KG_PER_SQFT[stype] / 1000
    cement_bags = area * CEMENT_BAGS_PER_SQFT

    m = st.columns(4)
    m[0].markdown(metric_card("Total budget", fmt_inr(budget)), unsafe_allow_html=True)
    m[1].markdown(metric_card("CapEx incurred", fmt_inr(capex)), unsafe_allow_html=True)
    m[2].markdown(metric_card("Current asset value", fmt_inr(value_now)), unsafe_allow_html=True)
    m[3].markdown(metric_card("Completed value gain", fmt_inr(value_now - capex)),
                  unsafe_allow_html=True)
    st.write("")
    m2 = st.columns(2)
    m2[0].markdown(metric_card("Steel requirement", f"{steel_t:,.1f} tonnes"), unsafe_allow_html=True)
    m2[1].markdown(metric_card("Cement requirement", f"{cement_bags:,.0f} bags (50 kg)"),
                   unsafe_allow_html=True)

    current = [n for p, n in MILESTONES if pct >= p][-1]
    st.markdown(f"**Milestone progress:** {current} ({pct}%)")
    st.progress(pct / 100)
    st.caption("Estimates use indicative planning rates (₹/sq ft, kg steel/sq ft). "
               "Replace with local rates and a BOQ for real decisions. Not a certified valuation.")

    st.markdown("### 🎨 Conceptual 3D rendering")
    style = st.selectbox("Architectural style",
                         ["Modern minimalist", "Contemporary Indian", "Industrial", "Eco-friendly"])
    default_prompt = (f"Photorealistic 3D architectural render of a {style.lower()} "
                      f"{stype.lower()}, {int(area)} sq ft, Indian city setting, golden hour, "
                      f"detailed facade, landscaped surroundings")
    prompt = st.text_area("Image prompt", default_prompt)
    if st.button("Generate concept image", key="gen_img"):
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
               + "?width=1024&height=640&nologo=true")
        st.session_state["concept_url"] = url
    if st.session_state.get("concept_url"):
        st.image(st.session_state["concept_url"], caption="Generated via Pollinations AI (conceptual only)",
                 use_container_width=True)

# ------------------------------------------------------------------ #
# Tab 4: Weather + assistant
# ------------------------------------------------------------------ #
WEATHER = {
    "Normal": {"level": "ok", "alerts": ["Standard operations permitted.",
                                         "Carry out daily toolbox talk and equipment checks."]},
    "High Wind": {"level": "high", "alerts": [
        "Suspend crane and hoist operations when wind exceeds ~36 km/h (check manufacturer limit).",
        "Secure scaffolding sheets, formwork and loose materials.",
        "Halt work at height and on exposed edges."]},
    "Heavy Rain": {"level": "high", "alerts": [
        "Electrical hazard: de-energize temporary supplies, use RCD-protected, waterproof connections.",
        "Cover freshly placed concrete; postpone pours and protect cement from moisture.",
        "Check excavation shoring and dewater trenches; slip hazard on ramps and scaffolds."]},
    "Extreme Heat": {"level": "medium", "alerts": [
        "Concrete curing protocol: start curing early, wet-cure/cover for min. 7 days, pour in early morning.",
        "Mandatory hydration, shaded rest breaks, and heat-stress monitoring for workers.",
        "Reschedule heavy manual work away from peak afternoon hours."]},
}

ASSISTANT_SYSTEM = ("You are a senior construction engineering assistant for Indian sites. "
                    "Give practical, concise answers citing relevant standards (IS 456, IS 800, "
                    "NBC 2016, OSHA) where useful. If safety-critical, advise consulting a "
                    "licensed engineer. Current site weather: {w}.")


def demo_reply(q: str) -> str:
    q = q.lower()
    if "cure" in q or "curing" in q:
        return "Cure concrete at least 7 days (10+ for blended cements) per IS 456; keep surfaces continuously moist."
    if "slump" in q:
        return "Typical slump: 25-75 mm for footings/slabs, 75-125 mm for columns and beams (IS 456). Test per batch."
    if "steel" in q or "rebar" in q:
        return "Use Fe500/Fe500D TMT bars; maintain cover per IS 456 (e.g. 25 mm beams, 40 mm footings)."
    if "ppe" in q or "safety" in q:
        return "Minimum PPE: helmet, hi-vis vest, safety boots, gloves; harness for work above 1.8 m."
    return ("(Demo mode) Add a Gemini API key in the sidebar for full answers. "
            "Try asking about curing, slump, rebar or PPE.")


with tab4:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    weather = st.radio("Today's site conditions", list(WEATHER), horizontal=True)
    info = WEATHER[weather]
    st.markdown(f"**Advisory level:** {pill(weather, info['level'])}", unsafe_allow_html=True)
    for a in info["alerts"]:
        st.markdown(f'<div class="alert">⚠️ {a}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💬 Engineering assistant")
    if "chat" not in st.session_state:
        st.session_state["chat"] = []
    if st.button("Clear chat"):
        st.session_state["chat"] = []

    for role, text in st.session_state["chat"]:
        with st.chat_message(role):
            st.markdown(text)

    q = st.chat_input("Ask about concrete, safety, scheduling, materials...")
    if q:
        st.session_state["chat"].append(("user", q))
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    if LIVE:
                        history = "\n".join(
                            f"{'User' if r == 'user' else 'Assistant'}: {t}"
                            for r, t in st.session_state["chat"])
                        resp = get_client().models.generate_content(
                            model=st.session_state["model_name"],
                            contents=ASSISTANT_SYSTEM.format(w=weather) + "\n\n" + history
                                     + "\nAssistant:")
                        ans = resp.text
                    else:
                        ans = demo_reply(q)
                except Exception as e:
                    ans = f"Sorry, the request failed: {e}"
            st.markdown(ans)
        st.session_state["chat"].append(("assistant", ans))
