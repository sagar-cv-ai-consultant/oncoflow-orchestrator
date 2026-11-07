# OncoFlow Orchestrator

Team_vaidya's oncology clinic-operations prototype for Health-a-thon 2026.
The tagged **v1.0.0** is the manual workflow milestone. The current working
tree adds an **advisory automated chair scheduler** and a ghost-slot recovery
demo. It detects overdue unusable bookings, assigns feasible waiting patients
across those chairs with Google OR-Tools CP-SAT,
and rechecks the plan when staff confirm a replacement. AI assistance, live
HIS/LIS integration, and patient messaging are not implemented.

Only fictional patient data belongs in this prototype. It is not a clinical
decision system or a production deployment.

## Requirements

- Python **3.10 or newer**. The migrated repository was tested with Python 3.12.
- Node.js **20.19+**, or Node.js **22.12+** on the Node 22 release line.
- npm, supplied with Node.js.

No Docker, Redis, PostgreSQL, messaging credentials, or AI API key is needed.

## First-time setup

Run commands from the cloned repository root:

```sh
cd /Users/sagardeyagond/sagar_dir/hackathon/koita/oncoflow-orchestrator
python3 --version
```

If the displayed Python is older than 3.10, use a newer interpreter such as
`python3.12` instead of `python3` in the next command.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm ci
```

On Windows, use `py -3 -m venv .venv` and
`.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`.
The npm commands select the platform's virtual-environment interpreter.

## Run the application

```sh
npm run dev
```

This starts both services from one command:

- Dashboard: <http://127.0.0.1:5173/>
- Service health: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

Keep the terminal open. Press **Ctrl+C** to stop both services.
If the previous app is still running in the parent directory, stop it first:
both versions use ports 5173 and 8000. Open the dashboard URL rather than
opening `frontend/index.html` as a file.

## Repository layout

```text
oncoflow-orchestrator/
├── backend/
│   ├── src/oncoflow/
│   │   ├── adapters/fhir.py  # Status-only report input
│   │   ├── api.py            # HTTP routes, errors and startup
│   │   ├── config.py         # Database and demo configuration
│   │   ├── domain.py         # PatientVisit entity and transition rules
│   │   ├── evaluation.py     # Reproducible synthetic case comparison
│   │   ├── exceptions.py     # Explicit application errors
│   │   ├── fixtures.py       # Fictional seed visits
│   │   ├── repository.py     # SQLite transactions and audit persistence
│   │   ├── scheduler.py      # Advisory planning and CP-SAT ghost allocation
│   │   ├── schemas.py        # Validated command contracts
│   │   └── service.py        # Application use cases
│   └── tests/                # Workflow and regression tests
├── frontend/
│   ├── src/
│   │   ├── components/       # Worklist, visit details, summary and audit UI
│   │   ├── hooks/            # Polling, commands and feedback state
│   │   ├── services/         # Typed HTTP client
│   │   ├── App.tsx
│   │   ├── constants.ts
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   └── types.ts
│   ├── index.html
│   ├── tsconfig.json
│   └── vite.config.ts
├── docs/
│   ├── presentations/       # Phase I deck and supplied submission templates
│   ├── evidence/            # Existing demonstration screenshots
│   ├── ARCHITECTURE.md
│   ├── BUILD_PLAN.md
│   ├── DEMO_GUIDE.md
│   ├── EVIDENCE_LOG.md
│   └── MIGRATION.md
├── scripts/                  # Local process and Python command runners
├── .env.example
├── package.json
├── package-lock.json
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

Runtime folders `.venv/`, `node_modules/`, `data/`, and `dist/` are ignored by
Git. They are created locally, not copied into commits. There is no nested
repository or change to the clone's existing Git history.

## Code flow and object-oriented design

The React interface calls `ClinicApi`; `useClinic` owns synchronization and
feedback. FastAPI validates incoming commands and delegates to `ClinicService`.
`SQLiteVisitRepository` loads a `PatientVisit`, checks its version and event
identifier, applies the entity's transition rules, and saves the visit and
audit event in one transaction.

`PatientVisit` owns readiness and transition rules, `FHIRReportAdapter` owns
status filtering, and the repository owns persistence. React uses idiomatic
function components and hooks. Classes are used where they express a useful
responsibility, rather than adding inheritance to presentation components.

See [architecture](docs/ARCHITECTURE.md) for the full request flow.

## Tests and coding standards

```sh
npm test                 # Python workflow and regression tests
npm run lint             # Ruff checks and strict TypeScript checking
npm run format:check     # Python and frontend formatting checks
npm run build            # TypeScript check and frontend production build
npm run check            # All checks above
npm run format           # Apply consistent formatting
```

Python uses four-space indentation, type annotations, focused classes,
docstrings, sorted imports, and a 79-character line limit. Ruff checks include
PEP 8-related errors, unused code, and import ordering. TypeScript uses strict
checking and unused-variable checks. Prettier formats frontend code and scripts.
Tool versions and frontend dependency resolution are recorded in the
requirements files and lockfile.

Tests cover the complete manual visit journey, missing prerequisites,
separation of report finality and clearance, duplicate and stale events,
corrections during ongoing care, concurrent chair assignment, persistence,
input redaction, and clinical-value exclusion from the status adapter.
Scheduler tests cover readiness gating, occupied-chair pinning, nurse-start
capacity, nearby patients and replanning after a confirmed start.

`npm run build` creates frontend assets in `dist/`. A production backend and
hosted deployment are not configured by that command.

## Database and configuration

The default database is `data/oncoflow.sqlite3` inside **this repository**.
It is created at service startup and initially contains twelve fictional
visits and six demo chairs. Updates survive restarts. A fresh clone starts
with a fresh fictional day; the parent folder's database is not imported.

Set `ONCOFLOW_DB` in the terminal to use another file. Relative paths resolve
against the repository root, not the terminal's current directory:

```sh
ONCOFLOW_DB=data/review-02.sqlite3 npm run dev
```

`.env.example` documents the setting. The application does **not** automatically
load `.env` files. Do not commit runtime databases or credentials.

For the ghost-chair demo, use a **new** database filename and the ghost
scenario flag. A database retains the scenario selected when it was created:

```sh
ONCOFLOW_SCENARIO=ghost ONCOFLOW_DB=data/ghost-demo-01.sqlite3 npm run dev
```

This seeds four active chairs, two overdue unusable bookings, seven physically
waiting patients, and two feasible replacements. The dashboard shows the
fictional clinic clock, reasons for exclusion, and a staff confirmation action.
See [ghost-chair demo and defense](docs/GHOST_SCHEDULER_DEMO.md).

`npm run dev` binds both services to `127.0.0.1` and enables the fictional
`/api/demo/*` controls for local review. A direct API launch leaves those
controls disabled unless `ONCOFLOW_LOCAL_DEMO=1` is set. Other API actions
also have no user authentication, so this prototype must not be published on
the open internet. Add access control before providing a hosted evaluator URL.

## Demonstrate the workflow

1. Open OF-003 and inspect its pending CBC report.
2. Expand **Demo event controls** and set CBC to **Final**.
3. Start and complete the consultation.
4. Record clearance already supplied by a clinician, then pharmacy readiness.
5. Confirm the patient's return if needed, select a free chair, and start.
6. Complete infusion and discharge, then inspect the audit history.

For an exception scenario, change a report to **Corrected** during infusion.
The UI requests staff review without automatically interrupting ongoing care.
See the [demo guide](docs/DEMO_GUIDE.md) for the narrative and scope caveats.

## Automated scheduling in the current working tree

The dashboard's **Suggested chair plan** is calculated by `ChairScheduler` on
every state read. A visit enters the plan only when required reports are final,
consultation is complete, clinician clearance and pharmacy readiness are
recorded, and the patient is in the waiting room. It sorts eligible visits by
staff-set priority, appointment due time, ready-since time, arrival and visit
ID. It assigns the
earliest available chair while limiting simultaneous nurse setup starts to two
per 15 minutes. Active infusions keep their chairs. The planning horizon is
eight hours from the current snapshot; the expected duration is a fictional
fixture value, defaulting to 90 minutes for visits saved before this change.

These nurse and duration assumptions are provisional and require clinic review.
The plan is **advisory**: future times are illustrative, no chair is reserved,
and a coordinator must review and confirm an immediate start. The existing
versioned command rechecks readiness, occupancy, protected bookings and nurse
start capacity at confirmation time. A report correction or other status
change removes an ineligible visit from the
next plan. See [scheduler demo](docs/SCHEDULER_DEMO.md) for a short walkthrough.

In the ghost scenario, a booking more than five minutes overdue becomes a
possible gap only if the booked patient is not ready or on site. The scheduler
checks that a replacement's planned duration plus ten-minute turnover fits
before the next protected booking and that a nurse setup slot is available.
Eligible patients are ranked by staff-set priority, appointment due time,
ready-since time, arrival and stable visit ID. The general follow-up plan uses
the same order. A ready patient with a due booking retains that chair;
multiple missed bookings on one chair produce one recovery card. Confirming a
replacement starts
that fictional infusion and marks the old booking as displaced for follow-up,
in one audited transaction. A stale proposal is rejected. The synthetic LIS
webhook accepts report-status events, rejects duplicate or older source
sequences, and discards report values before storage. CP-SAT maximizes the
number of feasible immediate fills before applying the documented ranking;
a deterministic fallback remains if the solver cannot return a plan within
two seconds.
When a displaced visit later becomes ready and an open interval fits before
the next protected booking, the dashboard suggests a new chair for staff to
review. A future booking cannot be silently overridden by a manual start.

Run the fixed case comparison with:

```sh
PYTHONPATH=backend/src .venv/bin/python -m oncoflow.evaluation
```

This one fictional case reports 120 recovered chair-minutes against holding
the two booked chairs and a possible 10-minute same-chair delay for one
displaced patient. These are scenario calculations, not observed clinic gains.
The command also runs 50 seeded variations and reports the spread of recovered
chair time and possible same-chair delay. The latter is a material tradeoff,
not a measured patient outcome.

## Current limits

- Local synthetic demo only. No authentication, role verification or verified
  clinician identity. Do not expose it to a network or use real patient data.
- CP-SAT solves immediate ghost-slot allocation only; the full-day rolling
  optimizer from Phase I is not implemented. There is no trained model. The
  app does not predict clinical outcomes or automate patient communication.
  Appointment and duration fields are
  fictional; doctor calendars, chair types and nurse shifts are not modeled.
  Actual starts require staff confirmation.
- Three-second polling, rather than WebSocket updates.
- A FHIR-shaped **demo** adapter and mock status webhook, not a production
  HIS/LIS integration. It sequences synthetic source events but has no source
  authentication, identity mapping or HL7 ingestion.
- Audit records are append-only through the application, not tamper-proof.
- No measured clinical benefit, real-world pilot, or clinician validation is
  claimed. Workflow assumptions still need the doctor partner's review.

The historical plan and evidence are in [docs](docs/EVIDENCE_LOG.md).
The v1.0.0 repository migration predates this advisory scheduling increment.
