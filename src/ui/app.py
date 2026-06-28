import json
import re
import sys
import os
import uuid

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agents.travel_agent import run_agent

st.set_page_config(
    page_title="Travel Itinerary Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Tighten global padding */
.block-container { padding-top: 3.5rem !important; padding-bottom: 0.5rem !important; max-width: 900px; }
div[data-testid="stSidebarContent"] { padding-top: 0.75rem; }

/* Compact place cards */
.place-card {
    background: #f8f9fa;
    border-left: 3px solid #1E88E5;
    border-radius: 5px;
    padding: 7px 11px;
    margin: 4px 0;
    height: 100%;
}
.place-card h4 { margin: 0 0 3px 0; color: #1565C0; font-size: 0.88em; }
.place-card .why { color: #37474F; font-size: 0.8em; line-height: 1.35; }
.place-card .tip { color: #2E7D32; font-size: 0.76em; font-style: italic; margin-top: 3px; }
.place-card .meta { color: #90A4AE; font-size: 0.72em; margin-top: 3px; }

/* Compact weather chip */
.weather-chip {
    display: inline-block;
    background: #E3F2FD;
    border-radius: 10px;
    padding: 1px 8px;
    font-size: 0.78em;
    color: #1565C0;
    margin-bottom: 5px;
}

/* Compact sidebar info */
.sidebar-block { font-size: 0.82em; line-height: 1.8; color: #37474F; }
.sidebar-block b { color: #1a1a1a; }
.sidebar-wx { font-size: 0.78em; line-height: 1.7; }

/* Shrink Streamlit success/info box */
div[data-testid="stAlert"] { padding: 6px 12px; font-size: 0.85em; }

/* Tighter expander */
details summary { font-size: 0.9em; }

/* Smaller chat messages */
div[data-testid="stChatMessage"] { padding: 6px 0; }
</style>
""", unsafe_allow_html=True)


def _extract_json(text: str) -> dict | None:
    clean = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def render_itinerary(plan: dict) -> None:
    st.success(plan.get("intro", "Here is your itinerary!"))

    for day in plan.get("days", []):
        day_num = day.get("day", "?")
        theme   = day.get("theme", "")
        weather = day.get("weather")

        label = f"Day {day_num} — {theme}"
        if weather:
            label += f"  ·  {weather.get('condition', '')} {weather.get('max_temp_c')}°/{weather.get('min_temp_c')}°C"

        with st.expander(label, expanded=False):
            places = day.get("places", [])
            cols = st.columns(2)
            for i, place in enumerate(places):
                name    = place.get("name", "")
                ptype   = place.get("type", "").capitalize()
                why     = place.get("why", "")
                tip     = place.get("tip", "")
                hours   = place.get("opening_hours", "")
                cuisine = place.get("cuisine", "")
                walk    = place.get("walk_from_prev_min")

                meta_parts = []
                if ptype:   meta_parts.append(ptype)
                if hours:   meta_parts.append(f"Open: {hours}")
                if cuisine: meta_parts.append(f"{cuisine}")
                if walk:    meta_parts.append(f"{walk} min walk")

                with cols[i % 2]:
                    st.markdown(f"""
<div class="place-card">
  <h4>{name}</h4>
  <div class="why">{why}</div>
  {"<div class='tip'>Tip: " + tip + "</div>" if tip else ""}
  {"<div class='meta'>" + " · ".join(meta_parts) + "</div>" if meta_parts else ""}
</div>""", unsafe_allow_html=True)

    if plan.get("bonus_tip"):
        st.info(f"**Local tip:** {plan['bonus_tip']}")


def render_sidebar(plan: dict) -> None:
    ci   = plan.get("country_info")
    fx   = plan.get("currency_info")
    days = plan.get("days", [])

    if ci:
        flag = ci.get("flag", "")
        cap  = ci.get("capital", "—")
        cur  = ", ".join(ci.get("currency", ["—"]))
        lang = ", ".join(ci.get("languages", ["—"])[:2])
        tz   = (ci.get("timezones") or ["—"])[0]
        st.sidebar.markdown(
            f"### {flag} {ci.get('name', '')}\n"
            f'<div class="sidebar-block">'
            f"🏛 <b>Capital</b> {cap}<br>"
            f"💰 <b>Currency</b> {cur}<br>"
            f"🗣 <b>Language</b> {lang}<br>"
            f"🕐 <b>Timezone</b> {tz}</div>",
            unsafe_allow_html=True,
        )

    if fx and fx.get("rate"):
        st.sidebar.markdown(
            f'<div class="sidebar-block" style="margin-top:8px">'
            f"💱 1 {fx['from_currency']} = <b>{fx['rate']:.4f}</b> {fx['to_currency']}"
            f"<br><span style='font-size:0.75em;color:#9E9E9E'>as of {fx.get('date','today')}</span></div>",
            unsafe_allow_html=True,
        )

    weather_days = [d["weather"] for d in days if d.get("weather")]
    if weather_days:
        st.sidebar.markdown("---")
        rows = ""
        for w in weather_days:
            icon = "🌧" if w.get("precipitation_mm", 0) > 1 else "☀️"
            rows += (
                f"`{w['date']}` {icon} {w.get('condition','')}<br>"
                f"&nbsp;&nbsp;&nbsp;<b>{w.get('max_temp_c')}° / {w.get('min_temp_c')}°C</b><br>"
            )
        st.sidebar.markdown(
            f'<div class="sidebar-wx">{rows}</div>',
            unsafe_allow_html=True,
        )


# ── Sidebar header ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ✈️ Trip Info")
    st.caption("Gemini · Open-Meteo · OSM · Frankfurter")
    if "current_plan" not in st.session_state:
        st.info("Ask me where you'd like to go!")

# ── Init session state ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.current_plan = None

# ── Main header ────────────────────────────────────────────────────────────────
st.markdown("### ✈️ Travel Itinerary Agent")

# Example queries (only before first message)
if not st.session_state.messages:
    examples = [
        "3 days in New York — historical places",
        "5 days in Paris — art museums & cafés (GBP)",
        "Best ramen restaurants in Tokyo",
        "2 days outdoors in Sydney",
    ]
    cols = st.columns(4)
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            full = {
                "3 days in New York — historical places": "I want to visit New York for 3 days. I love historical places.",
                "5 days in Paris — art museums & cafés (GBP)": "Plan 5 days in Paris focused on art museums and cafés. Show prices in GBP.",
                "Best ramen restaurants in Tokyo": "Recommend the best ramen restaurants in Tokyo.",
                "2 days outdoors in Sydney": "What outdoor spots should I visit in Sydney for 2 days?",
            }[ex]
            st.session_state["_prefill"] = full
            st.rerun()

# ── Render chat history ────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("plan"):
            render_itinerary(msg["plan"])
        else:
            st.markdown(msg["content"])

# ── Handle example button prefill ─────────────────────────────────────────────
prefill = st.session_state.pop("_prefill", None)

# ── Chat input ─────────────────────────────────────────────────────────────────
prompt = st.chat_input("Where do you want to go?") or prefill
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Planning your trip…"):
            try:
                response_text = run_agent(prompt, st.session_state.session_id)
            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    st.warning("Gemini is temporarily busy. Please try again in a moment.")
                else:
                    st.error(f"Something went wrong: {e}")
                st.stop()

        plan = _extract_json(response_text)
        if plan and "days" in plan:
            render_itinerary(plan)
            render_sidebar(plan)
            st.session_state.current_plan = plan
            st.session_state.messages.append({
                "role": "assistant", "content": response_text, "plan": plan,
            })
        else:
            st.markdown(response_text)
            st.session_state.messages.append({
                "role": "assistant", "content": response_text,
            })
