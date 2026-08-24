# Vision AI + Playwright POC

A small end-to-end POC demonstrating how **Vision AI** can work with **Playwright** for UI testing.

## Flow

```text
Web UI
  ↓
Screenshot + DOM
  ↓
Vision AI
  ↓
AI Action Plan
  ↓
Playwright
  ↓
Browser Interaction
  ↓
Result Screenshot
  ↓
Vision AI Validation
  ↓
PASS / FAIL
```

## How Vision AI Helps

Instead of hardcoding every UI action, Vision AI understands the page and identifies elements such as:

* Username field
* Password field
* Sign In button

Playwright then resolves and executes those actions.

Vision AI also analyzes the final screenshot to verify whether the expected UI state was reached.

## Tech Stack

* Python
* Playwright
* Ollama
* Qwen2.5-VL 7B

## Setup

### 1. Clone the repository

```bash
git clone <REPOSITORY_URL>
cd vision-playwright-poc
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Install the Vision AI model

```bash
ollama pull qwen2.5vl:7b
```

### 5. Start Ollama

```bash
ollama serve
```

## Run

From the project root:

```bash
python -m app.main
```

A Chromium browser will open and execute the test scenarios.

## Test Scenarios

The POC currently tests:

1. Valid login
2. Invalid password
3. Empty username
4. Empty password

Each test follows:

```text
Vision AI → Understand UI
              ↓
Playwright → Execute Actions
              ↓
Vision AI → Validate Result
              ↓
           PASS / FAIL
```

## Project Structure

```text
vision-playwright-poc/
│
├── app/
│   ├── main.py
│   └── vision.py
│
├── web/
│   └── index.html
│
├── screenshots/
│
├── requirements.txt
└── README.md
```

## Files

### `app/main.py`

Contains the Playwright automation and test execution.

### `app/vision.py`

Contains the Vision AI integration for:

* UI understanding
* Action-plan generation
* Visual result validation

### `web/index.html`

Simple login application used as the test target.

### `screenshots/`

Contains screenshots captured before and after each test.

## Goal

Demonstrate how **Vision AI can add UI understanding and visual validation to Playwright**, while **Playwright remains responsible for reliable browser automation**.
