# Phase 3 Local Dev Database & Testing Guide

> **Note:** DEV ONLY. The real schema and initialization belong to Phase 1. Do not merge this dev setup into the final database setup.

This directory contains standalone database initialization and seed data to develop and test Phase 3 features (Posts, Comments, Replies, Feed) independently of Phases 1 and 2.

---

## 1. Setup Local PostgreSQL Database

Create a local database for WanderLog (if not already created):

```bash
# Using psql:
createdb wanderlog
# Or within psql:
# CREATE DATABASE wanderlog;
```

Load the Phase 3 standalone development schema and seed records:

```bash
psql -d wanderlog -f server/dev/phase3_dev_schema.sql
```

This creates the 4 core content tables (`users`, `posts`, `comments`, `replies`) and populates seed users and posts:
* User 1: `alex_traveler` (Alex Mercer)
* User 2: `sarah_journeys` (Sarah Jenkins)
* User 3: `dan_nomad` (Dan Reynolds)
* User 4: `nomad_priya` (Priya Sharma)

---

## 2. Configure Environment Variables

Create or update `server/.env`:

```env
FLASK_SECRET_KEY=dev_secret_key_123
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/wanderlog

# Or separate connection parameters:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wanderlog
DB_USER=postgres
DB_PASSWORD=postgres
```

---

## 3. Run the Flask Server

From the `server` directory:

```bash
pip install -r requirements.txt
python app.py
```

The server starts on `http://127.0.0.1:5000`.

---

## 4. Testing Phase 3 Authenticated Requests

Because Phase 2 authentication is being developed concurrently by another team member, Phase 3 uses a **dev stub** in `server/content/compat.py` which inspects the `X-Dev-User-Id` header:

```bash
# Create a post as User 1 (Alex Mercer):
curl -X POST http://127.0.0.1:5000/api/posts \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 1" \
  -d '{"title": "Ghat Roads in the Rain", "content": "Navigating the hairpins in heavy monsoon clouds.", "location": "Tamhini Ghat"}'

# Fetch the global feed:
curl http://127.0.0.1:5000/api/feed
```
