"""Deterministic, advisory chair scheduling for a synthetic clinic day.

The plan is recalculated from current visit state. It never changes a visit or
books a chair; the coordinator confirms an immediate start separately.
"""

from dataclasses import dataclass

try:
    from ortools.sat.python import cp_model
except ImportError:  # The deterministic fallback keeps local review possible.
    cp_model = None

from .config import (
    CHAIR_COUNT,
    CHAIR_TURNOVER_MINUTES,
    GHOST_GRACE_MINUTES,
    NURSE_SETUP_MINUTES,
    NURSE_START_CAPACITY,
)
from .domain import PatientVisit


@dataclass(frozen=True)
class ScheduleSettings:
    """Provisional operational capacity to review with the clinic partner."""

    chairs: int = CHAIR_COUNT
    nurses_for_starts: int = NURSE_START_CAPACITY
    setup_minutes: int = NURSE_SETUP_MINUTES
    horizon_minutes: int = 480
    turnover_minutes: int = CHAIR_TURNOVER_MINUTES
    ghost_grace_minutes: int = GHOST_GRACE_MINUTES


class ChairScheduler:
    """Place eligible visits at the earliest feasible chair and nurse start."""

    def __init__(self, settings: ScheduleSettings | None = None) -> None:
        self.settings = settings or ScheduleSettings()
        if (
            min(
                self.settings.chairs,
                self.settings.nurses_for_starts,
                self.settings.setup_minutes,
                self.settings.horizon_minutes,
            )
            < 1
        ):
            raise ValueError("Scheduling settings must be positive.")

    def recommend(
        self, visits: list[PatientVisit], now_minute: int = 150
    ) -> dict:
        """Return a fresh proposal; only recorded operational state is used."""
        settings = self.settings
        chair_free = {chair: 0 for chair in range(1, settings.chairs + 1)}
        pinned = []
        for visit in visits:
            if not visit.infusing:
                continue
            if visit.chair not in chair_free:
                raise ValueError("An active visit has an unknown chair.")
            # No actual end estimate exists. Reserving the full planned
            # duration from now is conservative and visible in the proposal.
            chair_free[visit.chair] = visit.scheduled_duration_minutes
            pinned.append({"patient_id": visit.id, "chair": visit.chair})

        protected_start = {
            chair: settings.horizon_minutes
            for chair in range(1, settings.chairs + 1)
        }
        for visit in visits:
            if (
                visit.booking_status != "active"
                or visit.infusing
                or visit.booked_chair is None
                or visit.booked_start_minute is None
            ):
                continue
            chair = visit.booked_chair
            protected_start[chair] = min(
                protected_start[chair], visit.booked_start_minute
            )

        eligible = sorted(
            (
                visit
                for visit in visits
                if visit.stage == "ready_for_chair"
                and visit.location == "waiting_room"
                and visit.booking_status != "active"
            ),
            key=lambda visit: self._rank(visit, now_minute),
        )
        nurse_starts = [
            visit.infusion_started_minute - now_minute
            for visit in visits
            if visit.infusing
            and visit.infusion_started_minute is not None
            and visit.infusion_started_minute
            <= now_minute
            < visit.infusion_started_minute + settings.setup_minutes
        ]
        recommendations = []
        unscheduled = []
        for visit in eligible:
            candidates = []
            for chair, free in chair_free.items():
                start = self._next_nurse_start(free, nurse_starts)
                end = (
                    now_minute
                    + start
                    + visit.scheduled_duration_minutes
                    + settings.turnover_minutes
                )
                if end <= protected_start[chair] or (
                    protected_start[chair] == settings.horizon_minutes
                    and start + visit.scheduled_duration_minutes
                    <= settings.horizon_minutes - now_minute
                ):
                    candidates.append((start, chair))
            if not candidates:
                unscheduled.append(visit.id)
                continue
            start, chair = min(candidates)
            recommendations.append(
                {
                    "patient_id": visit.id,
                    "chair": chair,
                    "start_in_minutes": start,
                    "duration_minutes": visit.scheduled_duration_minutes,
                    "priority": visit.priority,
                    "reason": (
                        "Recorded prerequisites complete; patient on site; "
                        "chair and nurse start available."
                    ),
                }
            )
            nurse_starts.append(start)
            chair_free[chair] = start + visit.scheduled_duration_minutes

        return {
            "recommendations": recommendations,
            "pinned": pinned,
            "unscheduled": unscheduled,
            "assumptions": {
                "nurses_for_starts": settings.nurses_for_starts,
                "setup_minutes": settings.setup_minutes,
                "horizon_minutes": settings.horizon_minutes,
                "active_chair_remaining_minutes": "full planned duration",
            },
        }

    def ghost_slots(self, visits: list[PatientVisit], now: int) -> list[dict]:
        """Identify overdue bookings and jointly assign feasible patients."""
        occupied = {visit.chair for visit in visits if visit.infusing}
        active_starts = sum(
            visit.infusion_started_minute is not None
            and visit.infusion_started_minute
            <= now
            < visit.infusion_started_minute + self.settings.setup_minutes
            for visit in visits
            if visit.infusing
        )
        nurse_slots = max(0, self.settings.nurses_for_starts - active_starts)
        bookings = sorted(
            (
                visit
                for visit in visits
                if visit.booking_status == "active"
                and visit.booked_chair is not None
                and visit.booked_start_minute is not None
                and visit.booked_start_minute
                + self.settings.ghost_grace_minutes
                <= now
                and not visit.infusing
                and (
                    visit.stage != "ready_for_chair"
                    or visit.location != "waiting_room"
                )
                and visit.booked_chair not in occupied
            ),
            key=lambda visit: (
                visit.booked_start_minute,
                visit.booked_chair,
                visit.id,
            ),
        )
        # Only the latest missed booking on each chair can define its current
        # recoverable gap. A ready booked patient who is already due owns it.
        current_by_chair: dict[int, PatientVisit] = {}
        for booked in bookings:
            current_by_chair[booked.booked_chair] = booked
        options = []
        for booked in current_by_chair.values():
            if any(
                other.id != booked.id
                and other.booking_status == "active"
                and other.booked_chair == booked.booked_chair
                and other.booked_start_minute is not None
                and other.booked_start_minute <= now
                and other.stage == "ready_for_chair"
                and other.location == "waiting_room"
                for other in visits
            ):
                continue
            protected = min(
                (
                    visit.booked_start_minute
                    for visit in visits
                    if visit.id != booked.id
                    and visit.booking_status == "active"
                    and visit.booked_chair == booked.booked_chair
                    and visit.booked_start_minute is not None
                    and visit.booked_start_minute > booked.booked_start_minute
                ),
                default=self.settings.horizon_minutes,
            )
            candidates = []
            excluded = []
            for visit in visits:
                if visit.id == booked.id or visit.infusing or visit.closed:
                    continue
                reason = self._exclusion_reason(visit, now, protected, set())
                if reason:
                    excluded.append({"patient_id": visit.id, "reason": reason})
                else:
                    candidates.append(visit)
            candidates.sort(key=lambda visit: self._rank(visit, now))
            options.append((booked, protected, candidates, excluded))

        assignments, method = self._assign_ghosts(options, nurse_slots, now)
        chosen_ids = {visit.id for visit in assignments.values()}
        slots = []
        for index, (booked, protected, candidates, excluded) in enumerate(
            options
        ):
            chosen = assignments.get(index)
            for visit in candidates:
                if chosen is not None and visit.id == chosen.id:
                    continue
                if nurse_slots == 0:
                    reason = "Nurse start capacity full"
                elif visit.id in chosen_ids:
                    reason = "Proposed for another chair"
                else:
                    reason = "Lower in ranking after feasible fills"
                excluded.append({"patient_id": visit.id, "reason": reason})
            slots.append(
                {
                    "booked_patient_id": booked.id,
                    "chair": booked.booked_chair,
                    "booked_start_minute": booked.booked_start_minute,
                    "next_protected_minute": protected,
                    "solver": method,
                    "reason": (
                        "Booked patient cannot use this overdue slot: "
                        + ", ".join(booked.blockers or ["not on site"])
                    ),
                    "replacement": (
                        {
                            "patient_id": chosen.id,
                            "priority": chosen.priority,
                            "appointment_minute": chosen.appointment_minute,
                            "ready_since_minute": chosen.ready_since_minute,
                            "duration_minutes": (
                                chosen.scheduled_duration_minutes
                            ),
                            "worst_case_same_chair_delay_minutes": (
                                chosen.scheduled_duration_minutes
                                + self.settings.turnover_minutes
                            ),
                            "reason": (
                                "Prerequisites complete; on site; session "
                                "fits before next protected booking. "
                                "Ranked by staff priority, appointment due, "
                                "ready wait, arrival, then visit ID."
                            ),
                        }
                        if chosen
                        else None
                    ),
                    "excluded": excluded,
                }
            )
        return slots

    def _assign_ghosts(
        self, options: list[tuple], nurse_slots: int, now: int
    ) -> tuple[dict[int, PatientVisit], str]:
        """Choose the highest-ranked feasible patient set."""
        if not options or nurse_slots == 0:
            return {}, "none"
        candidates_by_id = {
            visit.id: visit
            for _, _, candidates, _ in options
            for visit in candidates
        }
        if not candidates_by_id:
            return {}, "none"
        ranked = sorted(
            candidates_by_id.values(), key=lambda visit: self._rank(visit, now)
        )
        rank = {visit.id: index for index, visit in enumerate(ranked)}
        if cp_model is not None:
            model = cp_model.CpModel()
            variables = {}
            for index, (_, _, candidates, _) in enumerate(options):
                for visit in candidates:
                    variables[index, visit.id] = model.NewBoolVar(
                        f"slot_{index}_{visit.id}"
                    )
            for index in range(len(options)):
                model.Add(
                    sum(
                        variable
                        for (slot, _), variable in variables.items()
                        if slot == index
                    )
                    <= 1
                )
            for patient_id in candidates_by_id:
                model.Add(
                    sum(
                        variable
                        for (_, candidate), variable in variables.items()
                        if candidate == patient_id
                    )
                    <= 1
                )
            model.Add(sum(variables.values()) <= nurse_slots)
            model.Maximize(
                sum(
                    variable * (1 << (len(ranked) - rank[patient_id] - 1))
                    for (_, patient_id), variable in variables.items()
                )
            )
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 2.0
            solver.parameters.num_search_workers = 1
            solver.parameters.random_seed = 0
            status = solver.Solve(model)
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                return (
                    {
                        index: candidates_by_id[patient_id]
                        for (index, patient_id), variable in variables.items()
                        if solver.Value(variable)
                    },
                    "cp_sat",
                )

        # A timeout or unavailable solver never bypasses feasibility checks.
        # A small exact matching fallback keeps the same strict patient-rank
        # policy when CP-SAT is unavailable.
        states: dict[int, tuple[tuple[int, ...], dict[int, PatientVisit]]] = {
            0: ((), {})
        }
        for visit in ranked:
            feasible = [
                index
                for index, (_, _, candidates, _) in enumerate(options)
                if visit in candidates
            ]
            for mask, (chosen_ranks, assignments) in list(states.items()):
                if len(assignments) >= nurse_slots:
                    continue
                for index in feasible:
                    bit = 1 << index
                    if mask & bit:
                        continue
                    new_mask = mask | bit
                    new_ranks = (*chosen_ranks, rank[visit.id])
                    previous = states.get(new_mask)
                    if previous is None or new_ranks < previous[0]:
                        states[new_mask] = (
                            new_ranks,
                            {**assignments, index: visit},
                        )
        best = max(
            states.values(),
            key=lambda state: sum(
                1 << (len(ranked) - patient_rank - 1)
                for patient_rank in state[0]
            ),
        )
        return best[1], "heuristic_fallback"

    def _exclusion_reason(
        self,
        visit: PatientVisit,
        now: int,
        protected: int,
        selected: set[str],
    ) -> str | None:
        if visit.id in selected:
            return "Already proposed for another chair"
        if visit.stage != "ready_for_chair":
            return ", ".join(visit.blockers) or "Not ready for a chair"
        if visit.location != "waiting_room":
            return "Not confirmed on site"
        if self._arrival_minute(visit.arrival) > now:
            return "Arrival is later than the demo clock"
        if visit.booking_status == "active":
            return "Has a protected booking"
        if (
            now
            + visit.scheduled_duration_minutes
            + self.settings.turnover_minutes
            > protected
        ):
            return "Session and turnover do not fit before next booking"
        return None

    @staticmethod
    def _arrival_minute(arrival: str) -> int:
        hour, minute = (int(part) for part in arrival.split(":"))
        return (hour - 8) * 60 + minute

    def _rank(self, visit: PatientVisit, now: int) -> tuple:
        return (
            -visit.priority,
            visit.appointment_minute
            if visit.appointment_minute is not None
            else self.settings.horizon_minutes + 1,
            visit.ready_since_minute
            if visit.ready_since_minute is not None
            else now,
            self._arrival_minute(visit.arrival),
            visit.id,
        )

    def _next_nurse_start(self, earliest: int, starts: list[int]) -> int:
        """Find the first minute with a free nurse setup slot."""
        minute = earliest
        while minute <= self.settings.horizon_minutes:
            simultaneous = sum(
                start <= minute < start + self.settings.setup_minutes
                for start in starts
            )
            if simultaneous < self.settings.nurses_for_starts:
                return minute
            minute = min(
                start + self.settings.setup_minutes
                for start in starts
                if start <= minute < start + self.settings.setup_minutes
            )
        return minute
