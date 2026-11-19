🎮 JoyStream AI

AI-powered Twitch Analytics Platform

JoyStream AI is a personal project that collects, stores, visualizes and analyzes Twitch channel statistics using Python, FastAPI, PostgreSQL, Docker and local Artificial Intelligence.

Built for the Twitch channel "Joysantalola" (https://www.twitch.tv/joysantalola67).

✨ Features

- Twitch API integration for clips, VODs, channel information and game categories.
- Historical tracking of views, followers and available subscriber metrics.
- Live-stream audience monitoring and game comparisons.
- Automated Twitch data synchronization.
- Modern responsive dashboard built with HTML, CSS and JavaScript.
- Local AI analytics powered by Ollama and Qwen 2.5 3B.
- Twitch advertising schedule information where available.
- PostgreSQL persistence and Python unit tests.

🛠️ Tech Stack

Category| Technology
Backend| Python, FastAPI
Database| PostgreSQL, SQLAlchemy
Artificial Intelligence| Ollama, Qwen 2.5 3B
Frontend| HTML, CSS, JavaScript, Nginx
Analytics| Pandas, Streamlit
Infrastructure| Docker, Docker Compose
Integration| Twitch Helix API, OAuth 2.0
Testing| Python unittest

🚀 Getting Started

Clone the repository:

git clone https://github.com/joysantalola/JoyStream-AI.git
cd JoyStream-AI

Configure your local ".env" file with the required Twitch credentials and database settings. Never commit secrets.

Start the application:

docker compose up -d --build

Download the local AI model:

docker compose exec ollama ollama pull qwen2.5:3b

Open the applications:

- Web Dashboard: http://localhost:8080
- FastAPI Documentation: http://localhost:8000/docs
- Streamlit Dashboard: http://localhost:8501

Some Twitch features require additional OAuth authorization and channel eligibility.

🤖 Local AI Assistant

JoyStream AI uses Ollama to analyze real statistics stored in PostgreSQL.

The assistant can help identify top-performing clips, compare games, review audience trends and suggest content improvements.

No paid AI API is required.

🧪 Testing

docker compose exec backend python -m unittest app.test_ai -v

📊 Project Status

Active development. The core analytics platform, dashboard and local AI assistant are implemented.

Live audience monitoring is awaiting validation during an actual Twitch broadcast. Additional testing, security improvements and detailed documentation are planned.

👨‍💻 About the Developer

Developed by Oleguer (Joysantalola), focused on Artificial Intelligence, Big Data and backend development.

- "GitHub" (https://github.com/joysantalola)
- "Twitch" (https://www.twitch.tv/joysantalola67)

---

Independent portfolio project. Not affiliated with Twitch.
