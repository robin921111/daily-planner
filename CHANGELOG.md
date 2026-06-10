## Weekend Build Log

### Prototype 1 — Claude.ai Artifact
- Built a Daily Planner Assistant widget inside Claude.ai
- Input: tasks, available hours, energy level, fixed commitments
- Output: time-blocked schedule with breaks and motivational note
- Tested successfully with real tasks
- No API key needed — ran directly in Claude chat

### Prototype 2 — VS Code + Streamlit + Google Gemini
- Rebuilt as a proper Python web app using Streamlit
- Connected to Google Gemini API (model: gemini-1.5-flash) for schedule generation
- API key stored securely in .env file (excluded from version control via .gitignore)
- UI features: task input, time pickers, energy level dropdown, fixed commitments field
- Generate and Regenerate buttons
- Reason for choosing Gemini: free tier available, no credit card required, easy setup

### What I Learned
- How to build a web app with Python and Streamlit
- How to connect an app to an external AI API
- How to manage API keys securely using .env files
- How to use VS Code's Build with Agents to generate code from plain English prompts