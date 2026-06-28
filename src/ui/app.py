import json
import re
import sys
import os

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.agents.travel_agent import run_agent

st.set_page_config(
    page_title="Travel Itinerary Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.place-card {
    background: #f8f9fa;
    border-left: 4px solid #1E88E5;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 6px 0;
}
.place-card h4 { margin: 0 0 4px 0; color: #1565C0; }
.place-card .why { color: #37474F; font-size: 0.9em; }
.place-card .tip { color: #2E7D32; font-size: 0.85em; font-style: italic; }
.place-card .meta { color: #78909C; font-size: 0.8em; margin-top: 4px; }
.weather-chip {
    display: inline-block;
    background: #E3F2FD;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.82em;
    color: #1565C0;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)


def _extract_json(text: str) -> dict | None:
    """Try to parse a TravelPlan JSON from the agent response."""
    # Strip markdown fences if present
    clean = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try to find first {...} block
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def render_itinerary(plan: dict) -> None:
    """Render a TravelPlan dict as structured Streamlit UI."""
    st.success(plan.get("intro", "Here is your itinerary!"))

    for day in plan.get("days", []):
        day_num = day.get("day", "?")
        theme   = day.get("theme", "")
        weather = day.get("weather")

        weather_html = ""
        if weather:
            weather_html = (
                f'<span class="weather-chip">'
                f'{weather.get("condition", "")}  '
                f'{weather.get("max_temp_c", "?")}°C / {weather.get("min_temp_c", "?")}°C'
                f'{"  🌧 " + str(weather.get("precipitation_mm", 0)) + "mm" if weather.get("precipitation_mm", 0) > 0 else ""}'
                f'</span>'
            )

        with st.expander(f"Day {day_num} — {theme}", expanded=(day_num == 1)):
            if weather_html:
                st.markdown(weather_html, unsafe_allow_html=True)

            for place in day.get("places", []):
                name   = place.get("name", "")
                ptype  = place.get("type", "").capitalize()
                why    = place.get("why", "")
                tip    = place.get("tip", "")
                hours  = place.get("opening_hours", "")
                cuisine = place.get("cuisine", "")
                walk   = place.get("walk_from_prev_min")

                meta_parts = []
                if ptype:    meta_parts.append(ptype)
                if hours:    meta_parts.append(f"Open: {hours}")
                if cuisine:  meta_parts.append(f"Cuisine: {cuisine}")
                if walk:     meta_parts.append(f"{walk} min walk from previous")

                st.markdown(f"""
<div class="place-card">
  <h4>{name}</h4>
  <div class="why">{why}</div>
  {"<div class='tip'>Tip: " + tip + "</div>" if tip else ""}
  {"<div class='meta'>" + "  ·  ".join(meta_parts) + "</div>" if meta_parts else ""}
</div>
""", unsafe_allow_html=True)

    if plan.get("bonus_tip"):
        st.info(f"**Local tip:** {plan['bonus_tip']}")


def render_sidebar(plan: dict) -> None:
    """Populate the sidebar with country info, FX rate, and weather summary."""
    ci = plan.get("country_info")
    fx = plan.get("currency_info")
    days = plan.get("days", [])

    if ci:
        flag = ci.get("flag", "")
        st.sidebar.markdown(f"## {flag}  {ci.get('name', '')}")
        st.sidebar.metric("Capital", ci.get("capital", "—"))
        st.sidebar.metric("Currency", ", ".join(ci.get("currency", ["—"])))
        st.sidebar.metric("Language", ", ".join(ci.get("languages", ["—"])[:2]))
        tz = ci.get("timezones", ["—"])[0]
        st.sidebar.metric("Timezone", tz)

    if fx and fx.get("rate"):
        st.sidebar.divider()
        st.sidebar.metric(
            "Exchange Rate",
            f"1 {fx['from_currency']} = {fx['rate']:.4f} {fx['to_currency']}",
            help=f"As of {fx.get('date', 'today')}",
        )

    weather_days = [d["weather"] for d in days if d.get("weather")]
    if weather_days:
        st.sidebar.divider()
        st.sidebar.markdown("**Weather Forecast**")
        for w in weather_days:
            icon = "🌧" if w.get("precipitation_mm", 0) > 1 else "☀️"
            st.sidebar.markdown(
                f"`{w['date']}` {icon} {w.get('condition', '')}  "
                f"**{w.get('max_temp_c')}° / {w.get('min_temp_c')}°C**"
            )


# ── Sidebar header ────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("✈️ Trip Info")
    st.caption("Powered by Claude + free APIs")
    st.divider()
    if "current_plan" not in st.session_state:
        st.info("Ask me where you'd like to go!")

# ── Init session state ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.history  = []
    st.session_state.current_plan = None

# ── Main header ───────────────────────────────────────────────────────────────
st.title("✈️ Travel Itinerary Agent")
st.caption("Powered by Claude Sonnet · Open-Meteo · OpenStreetMap · Frankfurter · REST Countries")

# Example queries
if not st.session_state.messages:
    st.markdown("**Try one of these:**")
    examples = [
        "I want to visit New York for 3 days. I love historical places.",
        "Plan 5 days in Paris focused on art museums and cafés. Show prices in GBP.",
        "Recommend the best ramen restaurants in Tokyo.",
        "What outdoor spots should I visit in Sydney for 2 days?",
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        if cols[i % 2].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state["_prefill"] = ex
            st.rerun()

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("plan"):
            render_itinerary(msg["plan"])
        else:
            st.markdown(msg["content"])

# ── Handle example button prefill ────────────────────────────────────────────
prefill = st.session_state.pop("_prefill", None)

# ── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Where do you want to go?") or prefill
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Planning your trip… (calling live APIs)"):
            response_text = run_agent(prompt, st.session_state.history)

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

    st.session_state.history.append({"role": "user",      "content": prompt})
    st.session_state.history.append({"role": "assistant", "content": response_text})
