# Campus Navigator

**Status:** *In Development*

Campus Navigator is a full-stack web application designed to help users navigate campus grounds, find offices, and discover local events. It combines an interactive map frontend with an AI-powered backend to resolve location queries and manage campus data.

## 📂 Project Structure

The repository is organized as a monorepo:

* **`backend/`**: Python application (likely FastAPI/Flask) that handles API requests, database interactions (`map.db`), and AI location logic.
* **`frontend/`**: Modern React application built with TypeScript and Vite. Contains the map view and UI components.
* **`frontend_old/`**: Deprecated frontend code (archived).

## 🚀 Getting Started

### Prerequisites

* Node.js & npm
* Python 3.10+
* Git

### 1. Backend Setup

The backend manages the database and AI resolution services.

```bash
# Navigate to backend
cd backend

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
# (Check run.sh for specific entry point, likely uvicorn or python app.main)
./run.sh

```

### 2. Frontend Setup

The frontend provides the interactive map interface.

```bash
# Open a new terminal and navigate to frontend
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev

```

The frontend typically runs at `http://localhost:5173`.

## ✨ Key Features

* **Interactive Map**: Navigate campus grounds using `MapView` (powered by Leaflet/Mapbox/Google Maps).
* **AI Location Resolution**: Natural language processing (`ai_locate.py`) to find buildings and offices based on vague user queries.
* **Event Tracking**: Real-time listing of campus events (`events_smart.py`).
* **Office Locator**: dedicated search for faculty and administrative offices.
* **Data Processing**: Scripts to fetch and calculate map centroids (`fetch_centroids.py`) using Overpass/OSM data.

## 🛠 Tech Stack

* **Frontend**: React, TypeScript, Vite, Tailwind CSS (inferred), ESLint.
* **Backend**: Python, SQLite, AI/ML libraries.
* **Deployment**: Docker support included (`backend/Dockerfile`).

## ⚠️ Notes

* The `scripts_out/` directory contains generated JSON data for map centroids.
* `frontend_old/` is kept for reference only and should not be used for development.

---

*Temporary for the `new-version` branch.*