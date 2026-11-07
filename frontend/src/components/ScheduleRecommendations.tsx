import type { Patient, Schedule } from '../types';

interface Props {
  schedule: Schedule;
  patients: Patient[];
  onReview: (patientId: string, chair: number) => void;
}

export function ScheduleRecommendations({ schedule, patients, onReview }: Props) {
  const names = new Map(patients.map((patient) => [patient.id, patient.alias]));
  return (
    <section className="schedule" aria-label="Automated chair recommendations">
      <div className="section-heading">
        <div>
          <span className="tiny">AUTOMATED SCHEDULING</span>
          <h2>Suggested chair plan</h2>
        </div>
        <span className="schedule-label">Staff confirmation required</span>
      </div>
      <p className="subtle">
        Recalculated as visit status changes. Only patients with recorded prerequisites
        complete and confirmed on site are included.
      </p>
      {schedule.recommendations.length === 0 ? (
        <p className="subtle">No patient is currently eligible for a chair.</p>
      ) : (
        <div className="schedule-list">
          {schedule.recommendations.map((item) => (
            <div className="schedule-item" key={item.patient_id}>
              <div>
                <strong>{names.get(item.patient_id) ?? item.patient_id}</strong>
                <small>
                  {item.patient_id} · Chair {item.chair} ·{' '}
                  {item.start_in_minutes === 0
                    ? 'Can start now'
                    : `Illustrative start in ${item.start_in_minutes} min`}
                </small>
              </div>
              {item.start_in_minutes === 0 && (
                <button
                  className="secondary"
                  onClick={() => onReview(item.patient_id, item.chair)}
                >
                  Review start
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      <p className="schedule-footnote">
        Assumes {schedule.assumptions.nurses_for_starts} nurses can start infusions at
        once, with {schedule.assumptions.setup_minutes}-minute setup. Active chairs are
        held for their full planned duration from the current snapshot. Future times are
        planning estimates, not appointments or reservations.
      </p>
    </section>
  );
}
