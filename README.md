# Personal Finance Manager — Multi-Agent System

A multi-agent system built with **CrewAI** and **Groq (Llama 3.3 70B)** that helps users manage personal finances through expense tracking, budget analysis, and savings recommendations. Includes a **Flask web dashboard** with interactive charts, budget tracking, and AI-powered financial advice.

## Screenshots

The web UI provides:
- **Dashboard** with budget cards, spending charts, financial goals, and recent transactions
- **Add Expense** form to log new transactions
- **AI Analysis** page to run multi-agent financial analysis (Sequential or Hierarchical)

## Features

### 3 Core Agents
| Agent | Role | Patterns |
|-------|------|----------|
| **Expense Tracker** | Records & categorizes expenses, identifies unusual spending | ReAct, Planning |
| **Budget Analyzer** | Compares spending vs budgets, calculates burn rates | ReAct, Reflection |
| **Financial Advisor** | Provides personalized savings advice & budget adjustments | Planning, Hierarchical |

### 5 Financial Tools
1. `calculate_category_total` — Total spent in a category for a date range
2. `check_budget_status` — Budget usage percentage and status per category
3. `predict_month_end_spending` — Projects end-of-month total based on burn rate
4. `find_savings_opportunities` — Identifies patterns and potential savings
5. `generate_spending_report` — Comprehensive financial summary

### Flask Web Dashboard
- **Budget overview cards** with color-coded progress bars and status badges
- **Interactive charts** (doughnut/bar toggle) powered by Chart.js
- **Financial goals tracker** with progress visualization
- **Recent transactions table** with category badges
- **Add Expense form** with validation (persists to data files)
- **AI Analysis page** with background processing, live progress indicator, and formatted results
- **Budget alerts banner** for categories approaching or exceeding limits

### Memory System
- **Short-term Memory**: Conversation context, recent transactions (7 days), active alerts, temp calculations
- **Long-term Memory**: User profile, spending history, financial goals, preferences
- **Persistence**: File-based save/load between sessions (`memory/storage/`)

### Collaboration Patterns
1. **Sequential**: Expense Tracker -> Budget Analyzer -> Financial Advisor
2. **Hierarchical**: Financial Advisor coordinates all agents as manager

## Project Structure

```
agentic ai/
├── app.py                   # Flask web application (dashboard UI)
├── main.py                  # CLI entry point — runs multi-agent workflow
├── agents/
│   ├── __init__.py
│   ├── expense_tracker.py   # Expense Tracker Agent (ReAct + Planning)
│   ├── budget_analyzer.py   # Budget Analyzer Agent (ReAct + Reflection)
│   └── financial_advisor.py # Financial Advisor Agent (Planning + Hierarchical)
├── tools/
│   ├── __init__.py
│   └── financial_tools.py   # 5 financial tool functions
├── memory/
│   ├── __init__.py
│   ├── memory_system.py     # Short-term & Long-term memory classes
│   └── storage/             # Persisted memory files (auto-created)
├── data/
│   ├── sample_expenses.json # 25+ mock transactions
│   ├── user_profile.json    # Income, budgets, goals
│   └── categories.json      # Valid expense categories
├── templates/
│   ├── base.html            # Base layout (Bootstrap 5, Chart.js, Font Awesome)
│   ├── dashboard.html       # Dashboard with charts, budget cards, goals, transactions
│   ├── add_expense.html     # Add new expense form
│   └── analysis.html        # AI analysis page with background processing
├── static/
│   └── css/
│       └── style.css        # Custom styles (gradients, cards, progress bars)
├── tests/
│   ├── test_tools.py        # Tests for all 5 financial tools
│   └── test_memory.py       # Tests for memory system
├── requirements.txt
├── .env                     # API key (not committed)
└── README.md
```

## Setup & Run

### 1. Create Virtual Environment (Python 3.11 recommended)

```bash
cd "agentic ai"
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set API Key

Edit the `.env` file and add your Groq API key:

```
GROQ_API_KEY=your_actual_groq_api_key
```

Get a key from: https://console.groq.com/keys

### 4. Run the Web Dashboard (Flask)

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

**Pages:**
- `/` — Dashboard with budget overview, charts, goals, and recent transactions
- `/add-expense` — Form to add a new expense
- `/analysis` — Run AI multi-agent analysis (Sequential or Hierarchical)

### 5. Run the CLI Version

```bash
python main.py
```

You will be prompted to select a workflow pattern:
- **Option 1**: Sequential pipeline (recommended for first run)
- **Option 2**: Hierarchical coordination
- **Option 3**: Run both patterns

### 6. Run Tests

```bash
python -m pytest tests/ -v
```

28 tests covering all 5 financial tools and the memory system.

## Expense Categories

| Category | Description |
|----------|-------------|
| food | Groceries, restaurants, cafes, delivery |
| transport | Public transit, ride-sharing, fuel |
| entertainment | Movies, games, subscriptions, events |
| bills | Utilities, rent, phone, internet |
| healthcare | Doctor, medicines, dental, insurance |

## How It Works

### Web Dashboard Flow
1. **Dashboard loads** — Reads expense data and user profile, computes budget status for all categories
2. **Budget alerts shown** — Categories approaching or exceeding limits are highlighted
3. **Charts rendered** — Chart.js visualizes spending breakdown (doughnut/bar toggle)
4. **Add expenses** — New transactions are saved to the data file and reflected immediately
5. **AI Analysis** — Runs CrewAI agents in a background thread; polls for results via API

### Multi-Agent Workflow
1. **Memory loads** — User profile, spending history, and previous session data are loaded
2. **Budget alerts check** — System scans all categories for approaching/exceeded limits
3. **Agents execute** — Based on selected pattern, agents analyze finances using tools
4. **Results synthesized** — Financial Advisor provides actionable recommendations
5. **Memory saved** — Session data persisted for next run

## Tech Stack

- **Backend**: Flask, CrewAI, LiteLLM
- **LLM**: Groq (Llama 3.3 70B Versatile)
- **Frontend**: Bootstrap 5.3, Chart.js 4, Font Awesome 6, Google Fonts (Inter)
- **Memory**: File-based JSON persistence
- **Testing**: pytest (28 tests)

## Notes

- **Groq Free Tier**: The free tier has a 12K tokens-per-minute limit. The app includes a built-in rate limiter (15s between LLM calls) and retry logic. AI analysis may take 2-5 minutes to complete.
- **Python Version**: Python 3.11 is recommended. Python 3.14 has compatibility issues with the `tiktoken` package.
