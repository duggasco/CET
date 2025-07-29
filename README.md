# Client Exploration Tool

A Flask-based web application for exploring money market mutual fund client data with interactive charts and tables.

## Features

- **Interactive Charts**: 30-day balance history line chart and distribution doughnut chart
- **Three Data Tables**: Client balances, fund summary, and account details
- **Click-to-Filter**: Click any row in any table to filter all data
- **SQLite Backend**: Efficient data storage with proper indexing
- **RESTful API**: Clean API endpoints for data retrieval

## Architecture

- **Backend**: Flask with SQLite database
- **Frontend**: Vanilla JavaScript with Chart.js for visualizations
- **Database Schema**:
  - `client_mapping`: Maps accounts to clients
  - `account_balances`: Daily fund-level balances per account

## Setup

1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Generate sample data:
   ```bash
   python database.py
   ```

3. Run the application:
   ```bash
   ./run.sh
   # or
   python app.py
   ```

4. Open browser to `http://localhost:5000`

## Usage

- Click on any client name to filter by that client
- Click on any fund name to filter by that fund
- Click on any account ID to see account-specific details
- Click the header title to reset to overview

## API Endpoints

- `GET /api/overview` - Get all aggregated data
- `GET /api/client/<client_id>` - Get client-specific data
- `GET /api/fund/<fund_name>` - Get fund-specific data
- `GET /api/account/<account_id>` - Get account-specific data