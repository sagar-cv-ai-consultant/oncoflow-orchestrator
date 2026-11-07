import type { GhostSlot, Patient, Schedule } from '../types';

interface Props {
  slots: GhostSlot[];
  patients: Patient[];
  schedule: Schedule;
  minute: number;
  busy: boolean;
  onApprove: (slot: GhostSlot) => void;
  onAdvance: (minutes: number) => void;
  onSelectPatient: (id: string) => void;
  onReview: (id: string, chair: number) => void;
  onOnboard: () => void;
}

function clinicTime(minute: number): string {
  const total = 8 * 60 + minute;
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

export function GhostSlots({
  slots,
  patients,
  schedule,
  minute,
  busy,
  onApprove,
  onAdvance,
  onSelectPatient,
  onReview,
  onOnboard,
}: Props) {
  const names = new Map(patients.map((patient) => [patient.id, patient.alias]));
  const displaced = patients.filter(
    (patient) => patient.booking_status === 'displaced',
  );
  return (
    <section className="ghost-panel" aria-label="Ghost chair recovery">
      <div className="section-heading">
        <div>
          <span className="tiny">GHOST CHAIR RECOVERY</span>
          <h2>Fill usable gaps without bypassing care steps</h2>
        </div>
        <div className="demo-clock">
          Fictional clinic clock <strong>{clinicTime(minute)}</strong>
          <button disabled={busy || minute > 450} onClick={() => onAdvance(15)}>
            +15 min
          </button>
          {!patients.some((patient) => patient.id === 'OF-013') && (
            <button disabled={busy} onClick={onOnboard}>
              Add already-tested patient
            </button>
          )}
        </div>
      </div>
      <p className="subtle ghost-intro">
        An overdue booking becomes a possible gap when its patient is not ready or on
        site. Only a coordinator can confirm a replacement.
      </p>
      {slots.length === 0 ? (
        <p className="subtle ghost-intro">No overdue unusable booking at this time.</p>
      ) : (
        <div className="ghost-grid">
          {slots.map((slot) => (
            <article className="ghost-card" key={slot.booked_patient_id}>
              <div className="ghost-card-top">
                <strong>
                  Chair {slot.chair} · missed {clinicTime(slot.booked_start_minute)}
                </strong>
                <span>Next protected {clinicTime(slot.next_protected_minute)}</span>
              </div>
              <small className="solver-label">
                {slot.solver === 'cp_sat'
                  ? 'CP-SAT assignment'
                  : slot.solver === 'heuristic_fallback'
                    ? 'Rule-based fallback'
                    : 'No available start capacity'}
              </small>
              <p>
                {names.get(slot.booked_patient_id) ?? slot.booked_patient_id} cannot
                take this slot: {slot.reason}
              </p>
              {slot.replacement ? (
                <>
                  <div className="ghost-choice">
                    <span>Recommended replacement</span>
                    <strong>
                      {names.get(slot.replacement.patient_id) ??
                        slot.replacement.patient_id}
                    </strong>
                    <small>
                      Staff priority {slot.replacement.priority} · planned{' '}
                      {slot.replacement.duration_minutes} min
                    </small>
                    <small>{slot.replacement.reason}</small>
                    <small className="displacement-warning">
                      If the booked patient becomes ready now, this chair may be
                      unavailable for up to{' '}
                      {slot.replacement.worst_case_same_chair_delay_minutes} min. Staff
                      must arrange their next slot.
                    </small>
                  </div>
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() => onApprove(slot)}
                  >
                    Confirm displacement and start
                  </button>
                </>
              ) : (
                <p className="subtle">No feasible replacement right now.</p>
              )}
              <details>
                <summary>Why other visits were excluded</summary>
                <ul>
                  {slot.excluded.map((item) => (
                    <li key={item.patient_id}>
                      {item.patient_id}: {item.reason}
                    </li>
                  ))}
                </ul>
              </details>
            </article>
          ))}
        </div>
      )}
      {displaced.length > 0 && (
        <div className="displaced-queue">
          <h3>Displaced bookings needing follow-up</h3>
          {displaced.map((patient) => (
            <div className="displaced-item" key={patient.id}>
              <button onClick={() => onSelectPatient(patient.id)}>
                <strong>{patient.alias}</strong>
                <span>
                  {patient.stage === 'ready_for_chair'
                    ? 'Ready for a new chair plan'
                    : patient.blockers.join(', ')}
                </span>
              </button>
              {schedule.recommendations
                .filter((item) => item.patient_id === patient.id)
                .map((item) => (
                  <div key={item.chair}>
                    <small>
                      Suggested Chair {item.chair} ·{' '}
                      {item.start_in_minutes === 0
                        ? 'available now'
                        : `after about ${item.start_in_minutes} min`}
                    </small>
                    {item.start_in_minutes === 0 && (
                      <button onClick={() => onReview(patient.id, item.chair)}>
                        Review new chair
                      </button>
                    )}
                  </div>
                ))}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
