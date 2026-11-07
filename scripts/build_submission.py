"""Fill the prescribed Health-a-thon templates without changing their layout.

Edit the content maps below after confirming team details and judge URLs, then
run this script from the repository root. It changes text only in existing
PowerPoint paragraphs and preserves slide order, shapes, styles, and geometry.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "presentations"
OUTPUT = ROOT / "docs" / "submission"
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

# Indexes are slide, text-bearing shape, paragraph, all starting at 1/0/0.
FINAL_TEXT: dict[tuple[int, int, int], str] = {
    (1, 2, 0): "OncoFlow Orchestrator",
    (1, 3, 0): "A coordinator-guided scheduler for oncology clinic chairs",
    (1, 4, 0): "TEAM NAME  Team_vaidya",
    (1, 5, 0): "TEAM CODE  9GGP74",
    (1, 6, 0): "HEALTH-A-THON 2026  •  FINAL SUBMISSION",
    (2, 2, 0): "Sagar Deyagond, Technical Lead; Sindhura C, Technical Developer. The team built and tested the local MVP.",
    (2, 2, 1): "Jatin Punera, Doctor Lead. Clinical workflow review was requested; feedback has not yet been received.",
    (2, 2, 2): "Team_vaidya is an independent hackathon team developing an oncology day-care operations prototype.",
    (3, 2, 0): "Oncology day care loses usable chair time when a booked patient cannot start on time while others wait.",
    (3, 2, 1): "Our fictional six-chair clinic has four chairs occupied, two overdue unusable bookings and seven waiting patients. This is a workflow test, not clinic prevalence.",
    (3, 2, 2): "Staff need a feasible next patient, a clear reason for selection, and a safe path for the displaced booking.",
    (4, 2, 0): "Primary user: day-care coordinator. The MVP reads staff-supplied priority and readiness from fictional visit records.",
    (4, 2, 1): "The coordinator reviews chair status, pending reports and waiting visits, then confirms a proposed replacement.",
    (4, 2, 2): "The worklist keeps the reason, exclusions and audit trail visible inside one operational view.",
    (5, 0, 0): "Solution Overview, Key Features & Impact",
    (5, 2, 0): "OncoFlow detects overdue unusable bookings and proposes eligible waiting patients for the open chair windows.",
    (5, 2, 1): "It checks recorded prerequisites, priority, arrival, nurse starts, treatment duration and future bookings.",
    (5, 2, 2): "Staff review a ranked proposal, approve it, and see the original booking move to follow-up for reallocation.",
    (5, 2, 3): "In one fictional case, 120 of 140 idle chair-minutes are recovered, with 10 minutes of possible same-chair delay.",
    (6, 0, 0): "Technology, Tools and AI Approach",
    (6, 2, 0): "React and TypeScript UI; FastAPI service; SQLite audit store; fictional patient and report-status data.",
    (6, 2, 1): "Google OR-Tools CP-SAT assigns feasible replacements jointly. It uses constraint optimisation; no trained model is present.",
    (6, 2, 2): "The solver has a two-second limit and fallback. The mock LIS webhook accepts status only. No live integration exists.",
    (6, 3, 0): "",
    (7, 2, 0): "Week 1: built the visit worklist, report gates, manual chair actions and audit trail.",
    (7, 2, 1): "Week 2: organised the repository, automated tests and repeatable local launch.",
    (7, 2, 2): "Week 3: added advisory scheduling and a coordinator recommendation panel.",
    (7, 2, 3): "Week 4: built ghost-slot recovery, CP-SAT assignment, approval checks and synthetic evaluation.",
    (7, 2, 4): "Still open: clinician validation, public judge access, live integration and patient communication.",
    (7, 3, 0): "",
    (8, 2, 0): "Thirty-six automated tests passed across workflow, scheduling and stale-state approval; build and lint checks passed.",
    (8, 2, 1): "Fixed fictional case: 120/140 idle chair-minutes recovered; 10 minutes possible same-chair delay.",
    (8, 2, 2): "Fifty varied fictional cases: median 101 minutes recovered; median 42 minutes possible delay; p90 delay 90.",
    (8, 2, 3): "Doctor review was requested from Jatin Punera. Feedback is pending; no clinical validation is claimed.",
    (8, 2, 4): "These are scenario-model outputs, not observed patient waits or clinic performance.",
    (8, 3, 0): "",
    (9, 2, 0): "The MVP uses fictional records. Status-only inputs discard laboratory values and clinical findings.",
    (9, 2, 1): "The solver may be wrong when readiness, duration or priority inputs are wrong. No autonomous clinical triage occurs.",
    (9, 2, 2): "A coordinator must approve each move; stale approvals fail and actions appear in the audit trail.",
    (9, 2, 3): "No authentication or production privacy controls yet. A pilot needs access control, consent and local policy review.",
    (10, 2, 0): "A pilot needs a protected host, role-based access, backups, operational owner and clinician-approved scheduling policy.",
    (10, 2, 1): "Integrate appointment, visit and laboratory status feeds after mapping local codes and testing event order.",
    (10, 2, 2): "Illustrative pilot setup: 80–160 engineering hours at ₹1,500/hour = ₹1.2–2.4 lakh; excludes hospital and clinician costs.",
    (10, 2, 3): "Prototype host: about $7/month. Pilot support: ₹6,000–12,000/month per facility, plus hosting and storage; no AI transaction fee.",
    (10, 2, 4): "Start with one day-care unit, measure chair use and delayed bookings, then expand only after validation.",
    (11, 2, 0): "Next: doctor walkthrough of priority and displacement rules, protected judge deployment, then a supervised single-unit pilot.",
    (11, 2, 2): "Public availability of solution information: Yes.",
    (12, 1, 0): "Team_vaidya  •  9GGP74",
    (12, 2, 0): "deyagondsagar@gmail.com  |  MVP and video links: submission form  |  Code: private",
}

BRIEF_TEXT: dict[tuple[int, int, int], str] = {
    (1, 0, 0): "Team_vaidya | OncoFlow Orchestrator",
    (1, 1, 0): "Vaidya",
    (1, 4, 2): "Sagar Deyagond, Technical Lead; Sindhura C, Technical Developer. Team_vaidya built this prototype.",
    (1, 4, 4): "Jatin Punera, Doctor Lead. Review requested; feedback pending.",
    (1, 4, 19): "In our fictional six-chair clinic, four chairs are occupied, two bookings cannot start, and seven patients wait. Coordinators need a safe replacement and follow-up plan.",
    (1, 6, 2): "OncoFlow detects ghost bookings and proposes feasible waiting patients. A coordinator approves each move. CP-SAT jointly allocates chairs; no trained model is used.",
    (1, 6, 9): "React, FastAPI, SQLite and Google OR-Tools CP-SAT. Fictional visit and status-only mock LIS data. No live integration.",
    (1, 6, 16): "Ghost detection; ranked reasons; capacity and future-booking checks; staff approval; audit and follow-up.",
    (2, 1, 2): "Built manual flow, audit and advisory scheduling, then CP-SAT ghost-chair recovery and synthetic evaluation. Live integration remains open.",
    (2, 1, 7): "36 tests passed. Fictional case: 120/140 idle chair-minutes recovered, with 10 minutes possible delay. Fifty variants: median 101 recovered, 42 delayed. Doctor feedback pending. No clinic benefit measured.",
    (2, 2, 2): "Fictional data; clinical values discarded. Staff set priority and approve moves. Stale approvals fail. A pilot needs authentication and policy sign-off.",
    (2, 2, 8): "Est. setup ₹1.2–2.4 lakh; host ~$7/mo; support ₹6–12k/mo per facility. Clinic fees extra.",
    (2, 2, 13): "MVP: link supplied in submission form",
    (2, 2, 14): "Video: link supplied in submission form",
    (2, 2, 15): "Other: team 9GGP74; code private",
    (2, 3, 0): "Team_vaidya | OncoFlow Orchestrator",
}


def fill_template(source: Path, destination: Path, changes: dict[tuple[int, int, int], str]) -> None:
    """Replace text in existing shape paragraphs while retaining PPTX geometry."""
    with ZipFile(source) as archive, ZipFile(destination, "w", ZIP_DEFLATED) as result:
        for member in archive.infolist():
            data = archive.read(member.filename)
            if member.filename.startswith("ppt/slides/slide") and member.filename.endswith(".xml"):
                suffix = member.filename.removeprefix("ppt/slides/slide").removesuffix(".xml")
                if suffix.isdigit():
                    slide_number = int(suffix)
                    tree = etree.fromstring(data)
                    shapes = tree.findall(".//p:sp", NS)
                    for shape_number, shape in enumerate(shapes):
                        paragraphs = shape.findall(".//a:p", NS)
                        for paragraph_number, paragraph in enumerate(paragraphs):
                            replacement = changes.get((slide_number, shape_number, paragraph_number))
                            if replacement is None:
                                continue
                            runs = paragraph.findall(".//a:t", NS)
                            if not runs:
                                raise ValueError(f"No text run at {slide_number}/{shape_number}/{paragraph_number}")
                            runs[0].text = replacement
                            for run in runs[1:]:
                                run.text = ""
                    data = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
            result.writestr(member, data)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fill_template(
        SOURCE / "PPT_Final_Teamplate_Health-a-thon 2026.pptx",
        OUTPUT / "OncoFlow_Phase_II_Final_Presentation_SUBMIT.pptx",
        FINAL_TEXT,
    )
    fill_template(
        SOURCE / "Two-page Solution Brief Template.pptx",
        OUTPUT / "OncoFlow_Two-page_Solution_Brief_SUBMIT.pptx",
        BRIEF_TEXT,
    )


if __name__ == "__main__":
    main()
