# WanderLog — Architecture Audit

**Project:** WanderLog
**Project type:** Database Management Systems (DBMS) project
**Audit phase:** Phase 1 — Foundation
**Status:** Implementation completed; final verification pending

## 1. Project Structure

The repository contains the following main components:

- `client/` — React frontend using Vite.
- `server/` — Flask backend and PostgreSQL integration.
- `ERD/` — Entity Relationship Diagram.
- `schema/` — Relational database schema diagram.
- `docs/` — Project documentation.

Important backend files:

- `app.py` — Flask application and API endpoints.
- `config.py` — Environment-based application configuration.
- `db.py` — PostgreSQL connection and SQL execution.
- `query_monitor.py` — SQL execution history.
- `schema.sql` — PostgreSQL table definitions.
- `requirements.txt` — Python dependencies.
- `.env.example` — Environment configuration template.

## 2. Frontend

**Technology:** React 19 and Vite.

The frontend entry point is `client/src/main.jsx`, with `client/src/App.jsx` as the main application component.

The existing interface checks the backend health endpoint.

Authentication, profiles, posts, comments, and other social functionality remain outside Phase 1.

## 3. Backend

**Technology:** Python and Flask.

The backend provides:

- `GET /api/health` — Basic service health check.
- `GET /api/health/db` — Database connectivity check.

A request ID is generated for each request and returned through the `X-Request-ID` response header.

## 4. Database Design

**Database system:** PostgreSQL
**Python adapter:** Psycopg 3

The database contains nine tables:

1. `users`
2. `moderators`
3. `follows`
4. `posts`
5. `comments`
6. `replies`
7. `post_likes`
8. `comment_likes`
9. `reports`

The implementation follows the supplied relational schema and ER diagram.

Implemented constraints include:

- Primary keys and foreign keys.
- Unique usernames and email addresses.
- Composite primary keys for relationship tables.
- A CHECK constraint preventing users from following themselves.
- A CHECK constraint requiring each report to target exactly one post, comment, or reply.

The `password_hash` column is NOT NULL, as specified by the relational schema.

### Recommended Indexes

The following indexes are identified as potential performance improvements for future application queries:

| Table | Recommended Index |
|---|---|
| `posts` | `(user_id)` |
| `posts` | `(created_at, post_id)` |
| `comments` | `(post_id, created_at, comment_id)` |
| `replies` | `(comment_id, created_at, reply_id)` |
| `follows` | `(following_id, follower_id)` |
| `post_likes` | `(post_id)` |
| `comment_likes` | `(comment_id)` |
| `reports` | `(status, created_at)` |

These indexes are documented as recommendations and have not been implemented. Their necessity should be evaluated against actual application query patterns in subsequent phases.

## 5. Configuration and Dependencies

Application configuration is loaded from environment variables using `python-dotenv`.

The application uses:

- `FLASK_SECRET_KEY`
- `DATABASE_URL`
- `QUERY_HISTORY_LIMIT`

Actual credentials are stored in `server/.env`, which is excluded from version control.

The example configuration is maintained in `server/.env.example`.

Python dependencies are recorded in `server/requirements.txt`.

## 6. Database Connection and SQL Execution

`server/db.py` provides:

- A shared PostgreSQL connection factory.
- Parameterized SQL execution.
- Transaction commit on success.
- Transaction rollback on failure.
- Cursor and connection cleanup.

The application uses explicit SQL rather than an ORM.

## 7. SQL Query Monitoring

`server/query_monitor.py` provides thread-safe, in-memory SQL execution history.

Recorded metadata includes:

- Query ID and request ID.
- Timestamp and endpoint/action.
- SQL operation and statement.
- Execution status (success or failure).
- Execution duration.
- Affected row count.
- Safe error summary.

The history is bounded by the configurable QUERY_HISTORY_LIMIT environment variable, which defaults to 500 records.

SQL parameter values and raw exception messages are not stored.

Query history is currently in-memory only and is not persisted across application restarts.

A dedicated query-inspector interface is outside the current implementation scope.

## 8. Documentation

The following documentation has been established:

- `docs/architecture-audit.md`
- `docs/database-setup.md`
- `docs/api-conventions.md`

These documents describe the architecture, database setup, implementation decisions, and conventions for future API development.

## 9. Pending Design Decisions

The diagrams do not specify all application-level policies.

The following decisions remain open for future phases:

- Permitted values and transitions for `account_status`.
- Permitted report statuses and moderation transitions.
- Account and content deletion policies.
- Automatic handling of `updated_at`.
- Whether nullable content and report fields should have stricter application-level validation.

These decisions should be made before implementing the relevant application functionality.

## 10. Phase 1 Completion Criteria

| Requirement | Status |
|---|---|
| Repository architecture audited | Complete |
| PostgreSQL environment configured | Complete |
| Database connection established | Complete |
| Nine tables implemented | Complete |
| Primary and foreign keys implemented | Complete |
| Required CHECK constraints implemented | Complete |
| Parameterized SQL execution implemented | Complete |
| Transaction handling implemented | Complete |
| Query success/failure capture implemented | Complete |
| Bounded, thread-safe query history implemented | Complete |
| Request ID tracking implemented | Complete |
| Database health endpoint implemented | Complete |
| Environment secrets excluded from Git | Complete |
| Database and API documentation | Complete |
| Final Git verification | Pending |