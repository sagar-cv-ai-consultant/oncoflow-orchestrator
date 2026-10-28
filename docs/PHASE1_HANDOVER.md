> Historical Phase I specification. This describes requested functionality, not the implementation delivered in the manual milestone.

# OncoFlow Orchestrator — build a working hackathon prototype

You are building a demo-ready prototype for a healthcare operations hackathon
(KOITA, Use Case 04: clinic operations and patient flow). I need running code,
not a design document. Work in small commits, keep everything runnable with one
command, and write a README as you go.

## What the system does

Oncology day-care clinics run on hard sequential dependencies: a patient cannot
see the doctor or start chemotherapy until that day's lab reports are verified.
When labs are late, doctors idle, infusion chairs sit empty, and immunocompromised
patients wait for hours in crowded rooms.

OncoFlow listens to lab-report STATUS events, clears dependencies automatically,
tells patients when to come in, and re-solves infusion chair assignment whenever
the day changes.

## HARD SCOPE RULE (this is a judged guardrail — do not violate it)

The system is operational logistics only. It must NEVER read, store, parse,
display or reason about clinical values. Specifically:

- From a lab report, consume ONLY the status flag (HL7 v2 OBR-25 == "F", or
  FHIR DiagnosticReport.status == "final"). Discard OBX segments / Observation
  resources at the adapter boundary — do not even persist them.
- No risk scoring, no triage logic, no prediction of clinical outcomes.
  Patient priority is an integer flag set manually by staff in the EHR feed.
- "Extended stay" is a nurse's button press, never an inferred adverse reaction.
- Write a unit test asserting the adapter drops result values.

## Stack

- Python 3.11, FastAPI, Pydantic v2
- Redis (Streams for the event bus, hashes for live queue state)
- PostgreSQL + SQLAlchemy for the append-only audit log
- Google OR-Tools CP-SAT for chair assignment
- WebSockets for dashboard push
- React + Vite + TypeScript for the coordinator dashboard
- Everything runs via `docker compose up`; also provide a `make demo` path that
  runs a seeded simulation end to end
- pytest for tests

## Repository layout

oncoflow/
  adapters/        hl7_v2.py, fhir.py  -> normalise to one internal event
  core/
    events.py      event schemas + Redis Streams publish/consume
    readiness.py   dependency DAG + readiness gate + predicted ready time
    scheduler.py   CP-SAT chair allocation
    notify.py      WhatsApp/Twilio adapter + console stub
    metrics.py     W, U, G computation from the audit log
  api/             FastAPI app, REST + WebSocket
  sim/             mock LIS, synthetic clinic day generator, FIFO baseline
  dashboard/       React app
  tests/

## Domain model

Patient visit steps form a DAG per patient:
  ARRIVE -> PHLEBOTOMY -> LABS_FINAL -> CONSULT -> PHARMACY_PREP -> CHAIR -> INFUSE -> DISCHARGE

Entities:
- Patient(id, name_alias, priority_flag:int (manual, default 0), wait_location,
  walk_time_min)
- Panel(id, patient_id, code e.g. "CBC"/"CMP", t_draw, t_final_or_null, status)
- VisitStep(patient_id, step, prerequisites:list[step|panel], state)
- Chair(id, unit)
- Session(patient_id, chair_id, planned_start, planned_duration_min, state)

Persist every state transition to the audit log with a timestamp. The metrics
module reads only from that log.

## Readiness engine — implement exactly this

1. Hard gate. Step i has prerequisite set P(i). ready_i(t) is TRUE iff every
   d in P(i) has status == FINAL. This is a pure boolean AND. Nothing else
   may release a patient into the call-up queue.

2. Predicted ready time, used ONLY to time notifications:
       T_i = max over d in P(i) of ( t_draw[d] + Q90(TAT[panel_code(d)]) )
   where Q90 is the 90th-percentile turnaround time for that panel code,
   computed from the trailing 30 days of (t_final - t_draw) in the audit log.
   Use the 90th percentile, not the mean, so patients are rarely called early.
   Cold start: seed defaults CBC = 45 min, CMP = 75 min, make them config.

3. Expected start and the notification rule:
       S_i = max( T_i , t_free[resource] )        # doctor or chair
       notify(i)  iff  S_i - now <= tau_i + delta
   tau_i = the patient's walk time from their chosen waiting location,
   delta = safety buffer, default 5 min, config.

   The prediction NEVER overrides the gate. If a report is not final when
   predicted, the patient simply stays gated and gets a "still waiting" update.
   Test this case explicitly.

## Chair scheduler — CP-SAT model

Variables and constraints, re-solved on every relevant event:

- x[p][k] in {0,1}, chair assignment, with sum_k x[p][k] == 1 for each patient p
- s[p] integer start time (minutes from clinic open), with s[p] >= r[p]
  where r[p] is the readiness time from the engine
- For each (p,k): an OPTIONAL interval I[p][k] = [s[p], s[p] + d[p]) present
  iff x[p][k] == 1   (OR-Tools: NewOptionalIntervalVar)
- AddNoOverlap over {I[p][k] : all p} for each chair k   -> no double-booking
- AddCumulative over nurse set-up intervals [s[p], s[p] + e[p]) with demand 1
  and capacity N nurses -> limits simultaneous starts
- Patients already infusing: s[p] and k[p] fixed with AddHint + equality
- d[p] = scheduled regimen duration from the order feed + chair turnover
  constant. A nurse "extended stay" flag increases d[p] and triggers a re-solve.

Objective:
    minimise  sum_p w[p] * (s[p] - r[p])  +  beta * sum_p moved[p]

- w[p] derives from the manual priority flag only (e.g. 1 + 2*flag)
- moved[p] is a boolean that is 1 when p's chair differs from the chair the
  patient was already told about; beta penalises churn so the plan stays stable.
  Implement moved[p] via AddBoolOr / reification against the previous plan.
- Solver: 2-second time limit, warm start from the previous solution, rolling
  horizon over the remaining clinic day.

Re-solve triggers: report final, consult finished, extended-stay flag, no-show,
new walk-in added.

## Simulation (this is what gets demoed)

`sim/` must generate a synthetic 40-patient clinic day:
- 8-hour day, arrivals spread with a morning peak
- Panels: CBC (~80% of patients), CMP (~50%), lognormal turnaround times
  calibrated so median CBC ≈ 25 min and the tail reaches 90+ min
- Regimen durations drawn from a realistic mix (30 min to 6 h)
- 12 chairs, 4 nurses, both config
- Random events: 10% extended stays, 5% no-shows
- Fixed random seed, so the demo is reproducible

Provide TWO run modes over the SAME generated day:
  A) `baseline` — FIFO by arrival time, patient waits on-site throughout
  B) `oncoflow` — full readiness gate + notifications + CP-SAT

## Metrics — compute from the audit log, print a comparison table

- On-site wait:    W = mean(t_called - t_arrived)
- Chair utilisation: U = sum_p d[p] / (C * H), C chairs, H clinic hours
- Ghost-slot minutes: G = sum over chairs of idle minutes during which
  q > 0, where q = count of patients who were ready but not seated
- Also report: mean crowd size L (sample the waiting-room count every minute;
  sanity-check it against Little's Law L = lambda * W, they should match
  within a few percent — assert this in a test)
- Coordinator manual interventions count

Output a side-by-side table, baseline vs oncoflow, plus a CSV for charting.

## Dashboard

Single-pane coordinator view, updating live over WebSocket:
- A row per patient with state: DRAWN -> VERIFIED -> WITH DOCTOR ->
  AWAITING CHAIR -> INFUSING -> DISCHARGED
- A chair timeline (Gantt) for the day showing planned vs actual
- Pending-dependency column showing WHICH prerequisite is blocking (panel code
  and status only — never a value)
- Manual override controls: force-call a patient, pin a chair, mark extended
  stay, mark no-show
- A live counter for people physically in the waiting room

## Notifications

`notify.py` with a provider interface and two implementations: a console/log
stub (default, used in the demo) and a WhatsApp Business API / Twilio adapter
behind an env flag. Template messages: "come in now", "about 20 minutes",
"delay, please stay comfortable". Rate-limit to avoid spamming, and log every
send to the audit log.

## Acceptance criteria

1. `docker compose up` then `make demo` runs both modes and prints the metrics table.
2. CP-SAT re-solve completes in under 2 seconds for 40 patients and 12 chairs;
   include a timing assertion in the tests.
3. Injecting an extended stay mid-run visibly re-plans downstream chairs, and
   patients already seated are not moved.
4. A test proves no clinical value ever reaches storage or the UI.
5. A test proves a patient is never called while any prerequisite is non-final,
   including when the Q90 prediction was wrong.
6. Little's Law cross-check passes.
7. README documents the math above, the config knobs, and a 3-minute demo script.

Start by scaffolding the repo, the event schemas and the simulation, then the
readiness engine with its tests, then the scheduler, then the dashboard. Tell
me your plan before writing large amounts of code.