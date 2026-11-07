# OncoFlow demo video: recording script

**Target duration:** about 5 minutes, below the organiser's 6–7 minute cap.
**Format:** narrated screen recording of the working local app. The clinic and
all patients are fictional. The draft uses a generated Indian English voice;
Sagar can replace it with his own narration if desired.
Use the final presentation only for the opening and results if desired; keep
most of the video on the working webpage.

## Prepare the demo

1. In the terminal currently running OncoFlow, press **Ctrl+C**. From the
   repository root, start a fresh fictional day with a database filename that
   has never been used:

   ```sh
   ONCOFLOW_SCENARIO=ghost ONCOFLOW_DB=data/video-demo-01.sqlite3 npm run dev
   ```

2. Open `http://127.0.0.1:5173/` and confirm it says **Connected locally**.
   The fictional clock should read **10:30**. Chair 2 should recommend OF-007;
   Chair 3 should recommend OF-011. If any of these differ, stop and choose a
   new database filename before recording.
3. Maximise the browser window, close unrelated tabs and notifications, and
   keep the pointer away from private information. Do one silent rehearsal.
4. On the Mac, press **Shift–Command–5**, choose **Record Selected Portion**
   or **Record Entire Screen**, and select your microphone in **Options**.
   Apple documents the recording controls at
   <https://support.apple.com/en-gb/102618>.

## Narrated walkthrough

### 0:00–0:37 — Team and problem

**On screen:** Show the title slide briefly, then open the OncoFlow webpage.

**Say:** “Hello, I’m Sagar Deyagond, Technical Lead for Team_vaidya, team code
9GGP74. Sindhura C is our Technical Developer, and Jatin Punera is our Doctor
Lead. We built OncoFlow Orchestrator for oncology day-care coordination. When a
patient booked for a chair cannot start on time, another patient may be ready
and waiting. A coordinator needs to see whether that chair can be used safely,
who should go next, and what happens to the original booking.”

### 0:37–1:12 — Fictional clinic day

**On screen:** Point to the summary counters and the Ghost Chair Recovery
section. Pause on the fictional clock at 10:30.

**Say:** “This is a fictional clinic day, with six chairs. Four are occupied.
Chairs 2 and 3 were booked for patients who still lack recorded prerequisites,
while six patients are in the waiting room. Waiting alone does not make a patient
eligible. The app tracks report availability, consultation, clinician clearance,
pharmacy readiness and whether the patient is on site. It never reads lab
values or decides whether treatment is clinically suitable.”

### 1:12–1:58 — Automatic recommendation and explanation

**On screen:** Show Chair 2 recommending OF-007 and Chair 3 recommending
OF-011. Open **Why other visits were excluded** on one card. Point to the
priority, duration and next protected booking. Do not approve yet.

**Say:** “The scheduler has already calculated two proposed replacements. It
checks whether each recorded prerequisite is complete, whether the planned
session and turnover fit before the next protected booking, and whether a nurse
can start the patient. The staff-supplied priority flag comes first. Ties use
appointment time, time ready, arrival and visit ID. Here the app explains why
other visits were excluded, and it does not propose the same patient for both
chairs. The actual chair assignment is calculated with Google OR-Tools CP-SAT,
a constraint optimiser. There is no trained prediction model in this MVP.”

### 1:58–2:33 — Human approval and displaced booking

**On screen:** Read the delay warning. Click **Confirm displacement and start**
for Chair 2. Wait for refresh. Point to OF-007 now infusing and **Displaced
bookings needing follow-up** for OF-003.

**Say:** “The warning matters: filling a chair can delay the original patient
if they become ready sooner than expected. A coordinator makes the final
decision. I’ll confirm Chair 2 now. The server checks the latest clinic state
again before it starts OF-007. OF-003 is marked for follow-up rather than
disappearing from the worklist. When OF-003 is ready, OncoFlow can suggest a
new feasible chair, and staff still confirm that move.”

### 2:33–3:01 — Audit and live updates

**On screen:** Click **Audit history** in the sidebar, find the ghost-slot
event, then return to the worklist.

**Say:** “The audit history records the coordinator’s action. Changes to
report status or visit state cause the recommendation to be recalculated. A
stale approval is rejected rather than applied to an outdated plan. We also
tested a corrected report: it removes an ineligible patient from future
suggestions and asks staff to review ongoing care.”

### 3:01–3:25 — Patient entering mid-journey

**On screen:** At the top of Ghost Chair Recovery, click **Add already-tested
patient**. Select the new OF-013 visit in the worklist and show that CBC is
already final and the next stage is consultation.

**Say:** “The system can also accept a patient who enters the workflow after
testing. This fictional patient arrives with the CBC report already final, so
the worklist begins at the consultation stage. The prototype receives only a
report status, not the report values.”

### 3:25–4:11 — Evidence and trade-off

**On screen:** Keep the dashboard visible, or briefly show slide 8 of the
final presentation with evaluation results.

**Say:** “We ran 36 automated tests across the workflow, scheduling and
approval checks. In one scripted fictional comparison, holding the two chairs
would leave 140 chair-minutes idle before the original patients are ready.
Confirmed backfill occupies 120 of those minutes, with 10 minutes of possible
extra same-chair wait for one original patient. Across 50 varied fictional
cases, median recovery was 101 minutes and median possible same-chair delay
was 42 minutes. These are scenario results, not measured clinic benefits. The
delay trade-off needs clinical review.”

### 4:11–4:57 — Safety, collaboration and close

**On screen:** Show the approval area and closing slide or title.

**Say:** “Our mentor encouraged us to focus on this scheduling decision and
validate its effect. We requested a clinical review from Jatin, but his
feedback has not arrived at the time of this recording, so we make no claim
of doctor validation. The current MVP uses fictional data and a local SQLite
store. It has no live hospital connection, patient messaging or production
access control. A protected pilot would need those controls and a
clinician-approved policy for priority and displacement. OncoFlow shows the
coordinator a feasible next step and keeps that decision under staff control.
Thank you.”

## Finish and share

1. Stop the recording and check that the voice is clear and the duration is
   below 7 minutes. Trim silent setup time; preserve the narrated actions.
2. Upload the file as an **Unlisted** YouTube video, or to a Drive file whose
   viewer permissions let the panel open it. YouTube says people with an
   unlisted link can watch without signing in; see
   <https://support.google.com/youtube/answer/157177>.
3. Open the link in a private browser window. Copy the tested link into the
   submission form. If the team changes the final presentation or two-page
   brief, replace their “link supplied in submission form” text with the link
   before the final upload if there is time.

**Before recording:** Do not claim that the doctor reviewed the workflow or
that the fictional recovery numbers were measured in a clinic. Keep the
recording on the synthetic demo; no real patient information belongs in it.
