# OncoFlow Orchestrator: independent review brief

Prepared 3 November 2026 from the user's messages, the Phase 1 handover,
the mentor transcript, organiser emails and the current repository. This is a
review aid, not a claim that every original idea was implemented. The draft
submission files are in `docs/submission/`.

## 1. Problem supplied by the hackathon

Track: **Clinic Operations & Patient Flow**. Busy outpatient clinics must
coordinate doctors, nurses, front desk and care coordinators around
appointments, arrivals, no-shows, walk-ins, delayed investigations, cancelled
slots and changing clinical priorities. The stated aim is to improve patient
flow, use vacant slots, identify bottlenecks and give timely recommendations
without disrupting care or existing workflows.

The team's chosen setting is oncology day care, with a particular focus on
infusion chair allocation after report, consultation and pharmacy steps.

## 2. Original Phase 1 handover: proposed system, not built scope

The handover text shared by the user proposed a much broader application:

- Track each visit through arrival, phlebotomy, final lab status,
  consultation, pharmacy preparation, chair, infusion and discharge.
- Ingest only lab **status** (for example, FHIR DiagnosticReport `final`),
  discarding result values at the adapter. A final report never implies a
  clinician has cleared treatment. Clinical priority comes from staff, not
  software risk scoring.
- Use historical lab turnaround times to estimate notification timing, but
  never use a prediction to bypass a hard readiness gate.
- Re-solve a full-day chair schedule with Google OR-Tools CP-SAT. The proposed
  model included no chair overlap, nurse start capacity, pinned active
  sessions, duration and turnover, priority weights, move penalties and a
  two-second solver limit.
- Simulate 40 patients, 12 chairs and 4 nurses, comparing FIFO against the
  proposed scheduler with wait, utilisation and ghost-slot metrics.
- Add a live dashboard, audit log, notification adapters, Redis,
  PostgreSQL, WebSockets and a Docker Compose launch.

These were **aspirational Phase 1 instructions**. The current app does not
implement the full-day model, notification timing, 40-patient comparison,
Redis, PostgreSQL, WebSockets, Docker Compose or patient messages. Reviewers
should not infer those features from the handover or the Phase 1 pitch deck.

## 3. Mentor meeting and the user's later priority

The mentor asked the team to concentrate on the scheduler as the strong
demonstrable feature. The specific scenario raised by the user after the call
was: four chairs in use, two booked chairs become unusable because their
original patients are not ready, and seven other patients are waiting. The
system should explain **who gets each chair and why**.

Questions the user asked explicitly:

1. Is the choice based on criticality, a doctor's input or a coordinator's
   input?
2. If waiting patients have equal priority, how is the tie broken?
3. What happens to the original booked patients after a chair is reassigned?

The mentor also stressed live status tracking, updates when a patient enters
mid-journey with tests already completed, one level of validation, and using
realistic synthetic data if real data is unavailable. Handwriting and voice
recognition were discussed as later-stage ideas unless accuracy could be
validated. The user then asked to build the scheduler first and to keep the
last five days focused on its critical functions.

## 4. Phase 2 organiser requirements supplied by the user

The final evaluation asks for four deliverables:

1. A **functional MVP** that evaluators can access and test, with links and
   access instructions.
2. A **final presentation** using the prescribed 12-slide template in its
   original order and structure. The theme may change, but the sequence and
   format must remain.
3. A **two-page solution brief** filled in the prescribed two-page template,
   with no structure or format changes.
4. A narrated **demo video** of no more than 6–7 minutes. The user excluded
   video production from the latest readiness request.

The organisers asked for actual build progress, doctor and technical-partner
collaboration, validation, safety, deployment and sustainability. The panel is
two doctors and one technology expert. The user said only five days remained
on 3 November; the latest email did not give an exact submission timestamp.

## 5. Current implemented MVP (local working tree)

The tagged `v1.0.0` is the manual workflow milestone. Scheduler changes after
that tag remain uncommitted locally. The current app is React/TypeScript with
FastAPI and SQLite. It launches locally with one command and contains only
fictional visit data.

Implemented behaviour:

- Coordinator worklist, prerequisite blockers, consultation, staff-recorded
  clinical clearance, pharmacy readiness, chair start/completion and audit.
- Status-only mock lab input; the adapter drops report values. Duplicate and
  stale mock source events are handled.
- A ghost scenario with six chairs total, four occupied, two overdue unusable
  bookings (Chairs 2 and 3), seven physically waiting patients and two
  immediately feasible replacements.
- The scheduler checks recorded reports, consultation, clearance, pharmacy,
  patient presence, chair availability, expected duration plus turnover,
  protected later bookings and provisional nurse start capacity.
- CP-SAT jointly assigns immediate ghost gaps, with a two-second limit and a
  deterministic fallback. It does **not** optimise the complete clinic day.
- Priority is supplied by staff. The deterministic ordering is staff
  priority, earlier appointment due time, longer time ready, earlier arrival,
  then visit ID. The software does not infer medical criticality.
- The interface shows proposals and exclusion reasons. A coordinator must
  click **Confirm displacement and start**. The server rechecks the clinic
  revision and feasibility in a transaction before changing state.
- The original booking becomes a visible displaced follow-up. A later chair
  may be recommended once that patient is ready; staff still confirm it.
- A fictional already-tested patient can enter at a later workflow stage.

For a fresh demo, run from the repository root:

```sh
ONCOFLOW_SCENARIO=ghost ONCOFLOW_DB=data/ghost-review-NEW.sqlite3 npm run dev
```

Use a new database name to get the initial fictional state. Open
`http://127.0.0.1:5173/`. The page should show Chair 2 recommending OF-007
and Chair 3 recommending OF-011 at the fictional clock time 10:30. The
recommendations appear automatically; actual moves require staff approval.
The detailed click-through is in `docs/GHOST_SCHEDULER_DEMO.md`.

## 6. Evidence and limitations to scrutinise

- `npm run check` passed on 5 November: 36 automated tests, Ruff, formatting,
  TypeScript and production frontend build. Local HTTP checks returned a 200
  page and the expected two chair recommendations.
- One fixed **fictional** comparison reported 140 baseline idle chair-minutes
  before the original patients become ready, 120 occupied by replacements,
  and 10 minutes of possible extra same-chair wait for an original patient.
- Fifty varied **fictional** cases reported median 101 chair-minutes
  recovered and median 42 minutes possible same-chair delay, with p90 delay
  of 90 minutes after the scheduler corrections. The raw record is in
  `docs/evidence/ghost-evaluation-2026-11-05.json`.
- These are modelled scenario outputs, not observed clinic benefit or patient
  waiting-time reduction. The assumptions about duration, nurse capacity,
  grace period, priority and acceptable displacement need doctor review.
- No doctor or coordinator walkthrough feedback is recorded yet. The user
  has emailed the doctor partner and will share comments when received.
- No real HIS/LIS connection, patient messaging, trained AI model,
  authentication or public judge deployment exists. The `/api/health`
  endpoint reports `ai_enabled: false`. CP-SAT is constraint optimisation;
  whether it satisfies the contest's functional AI requirement is unresolved.
- The current unauthenticated demo should not be exposed directly to the
  public internet. The user plans to ask the organiser about judge access.
- Draft submission decks are in `docs/submission/`; team details, doctor
  feedback, costs and final links remain placeholders.

## 7. Independent review questions

Please inspect the code and tests, rather than accepting the descriptions
above as proof. In particular:

1. Can a non-ready, off-site or clinically uncleared patient ever be proposed
   or started through any API path?
2. Are the CP-SAT objective and constraints consistent with the stated
   ranking, nurse limit, protected bookings and duration fit? Does the
   fallback preserve the same safety constraints?
3. Can a stale approval or concurrent action double-book a chair or lose a
   displaced booking?
4. Does corrected or withdrawn report status invalidate pending suggestions
   without silently interrupting a patient already receiving care?
5. Does the synthetic evaluation compare equivalent alternatives and report
   the cost to displaced patients clearly?
6. Are the draft slides and brief accurate about what is built, simulated,
   unvalidated and still planned?
7. What is the smallest safe improvement before submission, given the short
   time remaining?

Do not make changes, commit or push during an independent review unless the
user separately asks for that work.
