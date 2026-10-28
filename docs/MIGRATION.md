# Local repository migration

Prepared on 28 October 2026 for `oncoflow-orchestrator`.

## Scope

- Copy the manual milestone into the existing cloned repository.
- Preserve REST routes, seed visits, workflow rules, dashboard content and CSS.
- Move backend code to `backend/src/oncoflow` and tests to `backend/tests`.
- Encapsulate workflow in `PatientVisit`; separate persistence, application
  use cases, status adapter and HTTP transport.
- Split the existing React page into components, a hook and typed API client.
- Move source presentations to `docs/presentations` without modifying them.
- Move existing planning, evidence and screenshots under `docs`.
- Add repeatable formatting, lint, test and build commands.

## Small robustness improvements

- Database initialization occurs at startup, not Python import time.
- The default database path is anchored to the repository root.
- Malformed non-string report statuses return a redacted validation error.
- Client command submission uses an immediate in-flight guard.
- Older polling responses cannot overwrite a newer revision in the UI.
- Process launchers resolve the current checkout and platform's interpreter.

These changes preserve the intended manual workflow. Automated scheduling and
AI are disabled. No existing patient database is reset or migrated by copying
the repository. The destination starts with a fresh fictional day.

## Preservation

The original parent-folder files remain intact. The clone's `.git` directory,
remotes, branch and index are retained. No files are staged, committed or pushed.
Generated dependencies, build outputs, databases and caches are ignored.

Browser automation was unavailable for a new visual walkthrough during this
migration. Markup and styles are preserved; the frontend is checked by strict
TypeScript and a production build. The earlier screenshot in `docs/evidence`
documents the pre-refactor manual demonstration, not a new browser test.
