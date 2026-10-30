# WanderLog Phase 4 — Final Demonstration

Phase 4 completes likes, reporting, moderator review, and the SQL Inspector on top of
the Phase 1 database foundation and Phase 2/3 application.

## 1. Initialize and run

Initialize a fresh PostgreSQL database using the steps in
[database-setup.md](./database-setup.md), then install dependencies and configure
`server/.env`. Use a generated `FLASK_SECRET_KEY`, the correct `DATABASE_URL`, and
leave `ALLOW_DEV_AUTH=0` for the real session-auth demonstration.

Start the backend from `server/`:

```bash
python app.py
```

In another terminal, start the client from `client/`:

```bash
npm install
npm run dev
```

Register two accounts through the UI. The SQL seed users have placeholder development
password hashes and are for the header-auth smoke test only.

## 2. Provision a moderator

Grant moderator access to one registered account using trusted local server access:

```bash
cd server
python manage_moderators.py <moderator-username>
```

There is deliberately no public moderator-promotion API.

## 3. Demonstrate core application features

1. Register and log in; reload the page to demonstrate signed-session restoration.
2. Edit the profile, follow another user, and view follower/following lists.
3. Create a post, comment, and reply; edit and delete owned content.
4. Like/unlike a post and comment. Repeat the like request to demonstrate duplicate
   prevention and use the returned count/current-user state.
5. Submit a report against a post, comment, or reply. The reporter and target columns
   are selected by the server.
6. Log in as the provisioned moderator and open **Moderation**. Review a pending report
   as resolved or dismissed; verify the reviewer attribution.
7. Open the moderator-only **SQL Query Inspector**, filter by operation or request ID,
   and show actual captured SQL templates, status, duration, affected rows, action,
   endpoint, timestamp, and request correlation. Parameter values are never displayed.
8. Attempt to delete the reported content. The API returns `409 CONTENT_HAS_REPORTS`;
   report history is retained even after review. Unreported owned content can still be
   deleted.

## 4. Automated checks

From the repository root:

```bash
cd server
python -m unittest tests.test_content tests.test_phase4 -v
cd ../client
npm run build
npm run lint
```

The test suites mock PostgreSQL for deterministic endpoint checks. For database-level
constraint and transaction demonstrations, run the real-PostgreSQL smoke checks in
`server/tests/smoke_test_real_db.md`.

## 5. Phase 4 policy decisions

- Likes are supported for posts and comments; replies are not likeable.
- Reports start `pending`; a moderator may move them once to `resolved` or `dismissed`.
  Both review outcomes are terminal.
- Report records are retained. Because the schema uses restrictive target foreign keys,
  any content with a report remains undeletable after review.
- Moderator membership is granted only through trusted server/database operator access.
- The SQL Inspector is moderator-only, read-only, bounded to the in-memory history, and
  never executes SQL supplied by a client.
