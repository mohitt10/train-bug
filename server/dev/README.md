# WanderLog Development Database & Setup Guide

This guide describes how to initialize your PostgreSQL database with the official schema and development seed data for Phase 3.

---

## 1. Create Local Database

Create the PostgreSQL database as specified in `server/.env.example` (`wanderlog_db`):

```bash
createdb wanderlog_db
# Or inside psql:
# CREATE DATABASE wanderlog_db;
```

---

## 2. Apply Schema & Seed Data

Run the official Phase 1 database schema first, followed by the safe development seed data:

```bash
# 1. Apply authoritative schema (all 9 tables, constraints, indexes)
psql -d wanderlog_db -f server/schema.sql

# 2. Insert dev seed data (users, sample posts, comments, replies)
psql -d wanderlog_db -f server/dev/seed_dev_data.sql
```

The seed script creates 4 seed travelers:
1. `alex_traveler` — Alex Mercer
2. `sarah_journeys` — Sarah Jenkins
3. `dan_nomad` — Dan Reynolds
4. `priya_wander` — Priya Sharma

---

## 3. Configure Environment Variables

In `server/.env`:

```env
FLASK_SECRET_KEY=dev_secret_key_123
DATABASE_URL=postgresql://wanderlog_user:replace-with-password@localhost:5432/wanderlog_db
QUERY_HISTORY_LIMIT=500

# Enable dev auth simulation header (X-Dev-User-Id)
ALLOW_DEV_AUTH=1
```

---

## 4. Run the Server

From the `server` directory:

```bash
pip install -r requirements.txt
python app.py
```

The server starts on `http://127.0.0.1:5000`.

---

## 5. Testing with Simulated Auth

With `ALLOW_DEV_AUTH=1`, requests with `X-Dev-User-Id` will authenticate as that user if they exist in the `users` table:

```bash
# Create a post as User 1 (Alex Mercer):
curl -X POST http://127.0.0.1:5000/api/posts \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 1" \
  -d '{"title": "Ghat Roads in the Rain", "content": "Navigating the hairpins in heavy monsoon clouds.", "location": "Tamhini Ghat"}'

# Fetch the global feed:
curl http://127.0.0.1:5000/api/feed
```
