"""
Generate a detailed PDF technical report for the Personal Finance Manager project.
Run: python generate_report.py
Output: Project_Report.pdf
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)
from reportlab.lib import colors

import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Project_Report.pdf")

# ─── Colors ──────────────────────────────────────────────────────────────────
PRIMARY = HexColor("#6366f1")
PRIMARY_LIGHT = HexColor("#e0e7ff")
DARK = HexColor("#1e293b")
MUTED = HexColor("#64748b")
GREEN = HexColor("#10b981")
ORANGE = HexColor("#f59e0b")
RED = HexColor("#ef4444")
BLUE = HexColor("#3b82f6")
BG_LIGHT = HexColor("#f8fafc")
BORDER = HexColor("#e2e8f0")

# ─── Styles ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    "CoverTitle", parent=styles["Title"], fontSize=28, leading=34,
    textColor=DARK, alignment=TA_CENTER, spaceAfter=6,
))
styles.add(ParagraphStyle(
    "CoverSubtitle", parent=styles["Normal"], fontSize=14, leading=18,
    textColor=MUTED, alignment=TA_CENTER, spaceAfter=30,
))
styles.add(ParagraphStyle(
    "SectionHeading", parent=styles["Heading1"], fontSize=18, leading=24,
    textColor=PRIMARY, spaceBefore=24, spaceAfter=10,
    borderPadding=(0, 0, 4, 0),
))
styles.add(ParagraphStyle(
    "SubHeading", parent=styles["Heading2"], fontSize=13, leading=17,
    textColor=DARK, spaceBefore=16, spaceAfter=6,
))
styles.add(ParagraphStyle(
    "BodyText", parent=styles["Normal"], fontSize=10, leading=15,
    textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=8,
))
styles.add(ParagraphStyle(
    "BulletText", parent=styles["Normal"], fontSize=10, leading=15,
    textColor=DARK, leftIndent=20, spaceAfter=4,
    bulletIndent=8, bulletFontSize=10,
))
styles.add(ParagraphStyle(
    "CodeText", parent=styles["Normal"], fontSize=8.5, leading=12,
    fontName="Courier", textColor=DARK, leftIndent=12,
    spaceAfter=4, backColor=BG_LIGHT,
))
styles.add(ParagraphStyle(
    "SmallMuted", parent=styles["Normal"], fontSize=8.5, leading=11,
    textColor=MUTED, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    "TableHeader", parent=styles["Normal"], fontSize=9, leading=12,
    textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    "TableCell", parent=styles["Normal"], fontSize=9, leading=12,
    textColor=DARK,
))
styles.add(ParagraphStyle(
    "TableCellCenter", parent=styles["Normal"], fontSize=9, leading=12,
    textColor=DARK, alignment=TA_CENTER,
))


def heading(text):
    return Paragraph(text, styles["SectionHeading"])


def subheading(text):
    return Paragraph(text, styles["SubHeading"])


def body(text):
    return Paragraph(text, styles["BodyText"])


def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", styles["BulletText"])


def code(text):
    return Paragraph(text, styles["CodeText"])


def divider():
    return HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10, spaceBefore=10)


def make_table(headers, rows, col_widths=None):
    """Create a styled table."""
    header_row = [Paragraph(h, styles["TableHeader"]) for h in headers]
    data_rows = []
    for row in rows:
        data_rows.append([Paragraph(str(c), styles["TableCell"]) for c in row])

    table = Table([header_row] + data_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))
    return table


def info_box(text):
    """Create an info box with light background."""
    t = Table([[Paragraph(text, styles["BodyText"])]], colWidths=[460])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_LIGHT),
        ("BORDER", (0, 0), (-1, -1), 1, PRIMARY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


# ─── Build Document ──────────────────────────────────────────────────────────

def build_report():
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    story = []
    W = doc.width

    # ═══════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 80))
    story.append(Paragraph("Personal Finance Manager", styles["CoverTitle"]))
    story.append(Paragraph("Multi-Agent System", styles["CoverTitle"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="40%", thickness=3, color=PRIMARY, spaceAfter=16))
    story.append(Paragraph("Detailed Technical Report", styles["CoverSubtitle"]))
    story.append(Spacer(1, 40))

    cover_info = [
        ["Module", "Module 7 - Agentic & Multi-Agent Systems"],
        ["Assignment", "Personal Finance Manager Agent"],
        ["Framework", "CrewAI + Flask + LiteLLM"],
        ["LLM Provider", "Groq (Llama 3.3 70B Versatile)"],
        ["Language", "Python 3.11"],
        ["Author", "Shahrukh Khan"],
    ]
    cover_table = Table(
        [[Paragraph(f"<b>{r[0]}</b>", styles["TableCell"]),
          Paragraph(r[1], styles["TableCell"])] for r in cover_info],
        colWidths=[120, 340],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BG_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(cover_table)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("Table of Contents"))
    story.append(Spacer(1, 6))
    toc_items = [
        "1. Project Overview",
        "2. System Architecture",
        "3. Project Structure (File Tree)",
        "4. Part 1 - Agent Fundamentals & Single-Agent Patterns",
        "5. Part 2 - Tool Use & Function Calling (5 Tools)",
        "6. Part 3 - Multi-Agent Collaboration Patterns",
        "7. Part 4 - Memory System (Short-term & Long-term)",
        "8. Flask Web Dashboard (UI Layer)",
        "9. Rate Limiting & Groq Integration",
        "10. Testing Strategy",
        "11. Data Flow Walkthrough (End to End)",
        "12. Tech Stack Summary",
    ]
    for item in toc_items:
        story.append(body(f"<b>{item}</b>"))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # 1. PROJECT OVERVIEW
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("1. Project Overview"))
    story.append(body(
        "This project implements a <b>multi-agent personal finance management system</b> "
        "that uses three AI agents collaborating together to help users track expenses, "
        "analyze budgets, and receive personalized financial advice. The system is built "
        "with <b>CrewAI</b> as the multi-agent orchestration framework, <b>Groq</b> as the "
        "LLM provider (Llama 3.3 70B), and <b>Flask</b> for the web dashboard UI."
    ))
    story.append(body(
        "The system demonstrates four key concepts from agentic AI: "
        "<b>(1)</b> Agent Fundamentals with ReAct, Planning, and Reflection patterns; "
        "<b>(2)</b> Tool Use where agents call Python functions to analyze financial data; "
        "<b>(3)</b> Multi-Agent Collaboration through sequential and hierarchical workflows; "
        "<b>(4)</b> Agent Memory with short-term (session) and long-term (persistent) memory systems."
    ))
    story.append(info_box(
        "<b>Key Outcome:</b> When the user runs the system, three agents work in sequence "
        "- the Expense Tracker analyzes transactions, the Budget Analyzer checks spending "
        "against limits, and the Financial Advisor synthesizes everything into actionable "
        "advice with specific dollar amounts and timelines."
    ))
    story.append(Spacer(1, 4))

    # ═══════════════════════════════════════════════════════════════════════
    # 2. SYSTEM ARCHITECTURE
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("2. System Architecture"))
    story.append(body(
        "The system follows a layered architecture with clear separation of concerns. "
        "Here is how each layer works and connects:"
    ))
    story.append(subheading("2.1 Architecture Layers"))

    arch_rows = [
        ["Presentation Layer", "Flask (app.py), Jinja2 Templates, Bootstrap 5, Chart.js",
         "Renders the web dashboard, handles user input (add expense, run analysis), shows charts and budget cards."],
        ["Orchestration Layer", "CrewAI (main.py), LiteLLM",
         "Manages agents, assigns tasks, runs sequential/hierarchical workflows, handles LLM communication."],
        ["Agent Layer", "3 Agent files (agents/ folder)",
         "Each agent has a role, goal, backstory, and assigned tools. Agents reason using the LLM and call tools."],
        ["Tool Layer", "5 Tool functions (tools/financial_tools.py)",
         "Pure Python functions decorated with @tool. Each reads JSON data, computes results, returns JSON strings."],
        ["Memory Layer", "MemoryManager (memory/memory_system.py)",
         "Short-term memory for session state. Long-term memory for persistent data. File-based JSON storage."],
        ["Data Layer", "JSON files (data/ folder)",
         "sample_expenses.json (transactions), user_profile.json (budgets/goals), categories.json (metadata)."],
    ]
    story.append(make_table(
        ["Layer", "Components", "Responsibility"],
        arch_rows,
        col_widths=[95, 150, 225],
    ))
    story.append(Spacer(1, 8))

    story.append(subheading("2.2 How a Request Flows Through the System"))
    flow_steps = [
        "<b>User opens Dashboard</b> (GET /) - Flask loads expense data from JSON files, calls each tool's check_budget_status function, computes chart data, and renders the dashboard.html template.",
        "<b>User adds an expense</b> (POST /add-expense) - Flask validates the form, appends the expense to sample_expenses.json, saves memory, and redirects to the dashboard.",
        "<b>User runs AI Analysis</b> (POST /api/run-analysis) - Flask spawns a background thread that calls main.py's run_sequential() or run_hierarchical(). This initializes the LLM, creates agents, assigns tasks, and CrewAI orchestrates the full pipeline. The frontend polls /api/analysis-status every 5 seconds until the result is ready.",
        "<b>Agent executes a task</b> - CrewAI sends the task description + tool schemas to the LLM. The LLM reasons about what to do (ReAct pattern), decides which tool to call, CrewAI executes the tool, and returns the result to the LLM. This loop repeats until the agent produces a final answer.",
    ]
    for i, step in enumerate(flow_steps, 1):
        story.append(bullet(f"<b>Step {i}:</b> {step}"))
    story.append(Spacer(1, 4))

    # ═══════════════════════════════════════════════════════════════════════
    # 3. PROJECT STRUCTURE
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("3. Project Structure"))
    story.append(body("The project is organized into well-separated modules:"))

    tree_rows = [
        ["app.py", "Flask web application with 6 routes (dashboard, add expense, analysis, APIs)"],
        ["main.py", "CLI entry point + CrewAI orchestration (lazy init, sequential/hierarchical workflows)"],
        ["agents/__init__.py", "Re-exports all 3 agent factory functions"],
        ["agents/expense_tracker.py", "Expense Tracker Agent - ReAct + Planning patterns"],
        ["agents/budget_analyzer.py", "Budget Analyzer Agent - ReAct + Reflection patterns"],
        ["agents/financial_advisor.py", "Financial Advisor Agent - Planning + Hierarchical patterns"],
        ["tools/__init__.py", "Re-exports all 5 tool functions"],
        ["tools/financial_tools.py", "5 @tool-decorated functions + helper functions (_load_expenses, etc.)"],
        ["memory/__init__.py", "Re-exports ShortTermMemory, LongTermMemory, MemoryManager"],
        ["memory/memory_system.py", "Full memory system with persistence (save/load JSON)"],
        ["memory/storage/", "Auto-created directory for persisted long_term_memory.json"],
        ["data/sample_expenses.json", "25+ mock transactions across 5 categories"],
        ["data/user_profile.json", "User income ($5000), budget limits, financial goals, preferences"],
        ["data/categories.json", "Category definitions with subcategories"],
        ["templates/base.html", "Base layout - Bootstrap 5, Chart.js, Font Awesome CDN links, navbar"],
        ["templates/dashboard.html", "Dashboard - budget cards, charts, goals, transactions table"],
        ["templates/add_expense.html", "Add expense form with validation"],
        ["templates/analysis.html", "AI analysis page with background processing + polling"],
        ["static/css/style.css", "Custom CSS - gradients, card styles, progress bars, responsive design"],
        ["tests/test_tools.py", "13 tests for all 5 financial tools"],
        ["tests/test_memory.py", "15 tests for the memory system"],
    ]
    story.append(make_table(
        ["File", "Purpose"],
        tree_rows,
        col_widths=[155, 315],
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # 4. PART 1 - AGENT FUNDAMENTALS
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("4. Part 1 - Agent Fundamentals & Single-Agent Patterns"))
    story.append(body(
        "Three core agents are defined in the <b>agents/</b> folder. Each agent is a CrewAI "
        "<b>Agent</b> object with a role, goal, backstory, assigned tools, and an LLM. "
        "The backstory tells the LLM how to behave and which agentic pattern to use."
    ))

    story.append(subheading("4.1 Expense Tracker Agent"))
    story.append(body(
        "<b>File:</b> agents/expense_tracker.py<br/>"
        "<b>Role:</b> Expense Tracker<br/>"
        "<b>Pattern:</b> ReAct (Reason + Act) and Planning<br/>"
        "<b>Tools:</b> calculate_category_total, check_budget_status, generate_spending_report<br/>"
        "<b>allow_delegation:</b> False (works independently)"
    ))
    story.append(body(
        "<b>How ReAct works internally:</b> When CrewAI sends this agent a task, the LLM first "
        "<i>reasons</i> about what information it needs ('I need to generate a spending report for March 2026'). "
        "Then it <i>acts</i> by outputting a tool call (generate_spending_report with the date range). "
        "CrewAI intercepts this, executes the tool, and returns the JSON result. The LLM <i>observes</i> "
        "the result and decides whether to call another tool or produce a final answer. This Reason-Act-Observe "
        "loop continues until the agent has enough data to answer."
    ))
    story.append(body(
        "<b>How Planning works:</b> The task description explicitly tells the agent to follow a step-by-step plan: "
        "(1) Generate spending report, (2) Calculate totals per category, (3) Flag anomalies, (4) Summarize. "
        "The LLM follows these steps in order, ensuring thorough analysis."
    ))

    story.append(subheading("4.2 Budget Analyzer Agent"))
    story.append(body(
        "<b>File:</b> agents/budget_analyzer.py<br/>"
        "<b>Role:</b> Budget Analyzer<br/>"
        "<b>Pattern:</b> ReAct and Reflection<br/>"
        "<b>Tools:</b> check_budget_status, predict_month_end_spending, generate_spending_report<br/>"
        "<b>allow_delegation:</b> False"
    ))
    story.append(body(
        "<b>How Reflection works internally:</b> After the agent completes its initial analysis "
        "(checking all 5 category budgets), the task description instructs it to 'REFLECT: re-examine your "
        "findings'. This causes the LLM to critically review its own output - checking if percentages are "
        "correct, if it missed borderline categories, and if its prioritization makes sense. The agent may "
        "call tools again to verify its calculations. This self-critique step improves accuracy."
    ))

    story.append(subheading("4.3 Financial Advisor Agent"))
    story.append(body(
        "<b>File:</b> agents/financial_advisor.py<br/>"
        "<b>Role:</b> Financial Advisor<br/>"
        "<b>Pattern:</b> Planning and Hierarchical Coordination<br/>"
        "<b>Tools:</b> check_budget_status, predict_month_end_spending, find_savings_opportunities, generate_spending_report<br/>"
        "<b>allow_delegation:</b> True (can delegate to other agents)"
    ))
    story.append(body(
        "<b>How Hierarchical Coordination works:</b> This agent has <b>allow_delegation=True</b>, "
        "meaning it can ask other agents to perform sub-tasks. In the hierarchical workflow "
        "(run_hierarchical in main.py), only this agent receives a task - it then coordinates the full "
        "review by calling tools itself and synthesizing all insights into one comprehensive report."
    ))
    story.append(Spacer(1, 4))

    # ═══════════════════════════════════════════════════════════════════════
    # 5. PART 2 - TOOLS
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("5. Part 2 - Tool Use & Function Calling"))
    story.append(body(
        "All 5 tools are defined in <b>tools/financial_tools.py</b>. Each is a regular Python function "
        "decorated with CrewAI's <b>@tool</b> decorator. This decorator registers the function's name, "
        "description, and parameter schema so the LLM can call it. Every tool reads data from JSON files "
        "and returns a JSON string."
    ))

    story.append(subheading("5.1 How Tool Calling Works Internally"))
    tool_flow = [
        "CrewAI sends the agent's system prompt + task description + <b>tool schemas</b> (name, description, parameters) to the LLM via the Groq API.",
        "The LLM outputs a structured <b>tool call</b> - e.g., {\"tool\": \"check_budget_status\", \"args\": {\"category\": \"food\"}}.",
        "CrewAI's executor intercepts this, finds the matching Python function, and calls it with the provided arguments.",
        "The Python function reads sample_expenses.json, computes the result, and returns a JSON string.",
        "CrewAI sends this result back to the LLM as a 'tool result' message.",
        "The LLM decides to call another tool or produce its final answer.",
    ]
    for i, step in enumerate(tool_flow, 1):
        story.append(bullet(f"<b>{i}.</b> {step}"))

    story.append(subheading("5.2 Tool Details"))
    tool_rows = [
        ["1. calculate_category_total",
         "category, start_date, end_date",
         "Filters expenses by category and date range, sums amounts. Returns total, count, and transaction list."],
        ["2. check_budget_status",
         "category",
         "Loads budget limits from user_profile.json. Computes percentage used. Returns status: HEALTHY / ON_TRACK / WARNING / OVER_BUDGET."],
        ["3. predict_month_end_spending",
         "category",
         "Calculates daily burn rate (total spent / days elapsed). Projects month-end total. Returns forecast: WITHIN_BUDGET / AT_RISK / WILL_EXCEED_BUDGET."],
        ["4. find_savings_opportunities",
         "spending_data ('all' or category)",
         "Finds overspending categories (>90% of budget). Detects frequent small purchases. Checks discretionary spending ratio. Returns opportunities with dollar amounts."],
        ["5. generate_spending_report",
         "date_range ('YYYY-MM-DD to YYYY-MM-DD')",
         "Full report: per-category breakdown, budget comparison, top 5 expenses, daily average, savings rate."],
    ]
    story.append(make_table(
        ["Tool", "Parameters", "What It Computes"],
        tool_rows,
        col_widths=[135, 105, 230],
    ))

    story.append(Spacer(1, 6))
    story.append(subheading("5.3 Key Helper Function: _get_latest_month()"))
    story.append(body(
        "A critical design decision: the tools use <b>_get_latest_month(expenses)</b> instead of "
        "<b>datetime.now()</b> to determine which month to analyze. This function finds the most recent "
        "transaction date in the data and derives the month start, days in month, and days elapsed. "
        "This prevents the bug where tools return zero spending because today's date is in a different "
        "month than the expense data."
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # 6. PART 3 - MULTI-AGENT COLLABORATION
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("6. Part 3 - Multi-Agent Collaboration"))
    story.append(body(
        "The system implements two collaboration patterns, both defined in <b>main.py</b>. "
        "CrewAI's <b>Crew</b> class orchestrates the agents by assigning tasks, managing context passing, "
        "and collecting results."
    ))

    story.append(subheading("6.1 Pattern 1: Sequential Execution (run_sequential)"))
    story.append(body(
        "In the sequential pipeline, three agents run one after another. Each agent's output "
        "automatically becomes part of the next agent's context."
    ))
    seq_rows = [
        ["Step 1", "Expense Tracker", "Calls generate_spending_report + calculate_category_total. Produces expense summary with totals per category and flagged anomalies."],
        ["Step 2", "Budget Analyzer", "Receives expense summary as context. Calls check_budget_status for each category. Calls predict_month_end_spending for at-risk categories. Reflects on findings."],
        ["Step 3", "Financial Advisor", "Receives both previous outputs as context. Calls find_savings_opportunities. Synthesizes everything into savings tips, budget adjustments, and goal progress."],
    ]
    story.append(make_table(
        ["Step", "Agent", "What Happens"],
        seq_rows,
        col_widths=[45, 100, 325],
    ))
    story.append(Spacer(1, 6))

    story.append(body(
        "<b>How context passing works internally:</b> CrewAI stores each task's output in a "
        "<b>TaskOutput</b> object. When running sequentially, the output of task N is automatically "
        "appended to the prompt of task N+1 as 'context from previous tasks'. This is how the Budget "
        "Analyzer knows about the expense summary without being explicitly told."
    ))

    story.append(subheading("6.2 Pattern 2: Hierarchical Coordination (run_hierarchical)"))
    story.append(body(
        "In the hierarchical pattern, only the <b>Financial Advisor</b> receives a task. It acts as the "
        "manager and performs the full analysis itself using all 4 of its assigned tools. This produces "
        "a single comprehensive report. The advantage is a unified narrative; the disadvantage is that "
        "one agent does all the work."
    ))

    story.append(subheading("6.3 Agent Communication via Shared Memory"))
    story.append(body(
        "Beyond CrewAI's built-in context passing, agents also communicate through the "
        "<b>MemoryManager</b>. When the workflow starts, main.py logs a 'workflow_started' event. "
        "When it completes, it logs 'workflow_completed'. The MemoryManager's get_full_context() "
        "method provides a unified view of budget limits, goals, and preferences that is injected "
        "into every task description. This shared context ensures all agents work with the same data."
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # 7. PART 4 - MEMORY SYSTEM
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("7. Part 4 - Memory System"))
    story.append(body(
        "The memory system is defined in <b>memory/memory_system.py</b> and consists of three classes: "
        "<b>ShortTermMemory</b>, <b>LongTermMemory</b>, and <b>MemoryManager</b> (the coordinator)."
    ))

    story.append(subheading("7.1 ShortTermMemory"))
    stm_rows = [
        ["conversation_context", "list[dict]", "Last 20 agent interactions with role, message, and timestamp. Used to track what happened during a session."],
        ["recent_transactions", "list[dict]", "Transactions from the last 7 days. Auto-loaded on init by filtering sample_expenses.json."],
        ["active_alerts", "list[dict]", "Budget warnings/critical alerts. Each has category, message, severity, timestamp."],
        ["calculation_results", "dict[str, Any]", "Temporary key-value store for intermediate calculations between agent calls."],
    ]
    story.append(make_table(
        ["Attribute", "Type", "Purpose"],
        stm_rows,
        col_widths=[120, 80, 270],
    ))
    story.append(Spacer(1, 6))

    story.append(subheading("7.2 LongTermMemory"))
    story.append(body(
        "Long-term memory loads data from two sources on initialization:"
    ))
    story.append(bullet("<b>Data files</b> (data/): user_profile.json for income, budgets, goals; sample_expenses.json for all transactions."))
    story.append(bullet("<b>Persisted memory</b> (memory/storage/long_term_memory.json): Runtime additions from previous sessions - new transactions, updated goals, changed preferences."))

    story.append(body(
        "<b>How persistence works:</b> When save() is called, LongTermMemory compares the current "
        "spending_history against the original sample_expenses.json. Any transactions NOT in the original "
        "file are saved as 'additional_transactions' in long_term_memory.json. On next load, these are "
        "merged back. This design keeps the original data files clean while allowing runtime additions."
    ))

    story.append(subheading("7.3 MemoryManager (Coordinator)"))
    story.append(body(
        "MemoryManager creates both memory objects and provides high-level methods: "
        "<b>add_expense()</b> writes to both memories; "
        "<b>check_budget_alert()</b> compares spending against thresholds; "
        "<b>log_interaction()</b> records agent events; "
        "<b>get_full_context()</b> returns a unified dict for agent prompts; "
        "<b>save_all()</b> persists everything to disk."
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # 8. FLASK WEB DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("8. Flask Web Dashboard"))
    story.append(body(
        "The web UI is defined in <b>app.py</b> with 6 routes. It uses Jinja2 templates extending "
        "a base layout with Bootstrap 5, Chart.js, and Font Awesome."
    ))

    routes_rows = [
        ["GET /", "dashboard()", "Loads all data, computes budget statuses by calling check_budget_status tool for each category, renders interactive dashboard."],
        ["GET /add-expense", "add_expense()", "Renders the expense form with category dropdown, date picker, amount input."],
        ["POST /add-expense", "add_expense()", "Validates form data, appends to sample_expenses.json, saves memory, redirects to dashboard with flash message."],
        ["GET /analysis", "analysis()", "Renders the AI analysis page with agent descriptions and run buttons."],
        ["POST /api/run-analysis", "run_analysis()", "Accepts JSON {pattern: 'sequential'|'hierarchical'}. Spawns background thread running CrewAI pipeline. Returns task_id."],
        ["GET /api/analysis-status/&lt;id&gt;", "analysis_status()", "Returns JSON {status, result, error}. Frontend polls this every 5 seconds."],
    ]
    story.append(make_table(
        ["Route", "Function", "What It Does"],
        routes_rows,
        col_widths=[120, 95, 255],
    ))
    story.append(Spacer(1, 6))

    story.append(subheading("8.1 Dashboard Internals"))
    story.append(body(
        "The dashboard route does NOT use the LLM. It calls the tool functions directly: "
        "json.loads(check_budget_status.run(category='food')) returns a Python dict with total_spent, "
        "percentage_used, status, etc. This is fast (no API calls) and provides real-time data."
    ))
    story.append(body(
        "Chart.js renders an interactive doughnut/bar chart. The chart data is injected into the template "
        "as a JSON object via {{ chart_data | tojson }}. Users can toggle between chart types."
    ))

    story.append(subheading("8.2 Background Analysis (Threading)"))
    story.append(body(
        "When the user clicks 'Run Sequential Analysis', JavaScript sends a POST to /api/run-analysis. "
        "Flask creates a UUID task ID, stores it in the analysis_tasks dict with status='running', "
        "and spawns a daemon thread that imports and calls run_sequential() from main.py. "
        "The frontend polls /api/analysis-status/<id> every 5 seconds. When status becomes 'complete', "
        "the result is displayed in a formatted card. If it's 'error', a friendly message is shown "
        "(with special handling for Groq rate limit errors)."
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # 9. RATE LIMITING
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("9. Rate Limiting & Groq Integration"))
    story.append(body(
        "Groq's free tier allows only <b>12,000 tokens per minute</b> (TPM). A single agent task uses "
        "~2,000-3,000 tokens per LLM call, and each agent makes 2-4 calls. Without rate limiting, "
        "the system would exhaust the quota within seconds."
    ))
    story.append(subheading("9.1 Rate Limiter Implementation"))
    story.append(body(
        "In main.py, the system <b>monkey-patches litellm.completion</b> with a wrapper function. "
        "Before each LLM call, the wrapper checks if 15 seconds have passed since the last call. "
        "If not, it sleeps for the remaining time. This ensures at most 4 calls per minute, "
        "staying within the 12K TPM limit. Additionally, litellm.num_retries=5 and "
        "litellm.retry_after=20 provide fallback retry logic."
    ))
    story.append(body(
        "<b>LLM Configuration:</b> model='groq/llama-3.3-70b-versatile', temperature=0.3, "
        "max_tokens=1024. The low temperature ensures consistent, factual output. "
        "max_tokens=1024 keeps responses concise to reduce token usage."
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # 10. TESTING
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("10. Testing Strategy"))
    story.append(body(
        "The project includes <b>28 tests</b> in the tests/ folder, covering all tools and the memory system. "
        "Tests run with: <b>python -m pytest tests/ -v</b>"
    ))

    test_rows = [
        ["test_tools.py", "TestCalculateCategoryTotal", "3", "Tests food category total, empty date range, and all categories having data."],
        ["test_tools.py", "TestCheckBudgetStatus", "2", "Tests valid status return and all 5 categories."],
        ["test_tools.py", "TestPredictMonthEndSpending", "2", "Tests projection output and positive days."],
        ["test_tools.py", "TestFindSavingsOpportunities", "2", "Tests 'all' scope and single category."],
        ["test_tools.py", "TestGenerateSpendingReport", "2", "Tests March report completeness and all categories present."],
        ["test_memory.py", "TestShortTermMemory", "6", "Conversation entries, 20-entry limit, alerts, calculations, context summary."],
        ["test_memory.py", "TestLongTermMemory", "6", "Profile loading, spending history, category filter, transactions, goals, save/reload."],
        ["test_memory.py", "TestMemoryManager", "5", "Init, add_expense, full_context, log_interaction, save_all."],
    ]
    story.append(make_table(
        ["File", "Test Class", "Count", "What Is Tested"],
        test_rows,
        col_widths=[85, 130, 35, 220],
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # 11. END-TO-END DATA FLOW
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("11. Data Flow Walkthrough (End to End)"))
    story.append(body(
        "Here is a complete walkthrough of what happens when a user clicks "
        "'<b>Run Sequential Analysis</b>' on the web dashboard:"
    ))

    e2e_steps = [
        "<b>Browser</b> sends POST /api/run-analysis with {\"pattern\": \"sequential\"}.",
        "<b>Flask</b> (app.py) creates a task ID, stores it in analysis_tasks dict, spawns a background thread.",
        "<b>Thread</b> imports main.py and calls run_sequential().",
        "<b>run_sequential()</b> calls initialize() which creates the LLM object (groq/llama-3.3-70b-versatile) and 3 agents.",
        "<b>CrewAI Crew</b> is created with agents=[expense_tracker, budget_analyzer, financial_advisor], tasks=[task_track, task_budget, task_advise], process=Process.sequential.",
        "<b>crew.kickoff()</b> starts the pipeline. CrewAI sends Task 1 to the Expense Tracker agent.",
        "<b>Expense Tracker</b> receives the task prompt. The LLM reasons: 'I need to call generate_spending_report'. CrewAI calls the tool. The tool reads sample_expenses.json, filters by March 2026, computes totals per category, and returns a JSON report.",
        "<b>Expense Tracker</b> receives the tool result. The LLM summarizes: 'Food: $318.00 (9 transactions), Entertainment: $245.00 (5 transactions, near budget)...' This becomes the final output for Task 1.",
        "<b>CrewAI</b> passes Task 1's output as context to Task 2. The Budget Analyzer receives both the task description and the expense summary.",
        "<b>Budget Analyzer</b> calls check_budget_status 5 times (one per category). For categories above 70%, it calls predict_month_end_spending. It then reflects on its analysis and outputs a prioritized budget report.",
        "<b>CrewAI</b> passes both Task 1 and Task 2 outputs as context to Task 3.",
        "<b>Financial Advisor</b> calls find_savings_opportunities('all'). Using all the context, it produces: top 3 savings tips with dollar amounts, budget adjustment suggestions, goal progress assessment, and a monthly action plan.",
        "<b>CrewAI</b> collects the final result. The background thread stores it in analysis_tasks[task_id] with status='complete'.",
        "<b>Browser</b> (polling every 5 seconds) gets status='complete' and displays the formatted result.",
        "<b>Memory is saved</b> - workflow events are persisted to long_term_memory.json.",
    ]
    for i, step in enumerate(e2e_steps, 1):
        story.append(bullet(f"<b>{i}.</b> {step}"))

    story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════════════════════
    # 12. TECH STACK
    # ═══════════════════════════════════════════════════════════════════════
    story.append(heading("12. Tech Stack Summary"))
    tech_rows = [
        ["CrewAI 1.12", "Multi-agent orchestration framework. Manages agents, tasks, tool calling, and sequential/hierarchical workflows."],
        ["Groq API", "LLM provider hosting Llama 3.3 70B Versatile. Provides fast inference. Free tier: 12K TPM."],
        ["LiteLLM", "Universal LLM gateway. Translates CrewAI's requests to Groq's API format. Handles retries."],
        ["Flask 3.1", "Web framework. Serves the dashboard, handles expense forms, provides REST APIs for analysis."],
        ["Bootstrap 5.3", "CSS framework for responsive layout, cards, progress bars, tables, badges, and alerts."],
        ["Chart.js 4", "JavaScript charting library. Renders interactive doughnut and bar charts for spending breakdown."],
        ["Font Awesome 6", "Icon library. Provides category icons (utensils, car, gamepad, etc.) and UI icons."],
        ["pytest", "Testing framework. 28 tests covering all tools and memory system."],
        ["Python 3.11", "Runtime. Required for tiktoken compatibility (Python 3.14 not supported)."],
    ]
    story.append(make_table(
        ["Technology", "Role in This Project"],
        tech_rows,
        col_widths=[100, 370],
    ))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="40%", thickness=2, color=PRIMARY, spaceAfter=10))
    story.append(Paragraph("End of Report", styles["SmallMuted"]))

    # ─── Build ────────────────────────────────────────────────────────────
    doc.build(story)
    print(f"Report generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_report()
