# Advisory scheduler: mentor walkthrough

Start with a fresh **fictional** clinic day so earlier demo actions do not
change the story:

```sh
ONCOFLOW_DB=data/mentor-scheduler-demo.sqlite3 npm run dev
```

Use a new filename each time you need a fresh day. Open
<http://127.0.0.1:5173/>. The app creates the file on first startup.

## Three-minute flow

1. Point to **Suggested chair plan**. OF-007 is eligible for Chair 2 now.
   OF-001 is already infusing in Chair 1 and is never moved. Other visits are
   absent because they lack a recorded prerequisite or are not on site.
2. Click **Review start** for OF-007. The patient and Chair 2 are selected.
   Explain that the computer recommends; the coordinator confirms. Click
   **Start infusion**. Chair 2 becomes occupied and the plan recalculates.
3. Select OF-003. Its CBC is pending. In **Demo event controls**, change CBC
   to **Final**. The patient is ready for consultation, not a chair: a final
   report does not grant treatment clearance.
4. Start and finish the consultation, record the clinician's existing
   clearance, then mark pharmacy ready. OF-003 now appears in the plan for an
   available chair. Click **Review start** to inspect the suggestion.
5. Before confirming, change OF-003's CBC to **Corrected**. The recommendation
   disappears and the visit asks for staff review. No infusion is started.

## What to say

"The app checks operational prerequisites and recomputes a proposed chair plan
when recorded status changes. It keeps active patients in their chairs and
limits simultaneous nurse starts. It does not read lab values or decide whether
treatment is safe. Staff supply clinical clearance and confirm every start."

## Questions for the mentor and doctor partner

- Which prerequisites vary by visit? Can some consultations precede reports?
- What chair types, nurse staffing and pharmacy constraints matter in practice?
- Where do scheduled infusion duration and patient availability come from?
- Which changes can be suggested, and which require direct staff confirmation?
- Is a plan relative to the current snapshot useful, or must it show appointment
  times and a real clock timeline before a pilot?

The two-nurse/15-minute setup and full-duration hold for active chairs are
provisional demo assumptions. Future starts are illustrative, not booked slots.
There is no AI model, real LIS connection, patient notification or measured
waiting-time improvement in this increment.
