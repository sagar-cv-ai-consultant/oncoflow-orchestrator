# Application structure

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| React components | Display existing clinic state and collect manual actions |
| `useClinic` | Polling, command submission state and user feedback |
| `ClinicApi` | Typed HTTP requests |
| FastAPI routes | HTTP validation, error mapping and dependency resolution |
| `ClinicService` | Dashboard and report-ingestion use cases |
| `PatientVisit` | Readiness, blockers and allowed transitions |
| `FHIRReportAdapter` | Extract operational report identifier and status |
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

The demo report route passes the transient input through `FHIRReportAdapter`.
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
milestone. No scheduler or AI module is introduced by the refactor.

## Extension points

Scheduling and AI can later be added as separate services. They should propose
versioned commands that pass the same domain and transaction checks. The
current release remains the manual workflow demonstration.
