# Gesture Data Dashboard

Gesture Data Dashboard is a camera-based hand gesture recognition project. The application recognizes hand gestures and saves the detected events to a PostgreSQL database. The recorded data can be viewed and analyzed on a web dashboard.

## Features

- Recognition of `OPEN PALM`, `FIST`, and `POINT` gestures
- Real-time camera tracking
- Saving gesture events to PostgreSQL
- Displaying event totals and percentages
- Daily and hourly activity charts
- Gesture and date filtering
- Paginated event table
- CSV export
- Gesture accuracy results

## Technologies

Python, Flask, PostgreSQL, OpenCV, MediaPipe, HTML, CSS, JavaScript, Chart.js, and Docker.

## Running the Project

Create and activate the virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the required packages:

```powershell
python -m pip install -r requirements-dashboard.txt
```

Start PostgreSQL and the dashboard:

```powershell
docker compose up --build -d
```

Start gesture detection:

```powershell
python hand_tracking.py
```

Open the dashboard in a browser:

```text
http://127.0.0.1:5000
```

## Testing

Run the application tests with:

```powershell
python -m unittest test_dashboard.py -v
```

## Project Purpose

The purpose of this project is to combine hand gesture recognition, database usage, data analysis, and web development in one application.

## Project Status

The project has been finalized after completing functional tests, documentation updates, and general repository checks.
