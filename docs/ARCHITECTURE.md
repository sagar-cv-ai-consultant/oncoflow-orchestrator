# Application structure

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| React components | Display clinic state, scheduling proposals and staff actions |
| `useClinic` | Polling, command submission state and user feedback |
| `ClinicApi` | Typed HTTP requests |
| FastAPI routes | HTTP validation, error mapping and dependency resolution |
| `ClinicService` | Dashboard and report-ingestion use cases |
| `PatientVisit` | Readiness, blockers and allowed transitions |
| `FHIRReportAdapter` | Extract operational report identifier and status |
| `ChairScheduler` | Detect overdue bookings and solve immediate assignments with CP-SAT |
| `SQLiteVisitRepository` | Atomic persistence, event idempotency and audit |

## Command flow

1. A component submits a manual action through `useClinic` and `ClinicApi`.
2. Pydantic validates `Command`, rejecting unknown fields.
3. The service delegates to a repository transaction.
4. The repository checks the event identifier and visit version, then reads
   occupied chairs while holding the SQLite write transaction.
5. `PatientVisit.apply` validates the transition and changes the entity.
6. The repository updates visit state and inserts an audit event atomically.
7. The client reloads the snapshot. Other screens poll every three seconds.

An identical event is acknowledged without a second write. Conflicting event
reuse or stale versions produce HTTP 409. Missing visits produce 404 and
blocked transitions produce 422. Invalid validation input is not echoed.

## Report flow

The demo report route and synthetic LIS webhook pass transient input through
`FHIRReportAdapter`. The webhook tracks a source sequence per visit and panel;
duplicate events are idempotent and older events are rejected.
Only the allowlisted normalized operational fields survive normalization.
Raw payloads, result values and observations are not passed to persistence.
Report availability never grants clinician clearance. Corrected or withdrawn
reports invalidate recorded readiness; ongoing sessions remain in place and
the UI flags unmet prerequisites for staff review.

## Lifecycle

`create_app` builds a FastAPI application without creating database files.
Startup creates the repository and service and seeds an empty database.
Repository operations open and close their own connections; there is no global
connection shared across worker threads. Tests use isolated temporary databases
and run the application lifespan explicitly.

The persistence format and REST paths remain compatible with the manual
milestone. The post-v1.0.0 working tree adds `ChairScheduler`, which reads
the visit snapshot and returns advisory plans and ghost-slot proposals in
`/api/state`. The scheduler itself does not mutate visits. When staff confirm
a ghost replacement, the repository locks the database, checks the clinic
revision, recomputes the proposal, validates the visit transition, updates
both bookings and appends one audit event atomically. The fictional clock and
initial mid-journey intake are demo-only tools.

## Extension points

The immediate ghost-slot planner uses CP-SAT with a deterministic fallback
and provisional capacity assumptions. A full-day planner, real appointment
and shift data,
source authentication, patient communication and a functional AI component
remain future work.
