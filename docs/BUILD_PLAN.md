> Historical sprint plan. Current implemented scope and startup instructions are documented in ../README.md. Scheduler and AI work remain deferred at the user's request.

# OncoFlow Phase II build plan

Planning baseline: 26 October 2026, Asia/Kolkata.

## Deadline

The participant guide, checked on 26 October, labels 10 October–7 November 2026 as “Build sprint & final submission”: https://healthathon.reskilll.com/guide

The Foundation page's results banner agrees on the sprint dates but its older timeline lists final submission on 8 November: https://www.koitafoundation.org/health-a-thon

Treat 7 November as the working submission date. Exact cutoff time and upload requirements remain unconfirmed. Internal completion target: 6 November. Latest organiser instructions take precedence.

## Starting position

- Phase I pitch and Phase II template are available locally.
- A handover specification describes intended functionality, not verified implementation.
- No application source files were present in this workspace at the initial inventory.
- Existing code elsewhere, team availability, and clinical workflow validation are pending.
- Do not claim past development milestones or user validation that did not occur.

## Product scope

One oncology outpatient/day-care unit. A coordinator tracks prerequisites, sees blocked visits, approves feasible queue changes, and recovers available consultation/chair capacity after disruptions.

Working journey: registration, required report availability, consultation, staff-recorded treatment clearance, pharmacy readiness, chair allocation, infusion, discharge. This is a provisional workflow for clinical-lead review. Required panels and dependencies are configurable per visit; same-day labs are not assumed mandatory for every patient.

Report finality is availability, not clinical clearance. A nurse or doctor supplies all clinical readiness decisions and priority flags. Predictions never release a prerequisite gate.

## Delivery slices

1. Foundation: domain state machine, allowlisted status adapter, persistent event audit, synthetic clinic-day fixture, readiness tests.
2. Complete basic journey: coordinator worklist, manual status updates, blocked-reason display, consultation queue, synthetic event controls, live refresh.
3. Scheduling: chair and nurse constraints, cancellation/backfill, delayed resources, ongoing sessions pinned, coordinator approval, infeasible-plan fallback.
4. Functional AI: operational text-to-action assistant for coordinator updates. Model output is a proposed structured action, checked against an allowlist and confirmed by staff before execution. Include ambiguous and forbidden requests in evaluation. Use synthetic operational data only. Provider/model choice and credentials remain pending. Do not count a mocked response as a functional AI demonstration.
5. Patient/caregiver view: status, estimated return window, acknowledgement, English and one clinic-selected language, staff-assisted fallback. In-app messaging first; external messaging optional.
6. Evidence and submission: repeatable baseline comparison, user walkthrough, cost assumptions, deployment, video, required presentation.

Prediction of readiness time is an optional enhancement if there is sufficient operational timestamp data. Synthetic evaluation demonstrates prototype behaviour only, not real clinical performance.

## Technical implementation proposal

React + TypeScript coordinator and patient views, Python FastAPI service, OR-Tools scheduler, persistent SQL audit store. Start with SQLite for a single-process local prototype and a database configuration that permits PostgreSQL for hosted use. Add Redis only if event processing needs an independent worker; retain replayable, uniquely identified events in SQL from the start.

Use a status-event simulator and spreadsheet import before live HIS/LIS integration. Adapter extracts allowlisted identifiers, report status, and timestamps only. Never log or persist the raw inbound clinical payload. Do not put raw report content into an AI prompt.

Choose and document one-command local startup after inspecting any existing source. Do not replace working Phase I infrastructure solely to match this proposal.

## Acceptance criteria

- End-to-end seeded day runs and can reset reliably.
- Missing, stale, corrected, or retracted prerequisites cannot silently make a visit ready. Corrected/retracted events invalidate pending recommendations and require staff review; ongoing care triggers a staff alert, not automatic interruption.
- Duplicate events are idempotent and out-of-order events cannot regress state silently.
- Report availability cannot set clinical clearance.
- No clinical values reach storage, logs, model prompts, or views through the status adapter.
- Recommendations check patient availability and return time, required clearance, pharmacy readiness, chair occupancy and staffing constraints.
- Infusing patients remain fixed during replanning.
- A solver timeout or infeasible result preserves the last valid plan and requests coordinator attention.
- Confirmation revalidates the proposal against current state; stale proposals cannot apply.
- Patient notifications are deduplicated and delivery/acknowledgement states are visible.
- AI proposals require staff confirmation and deterministic validation. Unauthorized actions fail closed.
- Demo dataset and results are reproducible; limitations are disclosed.

## Evaluation

Compare FIFO, a feasible coordinator-style heuristic, and OncoFlow on identical seeded exogenous events. Actual start-dependent events such as extended duration should be attached to the same patient, rather than artificially fixed to wall-clock time across policies.

Primary KPI: avoidable chair-idle minutes while at least one fully eligible, available patient could feasibly start. Include nurse capacity and all prerequisites in eligibility.

Other metrics: median and p90 readiness-to-service wait, actual physical waiting minutes from location intervals, completed visits, overtime, within-hours chair utilisation, patient reassignments, staff interventions, constraint violations, and solver latency.

Measure occupancy from actual in-room intervals. Do not equate arrival-to-call elapsed time with physical waiting. Do not assert Little's Law within a few percent for a finite nonstationary day. Report exact patient-minute/occupancy accounting over the same observation window instead.

AI evaluation: exact supported intent/field extraction, correct clarification or rejection on ambiguous/forbidden requests, attempted unauthorized changes, latency and cost. Separate mocked transport tests from real model evaluation. Preserve evaluation inputs and outputs without secrets.

Run several seeds and stressed scenarios. Do not invent targets or promise numerical improvement before evaluation.

## Schedule

| Dates | Deliverable |
| --- | --- |
| 26–27 October | Locate existing code, confirm workflow, lock scope, implement foundation |
| 28–30 October | Working coordinator journey with persistent status and audit |
| 31 October–2 November | Scheduler, disruptions, functional AI and patient acknowledgement |
| 3–4 November | Comparative evaluation, clinician/coordinator walkthrough, fixes |
| 5 November | Deployment rehearsal, cost sheet, deck draft and video |
| 6 November | Final checks and submission-ready package |
| 7 November | Deadline contingency, subject to official cutoff confirmation |

If time slips, defer external messaging, extra languages, historical prediction and live integrations before reducing correctness or evaluation.

## User and clinical lead contributions

- Location of existing code, if any.
- Team name/code, roles, expertise and contact details.
- Doctor partner and availability for a workflow review and later walkthrough.
- Actual clinic dependencies, capacity, staff responsibilities and scheduling rules.
- Latest submission instructions and assessment rubric when received.
- Review of costs, deployment destination and public-sharing preference before publication.

## Submission evidence

Maintain EVIDENCE_LOG.md during development. Follow the supplied Phase II presentation structure. Include only observed progress; distinguish implemented, simulated, externally integrated and planned capabilities.
