# Manual milestone demonstration

Use a fresh synthetic database if OF-003 has already progressed. Do not delete
an existing file just to reset the demo; start with a new `ONCOFLOW_DB` path.

## Narrative

The coordinator sees where each fictional visit is blocked, records operational
events and checks the audit history. This milestone demonstrates visibility and
workflow checks. It does not automatically optimize clinic capacity.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Select OF-003 | Pending CBC, consultation and clearance prerequisites visible |
| 2 | In demo controls, mark CBC Final | Ready for consultation; clearance remains unset |
| 3 | Start consultation | With doctor; physical waiting count decreases |
| 4 | Complete consultation | Awaiting clinician clearance |
| 5 | Record clearance | Records an existing clinician decision |
| 6 | Mark pharmacy ready | Ready for chair |
| 7 | Select an available chair and start | Infusing; chosen chair occupied |
| 8 | Complete infusion | Discharged; chair available |
| 9 | Open audit history | Successful updates visible with timestamps |

If a patient is waiting nearby, confirm their return before seating. Occupied
chairs and missing prerequisites block the corresponding action.

To demonstrate an exception, change an infusing patient's required report to
Corrected before step 8. Readiness is invalidated and staff review is requested,
but the application does not automatically interrupt ongoing care.

## Questions for the clinical lead

- Which steps differ from the actual clinic's workflow?
- Can consultation precede some reports? Which prerequisites vary per visit?
- Who records clearance, pharmacy readiness and changes in visit status?
- Which resources limit capacity beyond the chair count?
- Which actions would save staff time and which would add data-entry work?

Record the review date, reviewer role, observations and requested changes.
Ask before attributing feedback or recording identifiable material.

## What the demonstration does not establish

Synthetic scenarios and automated tests do not establish reduced waiting time,
clinical effectiveness, production readiness or completed user validation.
