import os
import json
import html
import re
from io import BytesIO
from datetime import date, datetime, time, timedelta
from pathlib import Path

from groq import Groq
import streamlit as st
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

if API_KEY:
    client = Groq(api_key=API_KEY)
else:
    client = None


SAVED_PLANS_FILE = Path(__file__).resolve().with_name("saved_plans.json")


st.set_page_config(page_title="Daily Planner Assistant", page_icon="🗓️", layout="centered")

st.title("Daily Planner Assistant")
st.caption("Turn your tasks into a realistic time-blocked schedule with Groq.")


for state_key, default_value in {
    "plan_generated": False,
    "last_plan": "",
    "last_inputs": None,
    "generate_requested": False,
    "regenerate_requested": False,
    "selected_date": date.today(),
    "past_plan_selection": "",
    "past_plan_selection_index": 0,
}.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value


def format_full_date(value: date) -> str:
    return f"{value.strftime('%A, %B')} {value.day}, {value.year}"


def set_selected_date(selected_date: date) -> None:
    st.session_state.selected_date = selected_date


today = date.today()
week_start = today - timedelta(days=today.weekday())
week_dates = [week_start + timedelta(days=offset) for offset in range(7)]
selected_date = st.session_state.selected_date
selected_date_label = format_full_date(selected_date)

st.markdown(
    f"<div style='font-size: 1.85rem; font-weight: 800; line-height: 1.2; margin-bottom: 0.35rem; color: #0f172a;'>{selected_date_label}</div>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div style='font-size: 0.95rem; font-weight: 700; color: #475569; margin-bottom: 0.5rem;'>This week</div>",
    unsafe_allow_html=True,
)

week_columns = st.columns(7)
for column, day in zip(week_columns, week_dates):
    is_selected = day == selected_date
    with column:
        st.button(
            f"{day.strftime('%a')}\n{day.day}",
            key=f"week_day_{day.isoformat()}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
            on_click=set_selected_date,
            args=(day,),
        )


def format_hour(value: time) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def build_prompt(
    tasks: str,
    start_hour: time,
    end_hour: time,
    energy_level: str,
    commitments: str,
    selected_date: date,
) -> str:
    selected_date_label = format_full_date(selected_date)
    return (
        f"Here is your plan for {selected_date_label}.\n\n"
        "You are a daily planner assistant. Given the user's tasks, available hours, "
        "energy level, and fixed commitments, create a realistic prioritized time-blocked schedule. "
        "Format it with clear time slots, task names, estimated durations, and a short note per task. "
        "Include short breaks. End with one motivational sentence.\n\n"
        f"Selected date: {selected_date_label}\n"
        f"User tasks:\n{tasks.strip()}\n\n"
        f"Available hours: {format_hour(start_hour)} to {format_hour(end_hour)}\n"
        f"Energy level: {energy_level}\n"
        f"Fixed commitments: {commitments.strip() or 'None'}\n\n"
        "Return only the schedule in a clean, readable format."
    )


def generate_plan(
    tasks: str,
    start_hour: time,
    end_hour: time,
    energy_level: str,
    commitments: str,
    selected_date: date,
) -> str:
    if not API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY in your .env file.")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a daily planner assistant."},
            {
                "role": "user",
                "content": build_prompt(tasks, start_hour, end_hour, energy_level, commitments, selected_date),
            },
        ],
        temperature=0.7,
    )

    generated_text = response.choices[0].message.content if response.choices else None
    if not generated_text:
        raise RuntimeError("Groq returned an empty response.")

    return generated_text.strip()


def request_generate() -> None:
    st.session_state.generate_requested = True


def request_regenerate() -> None:
    st.session_state.regenerate_requested = True


def load_saved_plans() -> list[dict]:
    if not SAVED_PLANS_FILE.exists():
        return []

    try:
        with SAVED_PLANS_FILE.open("r", encoding="utf-8") as file_handle:
            plans = json.load(file_handle)
    except (json.JSONDecodeError, OSError):
        return []

    return plans if isinstance(plans, list) else []


def save_saved_plans(plans: list[dict]) -> None:
    with SAVED_PLANS_FILE.open("w", encoding="utf-8") as file_handle:
        json.dump(plans, file_handle, ensure_ascii=False, indent=2)


def save_current_plan() -> None:
    if not st.session_state.last_plan or not st.session_state.last_inputs:
        return

    saved_plans = load_saved_plans()
    saved_plans.append(
        {
            "selected_date": st.session_state.last_inputs["selected_date"].isoformat(),
            "selected_date_label": format_full_date(st.session_state.last_inputs["selected_date"]),
            "tasks": st.session_state.last_inputs["tasks"],
            "energy_level": st.session_state.last_inputs["energy_level"],
            "fixed_commitments": st.session_state.last_inputs["fixed_commitments"],
            "generated_schedule": st.session_state.last_plan,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_saved_plans(saved_plans)


def delete_saved_plan(index: int) -> None:
    saved_plans = load_saved_plans()
    if 0 <= index < len(saved_plans):
        del saved_plans[index]
        save_saved_plans(saved_plans)


def get_downloads_folder() -> Path:
    downloads_folder = Path.home() / "Downloads"
    downloads_folder.mkdir(parents=True, exist_ok=True)
    return downloads_folder


def safe_pdf_filename(selected_date_value: date) -> str:
    return re.sub(r"[^a-z0-9]+", "_", format_full_date(selected_date_value).lower()).strip("_") + ".pdf"


def build_pdf_bytes(plan_data: dict[str, str]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Daily Planner Assistant",
        author="Daily Planner Assistant",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PlannerTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "PlannerSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "PlannerBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
    )
    body_bold_style = ParagraphStyle(
        "PlannerBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    note_style = ParagraphStyle(
        "PlannerNote",
        parent=body_style,
        fontName="Helvetica-Oblique",
        alignment=TA_CENTER,
    )
    footer_style = ParagraphStyle(
        "PlannerFooter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748b"),
    )

    story: list = [Paragraph(html.escape(plan_data["selected_date_label"]), title_style)]

    summary_rows = [
        [Paragraph("Date", body_bold_style), Paragraph(html.escape(plan_data["selected_date_label"]), body_style)],
        [Paragraph("Tasks", body_bold_style), Paragraph(html.escape(plan_data["tasks"]).replace("\n", "<br/>"), body_style)],
        [Paragraph("Energy level", body_bold_style), Paragraph(html.escape(plan_data["energy_level"]), body_style)],
        [Paragraph("Fixed commitments", body_bold_style), Paragraph(html.escape(plan_data["fixed_commitments"] or "None").replace("\n", "<br/>"), body_style)],
    ]
    summary_table = Table(summary_rows, colWidths=[1.4 * inch, 4.6 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbe4ef")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.extend([Paragraph("Summary", section_style), summary_table, Spacer(1, 12), Paragraph("Schedule", section_style)])

    schedule_blocks, motivational_sentence = parse_schedule_text(plan_data["generated_schedule"])
    for block in schedule_blocks:
        block_table = Table(
            [[
                Paragraph(f"🕗 <b>{html.escape(block['time_slot'])}</b>", body_style),
                Paragraph(
                    f"📌 <b>{html.escape(block['task_name'])}</b><br/><font size='8'>{html.escape(block['duration_text'])}</font>",
                    body_style,
                ),
                Paragraph(f"💡 <i>{html.escape(block['note_text'])}</i>", body_style),
            ]],
            colWidths=[1.5 * inch, 3.1 * inch, 1.4 * inch],
        )
        block_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbe4ef")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("SPACEBELOW", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.extend([block_table, Spacer(1, 6)])

    if motivational_sentence:
        story.extend([Spacer(1, 8), Paragraph(html.escape(motivational_sentence), note_style)])

    story.extend([Spacer(1, 14), Paragraph("Generated by Daily Planner Assistant", footer_style)])

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawCentredString(A4[0] / 2, 24, "Generated by Daily Planner Assistant")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def export_current_plan_to_pdf() -> Path:
    if not st.session_state.last_plan or not st.session_state.last_inputs:
        raise RuntimeError("No generated plan available to export.")

    pdf_data = build_pdf_bytes(
        {
            "selected_date_label": format_full_date(st.session_state.last_inputs["selected_date"]),
            "tasks": st.session_state.last_inputs["tasks"],
            "energy_level": st.session_state.last_inputs["energy_level"],
            "fixed_commitments": st.session_state.last_inputs["fixed_commitments"],
            "generated_schedule": st.session_state.last_plan,
        }
    )
    pdf_path = get_downloads_folder() / safe_pdf_filename(st.session_state.last_inputs["selected_date"])
    pdf_path.write_bytes(pdf_data)
    return pdf_path


def render_schedule_cards(plan_text: str, heading_label: str) -> None:
    schedule_blocks, motivational_sentence = parse_schedule_text(plan_text)

    st.markdown(
        """
        <style>
            .planner-card {
                background: #f8fafc;
                border: 1px solid #dbe4ef;
                border-radius: 18px;
                padding: 1rem 1rem 0.95rem 1rem;
                margin-bottom: 0.9rem;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
            }
            .planner-card-grid {
                display: grid;
                grid-template-columns: 1.1fr 1.6fr 1.2fr;
                gap: 0.9rem;
                align-items: start;
            }
            .planner-meta {
                font-size: 0.95rem;
                line-height: 1.45;
                color: #0f172a;
            }
            .planner-meta strong {
                display: block;
                margin-bottom: 0.25rem;
                font-size: 1rem;
                color: #0f172a;
            }
            .planner-duration {
                display: block;
                margin-top: 0.35rem;
                font-size: 0.82rem;
                color: #64748b;
            }
            .planner-note {
                font-style: italic;
                color: #334155;
                line-height: 1.5;
            }
            .planner-footer {
                margin-top: 1.15rem;
                text-align: center;
                font-weight: 700;
                color: #0f172a;
            }
            @media (max-width: 700px) {
                .planner-card-grid {
                    grid-template-columns: 1fr;
                    gap: 0.65rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="text-align:center; font-size: 1rem; font-weight: 800; color: #0f172a; margin: 0.75rem 0 1rem 0;">{heading_label}</div>',
        unsafe_allow_html=True,
    )

    for block in schedule_blocks:
        st.markdown(
            f"""
            <div class="planner-card">
                <div class="planner-card-grid">
                    <div class="planner-meta">🕗 <strong>{block['time_slot']}</strong></div>
                    <div class="planner-meta">📌 <strong>{block['task_name']}</strong><span class="planner-duration">{block['duration_text']}</span></div>
                    <div class="planner-meta">💡 <span class="planner-note">{block['note_text']}</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if motivational_sentence:
        st.markdown(f'<div class="planner-footer">{motivational_sentence}</div>', unsafe_allow_html=True)


def parse_schedule_text(plan_text: str) -> tuple[list[dict[str, str]], str]:
    blocks: list[dict[str, str]] = []
    closing_line = ""

    for raw_line in [line.strip() for line in plan_text.splitlines() if line.strip()]:
        cleaned_line = raw_line.lstrip("-•*").strip()

        if not cleaned_line:
            continue

        if not closing_line and len(blocks) > 0 and not any(char.isdigit() for char in cleaned_line[:12]):
            closing_line = cleaned_line
            continue

        time_slot = ""
        task_name = cleaned_line
        duration_text = ""
        note_text = ""

        if "|" in cleaned_line:
            parts = [part.strip() for part in cleaned_line.split("|")]
            if parts:
                time_slot = parts[0]
            if len(parts) > 1:
                task_name = parts[1]
            if len(parts) > 2:
                duration_text = parts[2]
            if len(parts) > 3:
                note_text = " | ".join(parts[3:])
        else:
            first_dash = cleaned_line.find(" - ")
            if first_dash != -1:
                time_slot = cleaned_line[:first_dash].strip()
                remainder = cleaned_line[first_dash + 3 :].strip()
            else:
                remainder = cleaned_line

            duration_markers = ["Duration:", "Estimated duration:", "Note:"]
            split_index = -1
            for marker in duration_markers:
                marker_index = remainder.find(marker)
                if marker_index != -1:
                    split_index = marker_index
                    break

            if split_index != -1:
                task_name = remainder[:split_index].strip()
                trailing_text = remainder[split_index:].strip()
                pieces = [piece.strip() for piece in trailing_text.split("|")]
                if pieces:
                    duration_text = pieces[0]
                if len(pieces) > 1:
                    note_text = " | ".join(pieces[1:])
            else:
                task_name = remainder

        if not time_slot and not any(char.isdigit() for char in cleaned_line[:12]) and not blocks:
            note_text = cleaned_line
            continue

        blocks.append(
            {
                "time_slot": time_slot or "Scheduled block",
                "task_name": task_name or "Task",
                "duration_text": duration_text or "Duration varies",
                "note_text": note_text or "Stay focused and keep the momentum going.",
            }
        )

    if blocks and not closing_line:
        closing_line = blocks[-1]["note_text"]

    return blocks, closing_line


tasks = st.text_area(
    "Tasks for the day",
    placeholder="Example: finish project outline, reply to emails, exercise, grocery shopping, read 30 minutes",
    height=180,
)

time_col_1, time_col_2 = st.columns(2)
with time_col_1:
    start_hour = st.time_input("Available start hour", value=time(8, 0))
with time_col_2:
    end_hour = st.time_input("Available end hour", value=time(17, 0))

energy_level = st.selectbox("Energy level", ["High", "Medium", "Low"])
fixed_commitments = st.text_input("Fixed commitments (optional)", placeholder="Example: team meeting at 11:00 AM")

st.button("Generate My Plan", type="primary", on_click=request_generate)

should_generate = st.session_state.generate_requested or st.session_state.regenerate_requested

if should_generate:
    if not tasks.strip():
        st.error("Please enter at least one task for the day.")
        st.session_state.generate_requested = False
        st.session_state.regenerate_requested = False
    elif start_hour >= end_hour:
        st.error("The end hour must be later than the start hour.")
        st.session_state.generate_requested = False
        st.session_state.regenerate_requested = False
    else:
        try:
            with st.spinner("Creating your schedule..."):
                plan = generate_plan(tasks, start_hour, end_hour, energy_level, fixed_commitments, selected_date)

            st.session_state.last_inputs = {
                "tasks": tasks,
                "start_hour": start_hour,
                "end_hour": end_hour,
                "energy_level": energy_level,
                "fixed_commitments": fixed_commitments,
                "selected_date": selected_date,
            }
            st.session_state.last_plan = plan
            st.session_state.plan_generated = True
            st.session_state.generate_requested = False
            st.session_state.regenerate_requested = False
        except Exception as exc:
            st.error(f"Unable to generate a plan: {exc}")
            st.session_state.generate_requested = False
            st.session_state.regenerate_requested = False


st.subheader("Your Time-Blocked Schedule")

if st.session_state.last_plan:
    render_schedule_cards(st.session_state.last_plan, f"Here is your plan for {selected_date_label}")

    action_col_1, action_col_2 = st.columns(2)
    with action_col_1:
        st.button("Save Plan", use_container_width=True, on_click=save_current_plan)
    with action_col_2:
        export_clicked = st.button("Export to PDF", use_container_width=True)
        if export_clicked:
            try:
                pdf_path = export_current_plan_to_pdf()
                st.success(f"PDF saved to {pdf_path}")
            except Exception as exc:
                st.error(f"Unable to export PDF: {exc}")
else:
    st.info("Your AI-generated schedule will appear here after you click Generate My Plan.")


if st.session_state.plan_generated:
    st.button("Regenerate", on_click=request_regenerate)


st.subheader("Past Plans")

saved_plans = load_saved_plans()

if not saved_plans:
    st.info("No saved plans yet — generate and save your first plan!")
else:
    saved_plan_options = [
        f"{plan.get('selected_date_label', plan.get('selected_date', 'Unknown date'))} • Saved {datetime.fromisoformat(plan.get('saved_at')).strftime('%b %d, %I:%M %p') if plan.get('saved_at') else 'Unknown time'}"
        for plan in saved_plans
    ]

    max_index = len(saved_plan_options) - 1
    current_index = st.session_state.past_plan_selection_index
    if current_index > max_index:
        current_index = 0
    if current_index < 0:
        current_index = 0

    selected_saved_label = st.selectbox(
        "Choose a saved plan",
        saved_plan_options,
        index=current_index,
        key="past_plan_selection",
    )

    st.session_state.past_plan_selection_index = saved_plan_options.index(selected_saved_label)

    selected_saved_plan = saved_plans[st.session_state.past_plan_selection_index]
    saved_plan_heading = selected_saved_plan.get("selected_date_label", selected_saved_plan.get("selected_date", "Saved plan"))

    header_col, delete_col = st.columns([0.8, 0.2])
    with header_col:
        st.markdown(
            f'<div style="font-size: 1rem; font-weight: 800; color: #0f172a; margin: 0.5rem 0 0.75rem 0;">{saved_plan_heading}</div>',
            unsafe_allow_html=True,
        )
    with delete_col:
        if st.button("Delete Plan", key=f"delete_saved_plan_{st.session_state.past_plan_selection_index}"):
            delete_saved_plan(st.session_state.past_plan_selection_index)
            st.session_state.past_plan_selection_index = 0
            st.rerun()

    render_schedule_cards(
        selected_saved_plan.get("generated_schedule", ""),
        f"Here is your plan for {saved_plan_heading}",
    )
