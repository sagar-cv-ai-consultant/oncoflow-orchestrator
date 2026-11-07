# Ghost-chair demo and evaluator defense

This is a fictional operational scenario for workflow review. It does not use
real patient data, interpret medical results or establish clinical benefit.

## Start a clean demo

From the repository root, choose a database filename you have not used before:

```sh
ONCOFLOW_SCENARIO=ghost ONCOFLOW_DB=data/ghost-demo-01.sqlite3 npm run dev
```

Open <http://127.0.0.1:5173/>. The seeded clinic clock reads **10:30**.
Four of six chairs are occupied. Chairs 2 and 3 were booked for OF-003 and
OF-004 at 10:15, but both still lack recorded prerequisites. Six patients
are physically waiting; only OF-007 and OF-011 are currently eligible for
those gaps. Later bookings on both chairs remain protected.

If another booked patient on that chair is ready and due, the chair is kept
for that patient. Multiple overdue unusable bookings on one chair produce one
recovery proposal; prior missed bookings join the follow-up queue if staff
confirm the replacement. Direct starts also check nurse setup capacity.

## Four-minute walkthrough

1. Point to the clinic overview: four occupied chairs and six waiting
   patients. Explain that waiting does not mean eligible for infusion.
2. In **Ghost chair recovery**, open **Why other visits were excluded**. Show
   the pending report, incomplete consultation, clearance, pharmacy, presence
   or booking reason. No lab values appear.
3. Show Chair 2 recommending OF-007. Its priority flag was supplied by staff;
   its planned session fits before the next protected booking. Chair 3
   recommends OF-011, rather than proposing OF-007 twice.
4. Read the possible same-chair delay warning, then click **Confirm
   displacement and start** for Chair 2. The server rechecks
   the current revision and all operational gates before updating both
   visits. Chair 2 becomes occupied; OF-003 appears under displaced bookings
   needing follow-up. Repeat for Chair 3 if time permits.
5. Open **Audit history**. The `ghost_slot_filled` event records the choice.
   The displaced booking stays visible. When its prerequisites are later
   complete and a gap fits before the next booking, OncoFlow suggests a new
   chair; staff still confirm the start. Return to the worklist and click
   **Add already-tested patient** to show a
   new fictional patient arriving with CBC already final, at the consultation
   stage rather than at the beginning of the journey.
6. Optional exception: use a separate fresh database, change OF-007's CBC to
   **Corrected** under its demo controls, and watch the ghost recommendation
   change. This sends a mock status-only LIS event. It does not automatically
   interrupt care or grant clearance.

## Measured synthetic case

```sh
PYTHONPATH=backend/src .venv/bin/python -m oncoflow.evaluation
```

The fixed case compares holding two booked chairs until their fictional
patients complete all prerequisites with staff-confirmed backfill at 10:30.
It assumes OF-003 becomes ready at 11:30 and OF-004 at 11:50. These times
are withheld from the scheduler and used only in the comparison.

| Metric | Fixed case result |
| --- | ---: |
| Baseline idle chair-minutes before original patients are ready | 140 |
| Chair-minutes occupied by the two replacements in that window | 120 |
| Possible extra same-chair wait for the displaced patients | 10 minutes total |

This is **one scripted scenario**, not an estimate of clinic-wide time saved.
It excludes the effort of rebooking displaced patients, actual duration
variation, chair compatibility, nurse shifts, patient contact and real-world
workflow validation. Do not present 120 minutes as observed benefit.

The same command also runs 50 seeded variations of the fictional day. In the
5 November local run, the median recovered chair time was **101 minutes**,
while the median *possible same-chair delay* for displaced patients was
**42 minutes** (90th percentile: **90 minutes**). This tradeoff is why
staff confirmation and an explicit displaced-patient follow-up queue matter.
The sample varies fictional statuses, priorities and durations; it does not
measure actual hospital flow. See the generated JSON in `evidence/` for the
exact run and assumptions.

## Questions to answer during evaluation

**Why did a patient get this chair?** Only visits with recorded reports,
consultation, clinician clearance and pharmacy readiness complete, and with
the patient on site, can be considered. The session plus turnover must fit
before the next protected booking; nurse start capacity must be available.
Among eligible visits, the order is staff priority, earlier appointment due,
longer wait since readiness, arrival, then visit ID.

**Does the software decide clinical criticality?** No. The priority flag is
entered by staff. No lab values or clinical risk scores enter the scheduler.

**What happens to the original patient?** Their booking is marked displaced,
they remain visible in the worklist and a follow-up queue. Once ready, the
scheduler can suggest a new feasible chair; staff confirm the start. The
dashboard shows a worst-case same-chair wait if the patient becomes ready
immediately. This version does not automatically contact the patient.

**What if the status changes during approval?** The approval includes the
clinic revision. The server recomputes the proposal in a write transaction;
stale or infeasible proposals return HTTP 409 and do not start infusion.

**Is this AI?** Immediate ghost-slot assignment uses the CP-SAT constraint
solver, a classical optimization method, with a deterministic fallback. It is
not a trained prediction model and does not provide clinical advice. The
Phase II presentation should name the exact optimization task and avoid
claiming the full-day solver from the Phase I pitch. Whether this alone meets
the contest's functional-AI requirement should be checked with the organisers.

## Doctor-partner review still needed

Confirm the priority source, tie-break order, grace period, expected duration
source, turnaround buffer, chair compatibility, nurse setup capacity and
handling of displaced bookings. Record review date, role, scenario feedback
and resulting changes in `EVIDENCE_LOG.md` before claiming user validation.
