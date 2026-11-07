# Health-a-thon Round 2 submission readiness

Checked on 3 November 2026 against the latest organiser email. The supplied
final deck and two-page template match the copies in `docs/presentations` byte
for byte. The draft files in this directory retain the final deck's 12-slide
sequence and the brief's two-page layout. They are drafts until the fields
below are completed and reviewed.

| Deliverable | Current state | Before submission |
| --- | --- | --- |
| Functional MVP | Local ghost-chair demo runs at `http://127.0.0.1:5173/`. `npm run check` passes 36 tests, lint, formatting and build. The ghost scenario proposes Chair 2 to OF-007 and Chair 3 to OF-011. | Agree with organisers on judge access. A localhost URL cannot be opened by evaluators. The app still lacks user authentication. |
| Final presentation | `OncoFlow_Phase_II_Final_Presentation_DRAFT.pptx` fills all 12 prescribed slides in order. Synthetic outcomes and current limitations are labelled. | Add team code, member roles, doctor details and actual feedback, contact email, judge MVP URL, video URL, repository URL, cost assumptions and public-availability decision. Review every claim against the running demo. |
| Two-page brief | `OncoFlow_Two-page_Solution_Brief_DRAFT.pptx` fills the two supplied pages without changing their section order or geometry. | Add member roles/institution, doctor details and actual feedback, judge MVP URL, video URL, repository URL and confirmed deployment estimate. |
| Demo video | Outside the current request. | Record a narrated walkthrough no longer than 6–7 minutes; test the shared link. |

## Evidence and claim boundaries

- The chair-recovery metrics are from fictional scenarios, not patient outcomes or a clinic pilot. The fixed case recovered 120 of 140 baseline idle chair-minutes and allowed 10 minutes of possible same-chair delay. Fifty varied fictional cases had median recovery of 101 minutes and median possible delay of 42 minutes after the 5 November scheduler corrections. See `../evidence/ghost-evaluation-2026-11-05.json` and `../EVIDENCE_LOG.md`.
- Google OR-Tools CP-SAT performs constraint optimisation. The application health endpoint reports `ai_enabled: false`; no trained or generative model is deployed. The evaluation panel may require a distinct AI component. Describe the built optimiser accurately and confirm this requirement with the organisers.
- No doctor or coordinator validation is recorded. Use the real walkthrough date, observations and changes only after it occurs.
- No production authentication, live HIS/LIS integration, real patient messaging or public judge deployment is present.
- The cost fields in the deck are intentionally unfilled until hosting and pilot scope are chosen. Do not present an unsupported estimate.

## Final quality gate

1. Fill all bracketed fields in both PPTX drafts. Run `rg '\\[' scripts/build_submission.py` to find the corresponding source text, then run `scripts/build_submission.py` with the bundled Python or another interpreter with `lxml` installed.
2. Have the doctor review the proposed ranking, nurse-capacity assumption, protected bookings and displacement follow-up; record their actual comments in `../EVIDENCE_LOG.md`.
3. Open both PPTX files and check every slide/page visually after editing. Keep the final deck's slide order and the brief's format unchanged.
4. Test the judge MVP link and credentials from a separate device or browser session. Test the video link when ready.
5. Replace `DRAFT` filenames for the submission copies after all fields and links are confirmed.

The local demo command is:

```sh
ONCOFLOW_SCENARIO=ghost ONCOFLOW_DB=data/ghost-final-demo.sqlite3 npm run dev
```

Use a new database filename if the scenario was previously exercised. The
ghost-chair walkthrough is in `../GHOST_SCHEDULER_DEMO.md`.
