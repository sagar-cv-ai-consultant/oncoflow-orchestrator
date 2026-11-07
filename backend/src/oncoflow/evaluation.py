"""Transparent synthetic ghost-slot case study."""

import json
import random
import statistics
import time

from .fixtures import ghost_day_visits
from .scheduler import ChairScheduler


def evaluate_ghost_day() -> dict:
    """Compare holding two booked chairs with staff-approved backfill."""
    now = 150  # 10:30, minutes since 08:00
    # Fictional times when each delayed booking completes every prerequisite.
    # These are revealed to the evaluator, not supplied to the scheduler.
    completed_by = {"OF-003": 210, "OF-004": 230}
    visits = ghost_day_visits()
    slots = ChairScheduler().ghost_slots(visits, now)
    results = []
    for slot in slots:
        replacement = slot["replacement"]
        if replacement is None:
            raise ValueError("The case requires two feasible replacements.")
        original_ready = completed_by[slot["booked_patient_id"]]
        replacement_end = now + replacement["duration_minutes"]
        baseline_idle = original_ready - now
        recovered = max(0, min(replacement_end, original_ready) - now)
        # A ten-minute chair turnover is included before the original patient
        # could take the chair after the replacement.
        original_delay = max(0, replacement_end + 10 - original_ready)
        results.append(
            {
                "chair": slot["chair"],
                "delayed_booking": slot["booked_patient_id"],
                "replacement": replacement["patient_id"],
                "baseline_idle_minutes_until_original_ready": baseline_idle,
                "recovered_chair_minutes": recovered,
                "possible_same_chair_delay_minutes": original_delay,
            }
        )
    return {
        "scenario": "two overdue booked chairs, two ready replacements",
        "data": "fictional, deterministic",
        "comparison": "hold booking until ready vs confirmed backfill",
        "assumptions": {
            "clock_minute": now,
            "original_ready_minutes": completed_by,
            "chair_turnover_minutes": 10,
        },
        "per_chair": results,
        "totals": {
            "baseline_idle_minutes": sum(
                row["baseline_idle_minutes_until_original_ready"]
                for row in results
            ),
            "recovered_chair_minutes": sum(
                row["recovered_chair_minutes"] for row in results
            ),
            "possible_same_chair_delay_minutes": sum(
                row["possible_same_chair_delay_minutes"] for row in results
            ),
        },
        "limitation": (
            "One scripted case only; not measured patient or clinic benefit. "
            "The displaced patient still needs a new booking."
        ),
    }


def evaluate_varied_days(count: int = 50) -> dict:
    """Exercise the same policy on varied deterministic fictional inputs."""
    if count < 1:
        raise ValueError("At least one scenario is required.")
    scheduler = ChairScheduler()
    days = []
    for seed in range(count):
        randomizer = random.Random(seed)
        visits = ghost_day_visits()
        by_id = {visit.id: visit for visit in visits}
        for patient_id in ("OF-007", "OF-011", "OF-008", "OF-009"):
            visit = by_id[patient_id]
            if (
                patient_id in ("OF-008", "OF-009")
                and randomizer.random() < 0.5
            ):
                continue
            visit.panels = {"CBC": "final"}
            visit.consult_done = True
            visit.cleared = True
            visit.pharmacy_ready = True
            visit.location = "waiting_room"
            visit.priority = randomizer.randrange(3)
            visit.scheduled_duration_minutes = randomizer.choice(
                (30, 60, 90, 120, 180)
            )
            visit.appointment_minute = randomizer.randrange(90, 151)
            arrival = scheduler._arrival_minute(visit.arrival)
            visit.ready_since_minute = randomizer.randrange(
                max(0, arrival), 151
            )
        original_ready = {
            "OF-003": randomizer.randrange(190, 251),
            "OF-004": randomizer.randrange(190, 251),
        }
        started = time.perf_counter()
        slots = scheduler.ghost_slots(visits, 150)
        solve_ms = (time.perf_counter() - started) * 1000
        fills = 0
        recovered = 0
        same_chair_delay = 0
        for slot in slots:
            replacement = slot["replacement"]
            if replacement is None:
                continue
            fills += 1
            ready = original_ready[slot["booked_patient_id"]]
            end = 150 + replacement["duration_minutes"]
            recovered += max(0, min(end, ready) - 150)
            same_chair_delay += max(0, end + 10 - ready)
            if end + 10 > slot["next_protected_minute"]:
                raise AssertionError("A protected booking was displaced.")
        days.append(
            {
                "seed": seed,
                "fills": fills,
                "recovered_chair_minutes": recovered,
                "possible_same_chair_delay_minutes": same_chair_delay,
                "solve_ms": round(solve_ms, 3),
            }
        )
    recovered_values = sorted(day["recovered_chair_minutes"] for day in days)
    delay_values = sorted(
        day["possible_same_chair_delay_minutes"] for day in days
    )
    timings = sorted(day["solve_ms"] for day in days)
    p90_index = min(count - 1, (9 * count + 9) // 10 - 1)
    return {
        "scenario_count": count,
        "data": "varied synthetic states, seeds 0 through count-1",
        "comparison": "holding two blocked bookings vs immediate backfill",
        "summary": {
            "mean_fills_per_day": round(
                statistics.mean(day["fills"] for day in days), 2
            ),
            "median_recovered_chair_minutes": statistics.median(
                recovered_values
            ),
            "p90_recovered_chair_minutes": recovered_values[p90_index],
            "median_possible_same_chair_delay_minutes": statistics.median(
                delay_values
            ),
            "p90_possible_same_chair_delay_minutes": delay_values[p90_index],
            "p90_solver_ms": timings[p90_index],
        },
        "limitation": (
            "Synthetic robustness check, not a clinical-effectiveness study. "
            "Original patients still require rebooking."
        ),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "fixed_case": evaluate_ghost_day(),
                "varied_days": evaluate_varied_days(),
            },
            indent=2,
        )
    )
