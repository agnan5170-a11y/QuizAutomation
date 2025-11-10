# QuizAutomation (Python + Flask + SQLite)

A simple offline Quiz / Exam Automation system built with Flask and SQLite.

## Features

- Admin upload questions via JSON/CSV
- Randomized quiz (10–20 questions)
- Timer on quiz page
- Score calculation + review screen
- Auto-generated PDF certificate per attempt
- SQLite for persistence

## Tech Stack

- Python 3.x
- Flask
- SQLite
- ReportLab (PDF)
- Bootstrap 5

## Run Locally

```bash
git clone https://github.com/yourusername/QuizAutomation.git
cd QuizAutomation
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
python app.py
