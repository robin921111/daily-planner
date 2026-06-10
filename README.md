# Daily Planner Assistant

Daily Planner Assistant is a Streamlit web app that turns your tasks, available hours, energy level, and fixed commitments into a realistic AI-generated time-blocked plan. It also lets you navigate by day, save and revisit past plans, and export schedules to PDF for easy sharing or reference.

## Features

- AI-generated time-blocked schedules
- Week navigation with date display
- Energy level selector
- Fixed commitments input
- Save and view past plans
- Export to PDF
- Deployed as a live web app

## Tech Stack

- Python
- Streamlit
- Groq API (llama-3.3-70b-versatile)
- reportlab
- python-dotenv

## How to Run Locally

1. Clone the repository to your machine.
2. Create a `.env` file in the project root.
3. Add your Groq API key to the `.env` file:

   ```env
   GROQ_API_KEY=your_api_key_here
   ```

4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Run the app:

   ```bash
   streamlit run app.py
   ```

## Live Demo

[https://daily-planner-robin-9djizu26kaffvj4xjy86x6.streamlit.app/](https://daily-planner-robin-9djizu26kaffvj4xjy86x6.streamlit.app/)
