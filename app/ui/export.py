from fpdf import FPDF


def _safe(text: str) -> str:
    """Strip characters not supported by FPDF built-in Latin-1 fonts."""
    return (text or "").encode("latin-1", errors="ignore").decode("latin-1")


def plan_to_pdf(plan: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()

    def h1(text: str) -> None:
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(21, 101, 192)
        pdf.multi_cell(0, 9, _safe(text), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def h2(text: str) -> None:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 136, 229)
        pdf.multi_cell(0, 7, _safe(text), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def h3(text: str) -> None:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 6, _safe(text), new_x="LMARGIN", new_y="NEXT")

    def body(text: str, color: tuple = (60, 60, 60)) -> None:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*color)
        pdf.multi_cell(0, 5, _safe(text), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def divider() -> None:
        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)

    # Title & intro
    h1(f"Travel Itinerary - {plan.get('destination', '')}")
    body(plan.get("intro", ""), color=(46, 125, 50))
    divider()

    # Budget estimate
    budget = plan.get("budget_estimate")
    if budget:
        h2("Budget Estimate")
        bcur = budget.get("currency", "USD")
        body(f"Budget:     {budget.get('per_day_low')} {bcur}/day")
        body(f"Mid-range:  {budget.get('per_day_mid')} {bcur}/day")
        body(f"Luxury:     {budget.get('per_day_high')} {bcur}/day")
        if budget.get("notes"):
            body(budget["notes"], color=(120, 120, 120))
        pdf.ln(2)

    # Packing list
    packing = plan.get("packing_list", [])
    if packing:
        h2("Packing List")
        for item in packing:
            body(f"  - {item}")
        pdf.ln(2)

    # Hotel areas
    hotel_areas = plan.get("hotel_areas", [])
    if hotel_areas:
        h2("Where to Stay")
        for area in hotel_areas:
            h3(f"{area.get('name', '')}  {area.get('price_range', '')}")
            body(area.get("why", ""), color=(100, 100, 100))
        pdf.ln(2)

    divider()

    # Days
    for day in plan.get("days", []):
        w = day.get("weather")
        wx = f"  |  {w.get('condition', '')} {w.get('max_temp_c')}C / {w.get('min_temp_c')}C" if w else ""
        h2(f"Day {day.get('day')} - {day.get('theme', '')}{wx}")

        for place in day.get("places", []):
            h3(place.get("name", ""))
            body(place.get("why", ""))
            if place.get("tip"):
                body(f"Tip: {place['tip']}", color=(46, 125, 50))
            meta = []
            if place.get("opening_hours"):
                meta.append(f"Open: {place['opening_hours']}")
            if place.get("walk_from_prev_min"):
                meta.append(f"{place['walk_from_prev_min']} min walk")
            if meta:
                body(" | ".join(meta), color=(144, 164, 174))
            pdf.ln(1)
        pdf.ln(2)

    # Bonus tip
    if plan.get("bonus_tip"):
        divider()
        h2("Local Tip")
        body(plan["bonus_tip"], color=(21, 101, 192))

    return bytes(pdf.output())


def plan_to_markdown(plan: dict) -> str:
    lines = [f"# {plan.get('destination', 'Travel Itinerary')}", ""]
    lines.append(plan.get("intro", ""))
    lines.append("")

    budget = plan.get("budget_estimate")
    if budget:
        cur = budget.get("currency", "USD")
        lines += [
            f"## Budget Estimate (per day, {cur})",
            f"- Budget: {budget.get('per_day_low')} {cur}",
            f"- Mid-range: {budget.get('per_day_mid')} {cur}",
            f"- Luxury: {budget.get('per_day_high')} {cur}",
        ]
        if budget.get("notes"):
            lines.append(f"_{budget['notes']}_")
        lines.append("")

    packing = plan.get("packing_list", [])
    if packing:
        lines.append("## Packing List")
        for item in packing:
            lines.append(f"- {item}")
        lines.append("")

    hotel_areas = plan.get("hotel_areas", [])
    if hotel_areas:
        lines.append("## Where to Stay")
        for area in hotel_areas:
            lines.append(f"- **{area.get('name')}** ({area.get('price_range', '')}) — {area.get('why', '')}")
        lines.append("")

    for day in plan.get("days", []):
        w = day.get("weather")
        wx = f" · {w.get('condition')} {w.get('max_temp_c')}°/{w.get('min_temp_c')}°C" if w else ""
        lines.append(f"## Day {day.get('day')} — {day.get('theme', '')}{wx}")
        for place in day.get("places", []):
            lines.append(f"### {place.get('name')}")
            lines.append(place.get("why", ""))
            if place.get("tip"):
                lines.append(f"_Tip: {place['tip']}_")
            meta = []
            if place.get("opening_hours"):
                meta.append(f"Open: {place['opening_hours']}")
            if place.get("walk_from_prev_min"):
                meta.append(f"{place['walk_from_prev_min']} min walk")
            if meta:
                lines.append(" · ".join(meta))
            lines.append("")

    if plan.get("bonus_tip"):
        lines += ["## Local Tip", plan["bonus_tip"]]

    return "\n".join(lines)
