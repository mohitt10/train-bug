# WanderLog — Database Setup

## 1. Technology

WanderLog uses:

- PostgreSQL as its relational database.
- Psycopg 3 as its Python PostgreSQL adapter.
- Flask as the backend framework.
- Environment variables for database credentials and application configuration.

## 2. Database Details

| Setting | Value |
|---|---|
| Database | `wanderlog_db` |
| Application user | `wanderlog_user` |
| Host | `localhost` |
| Port | `5432` |
| Database system | PostgreSQL |

The application connects using the `DATABASE_URL` environment variable.

## 3. Environment Configuration

The backend expects a `.env` file inside the `server/` directory.

Required variables:

- `FLASK_SECRET_KEY`: Flask application secret.
- `DATABASE_URL`: PostgreSQL connection string.

An example configuration is provided in `server/.env.example`.

The actual `.env` file must not be committed to version control.

## 4. Python Environment

From the `server/` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Database Schema

The database schema is defined in `server/schema.sql`.

It creates the following nine tables:

1. `users`
2. `moderators`
3. `follows`
4. `posts`
5. `comments`
6. `replies`
7. `post_likes`
8. `comment_likes`
9. `reports`

The schema includes the primary keys, foreign keys, unique constraints, composite keys, and CHECK constraints specified by the relational design.
It also creates query-supporting indexes for timelines, threaded content, likes, follows,
and report queues.

To initialize an empty database:

```bash
psql "$DATABASE_URL" -f schema.sql
```

Run this script once against an empty database. It is not a migration script and should not be rerun against an already initialized database.

## 6. Database Connection

`server/db.py` provides the shared database connection and SQL execution functions.

- `get_connection()` creates a PostgreSQL connection.
- `execute_query()` executes parameterized SQL.
- Successful operations are committed.
- Failed operations are rolled back.
- Cursors and connections are closed after execution.

## 7. Query Monitoring

`server/query_monitor.py` maintains a thread-safe, in-memory history of SQL executions.

Each record contains:

- Query ID
- Request ID, when available
- Timestamp
- Endpoint
- Action
- SQL operation
- SQL statement
- Execution success or failure
- Execution duration
- Affected row count
- Safe error summary

The history is limited to 500 entries. Older entries are discarded when the limit is exceeded.

Query history is not persisted in PostgreSQL and is lost when the application process restarts.

SQL parameter values are not recorded.

The SQL Inspector is moderator-only. It exposes captured SQL templates and safe
execution metadata, not query parameter values. History is process-local, bounded, and
is not shared between multiple server workers.

## 10. Moderators and report policy

Moderator accounts are provisioned only by an operator with trusted server access; there
is no public endpoint that can grant moderator privileges. After registering the
account, run from `server/`:

```bash
python manage_moderators.py <username>
```

Reports use `pending`, `resolved`, and `dismissed` states. A pending report may be
reviewed once into either terminal state. The API sets `reviewed_by` from the
authenticated moderator and retains report rows. Because report-target foreign keys are
restrictive and history is retained, content with any report cannot be deleted, even
after review. Unreported owned content can be deleted under the existing FK-safe
cascade policy.

## 8. Health Checks

The backend currently provides:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Checks whether the Flask service responds. |
| `GET /api/health/db` | Checks whether Flask can execute a query against PostgreSQL. |

The database health endpoint uses the shared SQL execution layer.

## 9. Important Design Decisions

- SQL is written explicitly rather than through an ORM.
- PostgreSQL `TIMESTAMPTZ` is used for timestamp columns.
- Standalone integer primary keys use identity generation.
- Creation timestamps default to `CURRENT_TIMESTAMP`.
- Foreign keys use the default `NO ACTION` deletion behaviour.
- No additional database tables are introduced for query monitoring.
- No reply-likes table is included.

## Starting the Backend

After configuring PostgreSQL and initializing the database schema, the Flask backend can be started.

### 1. Navigate to the server directory

From the project root:

```bash
cd server
```

### 2. Activate the virtual environment

```bash
source .venv/bin/activate
```

If the virtual environment has not been created yet, create it first:

```bash
python3 -m venv .venv
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Ensure that `server/.env` contains the required variables:

- `FLASK_SECRET_KEY`
- `DATABASE_URL`
- `QUERY_HISTORY_LIMIT`

Refer to `.env.example` for the expected configuration format.

### 5. Start the Flask application

Run:

```bash
flask --app app run --debug
```

The backend will be available at:

`http://127.0.0.1:5000`

### 6. Verify the application

Open the following endpoints in a browser:

- `http://127.0.0.1:5000/api/health` — Checks whether the Flask service is running.
- `http://127.0.0.1:5000/api/health/db` — Checks whether the application can connect to PostgreSQL.

A successful database health check returns a JSON response indicating that the database is connected.

### 7. Stop the application

Press `Ctrl+C` in the terminal to stop the Flask development server.