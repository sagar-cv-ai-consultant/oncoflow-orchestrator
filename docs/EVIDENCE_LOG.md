# OncoFlow Phase II evidence log

Started 26 October 2026. No implementation, model performance, clinical validation, deployment, or measured benefit is claimed by this initial record.

| Date | Delivered change | Verification / result | Evidence location | Limitations / next action |
| --- | --- | --- | --- | --- |
| 26 October | Reviewed Phase I materials, Phase II email and required template; recorded scope and schedule | Workspace initially contained two presentations and no application source | BUILD_PLAN.md | Locate any existing code; clinician review pending |
| 26 October | Implemented milestone 01: React coordinator worklist, FastAPI service, SQLite persistence, report gates, staff-recorded clearance, manual chair occupancy and audit view | Eight automated backend tests passed; TypeScript check and production build passed | backend/tests/test_workflow.py, ../README.md | No AI, automatic scheduler, staff authentication, patient portal or clinical validation yet |
| 26 October | Browser walkthrough: OF-003 CBC changed from pending to final; started consultation; inspected audit history | Visit advanced to ready for consult and then with doctor; physical waiting count changed from 8 to 7; both updates visible in audit | evidence/milestone-01-audit.png | Fictional local data only; provisional workflow awaits clinical review |

## User validation records

Record date, role, scenario reviewed, observation, requested change, implemented response and follow-up. Obtain permission before including identifiable feedback or recordings. No reviews recorded yet.

## Evaluation records

Record source revision, dataset configuration, seeds, comparator definitions, observation window, raw output path, metrics and failures. Keep synthetic and real-setting evidence separate. No runs recorded yet.

## Model evaluation records

Record model/provider/version, prompt revision, test cases, expected actions, observed responses, validation outcomes, latency and costs. No runs recorded yet.

## Deployment and costs

Record actual services and pricing date, fixed hosting costs, AI and messaging usage assumptions, one-time setup effort, monthly facility estimate and known exclusions. No costs verified yet.

## Repository organization, 28 October 2026

The manual milestone was reorganized for the cloned repository. See MIGRATION.md for scope and ARCHITECTURE.md for the request flow. Original presentation files and historical evidence are retained. New validation: 13 automated tests, Ruff lint and formatting, Prettier formatting, strict TypeScript checking and production build passed in the preparation directory. Destination checks are recorded after local installation. No clinical validation or scheduling improvement is claimed.

Destination verification completed: all 13 tests, lint, formatting, TypeScript and production build passed inside the cloned repository. The one-command launcher started both services; HTTP checks verified the dashboard, API proxy, health flags and twelve seeded visits. Git metadata was unchanged during the copy and setup. No files were staged, committed or pushed.

## Advisory scheduling work, 29 October 2026

The working tree after v1.0.0 adds a deterministic chair recommendation service,
dashboard panel, and synthetic planned-duration fields. Recommendations use
recorded prerequisites, patient location, staff priority, chair occupancy and a
provisional two-nurse start capacity. Staff confirm actual starts through the
existing versioned command. This is not the proposed CP-SAT solver, an AI
model, an external integration or evidence of real-world benefit. Clinical
review and comparative evaluation remain pending.

Verification: 17 backend tests passed, Ruff lint and formatting passed,
Prettier and strict TypeScript checks passed, and the frontend production build
completed. The four new scheduler tests cover recorded eligibility, active-chair
pinning, nurse setup capacity, nearby-patient exclusion and replanning after
a confirmed start. No clinician walkthrough or measured outcome has occurred.

## Ghost-slot recovery, 3 November 2026

Added a second synthetic clinic scenario with four occupied chairs, two overdue
bookings and seven physically waiting patients. The scheduler proposes two
feasible replacements, explains exclusions, respects future protected bookings
and nurse start capacity, and uses a stable order: staff priority, appointment
due, time ready, arrival, visit ID. Staff confirmation revalidates the clinic
revision and proposal before starting a replacement and marking the old booking
for follow-up. A mock status-only LIS webhook rejects duplicate or older source
events and discards report values. A fixed already-tested patient can be
onboarded at the consultation stage.

The scripted comparison in `oncoflow.evaluation` reports 140 baseline idle
chair-minutes before the two original patients become ready, 120 chair-minutes
occupied by replacements in that same window, and 10 minutes of possible
extra same-chair wait for one displaced patient. These numbers come from one
deterministic fictional case, not a pilot or measured clinic benefit. No doctor
validation has yet been recorded for the ranking rule, capacity assumptions or
replacement policy. See `GHOST_SCHEDULER_DEMO.md` for the exact case and caveats.

Google OR-Tools CP-SAT now assigns patients jointly across immediate ghost
slots, maximizing feasible fills before applying the documented ranking.
A test constructs a case where greedy priority fills one chair while CP-SAT
fills two without violating duration or booking constraints. The solver has a
two-second limit and a deterministic fallback. This is narrower than the
full-day rolling optimizer proposed in Phase I and is not a trained model.

An additional 50-seed fictional robustness run varied candidate readiness,
staff priority, appointment due time and planned duration. The local run found
a median 101 recovered chair-minutes and a median 39.5 possible same-chair
delay minutes for displaced original bookings (p90 delay 90). This is a
scenario-model tradeoff, not observed clinic performance. It shows that the
permitted displacement window and rebooking policy need doctor review before
any real-setting claim.

The follow-up path was also exercised in an isolated integration test: after
one ghost-slot fill, the original patient completed recorded prerequisites,
the replacement finished, and the scheduler suggested a chair that fit before
the next protected booking. Staff confirmation started the original patient
without overriding that future booking. This is simulated workflow evidence,
not a real patient rebooking outcome.

## Scheduler corrections, 5 November 2026

An independent review identified a ready patient losing a due booking to a
ghost replacement, an objective that could rank a lower-priority patient ahead
of a higher-priority one, and inconsistencies in follow-up ordering and direct
start capacity checks. The scheduler now reserves a chair for any ready due
booked patient, protects later bookings even when their start time has passed,
and shows one recovery card per chair. Direct starts allow a ready patient to
use their own due booking after an earlier missed booking, move the earlier
booking into follow-up, and enforce nurse setup capacity. The CP-SAT objective
follows strict patient rank without a chair-position multiplier; the fallback
uses the same ordering. Follow-up recommendations use the five-step ranking.

`npm run check` passed 36 tests, Ruff, formatting, TypeScript and frontend
build. New regression tests cover the reported ready-booking case, priority
under one nurse slot, duplicate missed bookings, direct nurse capacity and
disabled demo routes in a direct API launch. The fixed fictional comparison
still reports 120 of 140 idle chair-minutes recovered and 10 minutes possible
same-chair delay. The 50-variant fictional run now reports median recovery of
101 minutes and median possible same-chair delay of 42 minutes (p90 90).
Results are saved in `evidence/ghost-evaluation-2026-11-05.json`. These remain
synthetic outputs, with no clinician validation or measured clinic benefit.
