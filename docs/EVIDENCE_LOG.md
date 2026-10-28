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
