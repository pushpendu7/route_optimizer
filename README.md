AI Agent for Real-time Logistics Route Optimization
---------------------------------------------------

1. Setup
- Python 3.10+ recommended.
- Create virtualenv and install requirements:
    pip install -r requirements.txt

2. API keys (optional but recommended for real APIs)
- OPENWEATHER_API_KEY: OpenWeatherMap
- MAPBOX_TOKEN: Mapbox
- ORS_API_KEY: OpenRouteService (or leave empty to use haversine fallback)
- OPENAI_API_KEY: OpenAI API for Planner LLM (or leave empty to use fallback heuristic)

Create a .env file in the project root with:
OPENWEATHER_API_KEY=your_key_here
MAPBOX_TOKEN=your_mapbox_token
ORS_API_KEY=your_ors_key
OPENAI_API_KEY=your_openai_key

3. Train sample model (optional)
- From command line: python -c "from models import train_and_save_model; train_and_save_model()"
- Or use the "Train sample model" button in the sidebar of the app.

4. Run
- streamlit run app.py

5. Usage
- Select role (Operator or Delivery Agent) from sidebar.
- Operator can generate plan, view traffic/weather sample JSON, apply manual overrides.
- Delivery Agent can view assigned route, mark delivery actions, and request reroute.

6. Notes & Extensions
- This is a demonstration scaffold. For production:
  - Add secure authentication & permissions (JWT/OAuth).
  - Persist state in a database (Postgres, Redis).
  - Replace demo polling with websocket-based push for real-time updates.
  - Harden LLM prompts and sanitize outputs.
  - Increase sample data volume and retrain a real travel-time model on historical telemetry.
