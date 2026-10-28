import type { Patient, PatientAction, ReportStatus } from '../types';
import { actions, labels } from '../constants';
interface Props {
  patient: Patient | undefined;
  patients: Patient[];
  chairCount: number;
  busy: boolean;
  offline: boolean;
  onCommand: PatientAction;
  chair: string;
  onChairChange: (chair: string) => void;
}
export function PatientDetails({
  patient,
  patients,
  chairCount,
  busy,
  offline,
  onCommand,
  chair,
  onChairChange,
}: Props) {
  const occupied = patients.filter((p) => p.infusing);
  const next = patient ? actions[patient.stage] : undefined;
  return (
    <aside className="patient-detail" aria-label="Selected patient details">
      {patient && (
        <>
          <div className="detail-heading">
            <span className="tiny">VISIT DETAILS</span>
            <span>{patient.id}</span>
          </div>
          <h2>{patient.alias}</h2>
          <span className={`badge ${patient.stage}`}>{labels[patient.stage]}</span>
          {patient.infusing && patient.blockers.length > 0 && (
            <div className="alert error" role="alert">
              Report or readiness changed during infusion. Staff review required.
              Ongoing care remains unchanged.
            </div>
          )}
          <h3>Required reports</h3>
          <p className="subtle">Availability only. Clinical values are excluded.</p>
          <div className="report-list">
            {Object.entries(patient.panels).map(([code, status]) => (
              <div className="report" key={code}>
                <div>
                  <strong>{code}</strong>
                  <small>
                    {status === 'final'
                      ? 'Final report available'
                      : status.replaceAll('-', ' ')}
                  </small>
                </div>
                <span className={status === 'final' ? 'check' : 'pending'}>
                  {status === 'final' ? '✓' : '◷'}
                </span>
              </div>
            ))}
          </div>
          <h3>Before infusion</h3>
          {patient.closed ? (
            <p className="subtle">This visit is closed.</p>
          ) : patient.blockers.length ? (
            <ul className="blockers">
              {patient.blockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          ) : (
            <p className="complete">✓ All recorded prerequisites complete</p>
          )}
          <div className="action-area">
            <h3>Coordinator action</h3>
            {next ? (
              <>
                <p className="subtle">
                  {patient.stage === 'awaiting_clearance'
                    ? 'Record a decision already made by a clinician. OncoFlow does not assess treatment suitability.'
                    : 'Confirm this step has occurred before updating the visit.'}
                </p>
                {patient.stage === 'ready_for_chair' && (
                  <label className="field-label">
                    Available chair
                    <select
                      aria-label="Select chair"
                      value={chair}
                      onChange={(e) => onChairChange(e.target.value)}
                    >
                      {Array.from({ length: chairCount }, (_, i) => (
                        <option
                          key={i}
                          value={i + 1}
                          disabled={occupied.some((p) => p.chair === i + 1)}
                        >
                          Chair {i + 1}
                          {occupied.some((p) => p.chair === i + 1) ? ' · occupied' : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <button
                  className="primary"
                  disabled={
                    busy ||
                    offline ||
                    !!(
                      patient.stage === 'ready_for_chair' &&
                      (patient.location !== 'waiting_room' ||
                        occupied.some((p) => p.chair === Number(chair)))
                    )
                  }
                  onClick={() =>
                    onCommand(
                      patient,
                      next.action,
                      patient.stage === 'ready_for_chair'
                        ? { chair: Number(chair) }
                        : {},
                    )
                  }
                >
                  {busy ? 'Saving…' : next.label}
                  <span>↗</span>
                </button>
                {patient.stage === 'ready_for_chair' &&
                  patient.location !== 'waiting_room' && (
                    <p className="subtle">
                      Confirm the patient's return below before seating.
                    </p>
                  )}
              </>
            ) : (
              <p className="subtle">
                {patient.closed
                  ? 'No further actions for this visit.'
                  : 'Required reports must be available before consultation can start.'}
              </p>
            )}
            {!patient.closed && !patient.infusing && !patient.in_consult && (
              <button
                className="secondary"
                disabled={busy || offline}
                onClick={() =>
                  onCommand(patient, 'location', {
                    location: patient.location === 'nearby' ? 'waiting_room' : 'nearby',
                  })
                }
              >
                {patient.location === 'nearby'
                  ? 'Confirm return to waiting room'
                  : 'Record waiting nearby'}
              </button>
            )}
          </div>
          {!patient.closed && (
            <details className="simulation">
              <summary>Demo event controls</summary>
              <p>
                Simulate report availability. Corrected reports require staff review and
                new clearance.
              </p>
              {Object.entries(patient.panels).map(([code, status]) => (
                <label key={code} className="field-label">
                  {code} report status
                  <select
                    aria-label={`${code} report status`}
                    value={status}
                    disabled={busy || offline}
                    onChange={(e) =>
                      onCommand(patient, 'report_status', {
                        panel: code as 'CBC' | 'CMP',
                        status: e.target.value as ReportStatus,
                      })
                    }
                  >
                    <option value="pending">Pending</option>
                    <option value="final">Final</option>
                    <option value="corrected">Corrected · review required</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="entered-in-error">Entered in error</option>
                  </select>
                </label>
              ))}
            </details>
          )}
        </>
      )}
    </aside>
  );
}
