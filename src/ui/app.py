import json
import re
import sys
import os
import uuid

import streamlit as st
import folium
from streamlit_folium import st_folium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agents.travel_agent import run_agent
from src.ui.export import plan_to_pdf, plan_to_markdown

st.set_page_config(
    page_title="Travel Itinerary Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Layout ─────────────────────────────────────────────────────────────── */
.block-container {
    padding-top: 3rem !important;
    padding-bottom: 0 !important;
    max-width: 920px;
}
div[data-testid="stSidebarContent"] { padding-top: 0.75rem; }

/* ── Place cards ─────────────────────────────────────────────────────────── */
.place-card {
    background: #f8f9fb;
    border-left: 3px solid #1E88E5;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 4px 0;
    height: 100%;
}
.place-card h4 { margin: 0 0 3px 0; color: #1565C0; font-size: 0.87em; }
.place-card .why { color: #37474F; font-size: 0.8em; line-height: 1.35; }
.place-card .tip { color: #2E7D32; font-size: 0.76em; font-style: italic; margin-top: 3px; }
.place-card .meta { color: #90A4AE; font-size: 0.72em; margin-top: 3px; }

/* ── Hotel cards ─────────────────────────────────────────────────────────── */
.hotel-card {
    background: #F3E5F5;
    border-left: 3px solid #8E24AA;
    border-radius: 6px;
    padding: 7px 11px;
    margin: 4px 0;
    font-size: 0.82em;
    height: 100%;
}
.hotel-card b { color: #6A1B9A; }
.hotel-card .price { color: #8E24AA; font-weight: bold; }

/* ── Packing chips ───────────────────────────────────────────────────────── */
.pack-chips { margin: 4px 0 10px 0; }
.pack-chip {
    display: inline-block;
    background: #E8F5E9;
    border: 1px solid #A5D6A7;
    border-radius: 12px;
    padding: 2px 9px;
    font-size: 0.78em;
    color: #2E7D32;
    margin: 2px 3px 2px 0;
}

/* ── Example buttons ─────────────────────────────────────────────────────── */
.example-grid { margin-bottom: 8px; }
div[data-testid="stButton"] button {
    font-size: 0.8em !important;
    padding: 4px 8px !important;
    height: auto !important;
    white-space: normal !important;
    text-align: left !important;
    border-radius: 8px !important;
    border: 1px solid #e0e0e0 !important;
    background: #fafafa !important;
    color: #333 !important;
    line-height: 1.3 !important;
}
div[data-testid="stButton"] button:hover {
    border-color: #1E88E5 !important;
    color: #1565C0 !important;
    background: #EEF4FF !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
.sidebar-block { font-size: 0.82em; line-height: 1.8; color: #37474F; }
.sidebar-block b { color: #1a1a1a; }
.sidebar-wx { font-size: 0.78em; line-height: 1.7; }
.budget-row { font-size: 0.8em; line-height: 1.9; }

/* ── Misc ────────────────────────────────────────────────────────────────── */
div[data-testid="stAlert"] { padding: 6px 12px; font-size: 0.85em; }
details summary { font-size: 0.9em !important; }
div[data-testid="stChatMessage"] { padding: 4px 0; }
[data-testid="stChatInput"] { margin-top: 4px; }
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


_STOP_COLORS = ["#1E88E5", "#43A047", "#E53935", "#FB8C00", "#8E24AA", "#00ACC1"]


def _build_day_map(places: list[dict]) -> folium.Map | None:
    coords = [(p["lat"], p["lon"]) for p in places if p.get("lat") and p.get("lon")]
    if not coords:
        return None

    center_lat = sum(c[0] for c in coords) / len(coords)
    center_lon = sum(c[1] for c in coords) / len(coords)
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles="CartoDB positron",
        zoom_control=True,
        scrollWheelZoom=False,
    )

    for i, (lat, lon) in enumerate(coords):
        color = _STOP_COLORS[i % len(_STOP_COLORS)]
        name  = places[i].get("name", f"Stop {i+1}")
        tip   = places[i].get("tip", "")
        popup_html = f"<b>{i+1}. {name}</b><br><small>{tip}</small>"
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=f"{i+1}. {name}",
            icon=folium.DivIcon(
                html=(
                    f'<div style="background:{color};color:#fff;border-radius:50%;'
                    f'width:26px;height:26px;display:flex;align-items:center;'
                    f'justify-content:center;font-weight:bold;font-size:12px;'
                    f'border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">'
                    f'{i+1}</div>'
                ),
                icon_size=(26, 26),
                icon_anchor=(13, 13),
            ),
        ).add_to(m)

    if len(coords) > 1:
        folium.PolyLine(
            locations=coords,
            color="#1E88E5",
            weight=2.5,
            opacity=0.7,
            dash_array="6 4",
        ).add_to(m)

    return m


def render_itinerary(plan: dict) -> None:
    st.success(plan.get("intro", "Here is your itinerary!"))

    # Packing list chips
    packing = plan.get("packing_list", [])
    if packing:
        chips = "".join(f'<span class="pack-chip">🎒 {item}</span>' for item in packing)
        st.markdown(f'<div class="pack-chips">{chips}</div>', unsafe_allow_html=True)

    # Day expanders
    for day in plan.get("days", []):
        day_num = day.get("day", "?")
        theme   = day.get("theme", "")
        weather = day.get("weather")
        label   = f"Day {day_num} — {theme}"
        if weather:
            label += f"  ·  {weather.get('condition', '')} {weather.get('max_temp_c')}°/{weather.get('min_temp_c')}°C"

        with st.expander(label, expanded=False):
            places = day.get("places", [])
            day_map = _build_day_map(places)
            if day_map:
                st_folium(day_map, height=260, use_container_width=True, returned_objects=[])

            cols = st.columns(2)
            for i, place in enumerate(places):
                meta_parts = []
                if place.get("type"):          meta_parts.append(place["type"].capitalize())
                if place.get("opening_hours"): meta_parts.append(f"Open: {place['opening_hours']}")
                if place.get("cuisine"):       meta_parts.append(place["cuisine"])
                if place.get("walk_from_prev_min"): meta_parts.append(f"{place['walk_from_prev_min']} min walk")
                with cols[i % 2]:
                    st.markdown(f"""
<div class="place-card">
  <h4>{place.get('name','')}</h4>
  <div class="why">{place.get('why','')}</div>
  {"<div class='tip'>Tip: " + place['tip'] + "</div>" if place.get('tip') else ""}
  {"<div class='meta'>" + " · ".join(meta_parts) + "</div>" if meta_parts else ""}
</div>""", unsafe_allow_html=True)

    # Hotel area suggestions
    hotel_areas = plan.get("hotel_areas", [])
    if hotel_areas:
        st.markdown("**🏨 Where to Stay**")
        cols = st.columns(len(hotel_areas))
        for i, area in enumerate(hotel_areas):
            with cols[i]:
                st.markdown(f"""
<div class="hotel-card">
  <b>{area.get('name','')}</b> <span class="price">{area.get('price_range','')}</span><br>
  <span style="color:#555">{area.get('why','')}</span>
</div>""", unsafe_allow_html=True)

    if plan.get("bonus_tip"):
        st.info(f"**Local tip:** {plan['bonus_tip']}")

    # Download buttons
    dest = plan.get("destination", "itinerary").replace(", ", "-").replace(" ", "-").lower()
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        st.download_button(
            "⬇️ PDF", data=plan_to_pdf(plan),
            file_name=f"{dest}-itinerary.pdf", mime="application/pdf",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "⬇️ Markdown", data=plan_to_markdown(plan),
            file_name=f"{dest}-itinerary.md", mime="text/markdown",
            use_container_width=True,
        )


def render_sidebar(plan: dict) -> None:
    ci     = plan.get("country_info")
    fx     = plan.get("currency_info")
    days   = plan.get("days", [])
    budget = plan.get("budget_estimate")

    if ci:
        flag = ci.get("flag", "")
        cap  = ci.get("capital", "—")
        cur  = ", ".join(ci.get("currency", ["—"]))
        lang = ", ".join(ci.get("languages", ["—"])[:2])
        tz   = (ci.get("timezones") or ["—"])[0]
        st.sidebar.markdown(
            f"### {flag} {ci.get('name','')}\n"
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

    if budget:
        bcur = budget.get("currency", "USD")
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            f'<div class="budget-row">'
            f"💰 <b>Budget/day ({bcur})</b><br>"
            f"🟢 Budget &nbsp;&nbsp; {budget.get('per_day_low')}<br>"
            f"🟡 Mid-range {budget.get('per_day_mid')}<br>"
            f"🔴 Luxury &nbsp;&nbsp; {budget.get('per_day_high')}</div>",
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
        st.sidebar.markdown(f'<div class="sidebar-wx">{rows}</div>', unsafe_allow_html=True)


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

EXAMPLES = {
    "🗽 3 days NYC — history":        "I want to visit New York for 3 days. I love historical places.",
    "🎨 5 days Paris — art & cafés":  "Plan 5 days in Paris focused on art museums and cafés. Show prices in GBP.",
    "🍜 Best ramen in Tokyo":         "Recommend the best ramen restaurants in Tokyo.",
    "🏄 2 days outdoors in Sydney":   "What outdoor spots should I visit in Sydney for 2 days?",
    "🕌 2 days Delhi — culture":      "What are the best places to see in Delhi, India in two days?",
    "🌊 3 days in Bali — beaches":    "Plan 3 days in Bali focused on beaches and local culture.",
    "🏰 4 days Rome — ancient sites": "Plan 4 days in Rome. I love ancient history and architecture.",
    "🌮 2 days Mexico City — food":   "Plan 2 days in Mexico City focused on street food and local cuisine.",
}

if not st.session_state.messages:
    cols = st.columns(4)
    for i, (label, prompt) in enumerate(EXAMPLES.items()):
        if cols[i % 4].button(label, key=f"ex_{i}", use_container_width=True):
            st.session_state["_prefill"] = prompt
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
