import type { Patient } from '../types';
export function ClinicSummary({
  patients,
  chairCount,
}: {
  patients: Patient[];
  chairCount: number;
}) {
  const waiting = patients.filter((p) => p.location === 'waiting_room').length,
    ready = patients.filter((p) =>
      ['ready_for_consult', 'ready_for_chair'].includes(p.stage),
    ).length,
    blocked = patients.filter((p) =>
      ['awaiting_reports', 'awaiting_clearance', 'awaiting_pharmacy'].includes(p.stage),
    ).length;
  const occupied = patients.filter((p) => p.infusing);
  return (
    <section className="metrics" aria-label="Clinic overview">
      <div>
        <span>Physically waiting</span>
        <strong>
          {waiting}
          <small>patients</small>
        </strong>
        <p>In the waiting room now</p>
      </div>
      <div>
        <span>Ready for next step</span>
        <strong className="teal">
          {ready}
          <small>patients</small>
        </strong>
        <p>Consultation or chair prerequisites met</p>
      </div>
      <div>
        <span>Awaiting a prerequisite</span>
        <strong>
          {blocked}
          <small>patients</small>
        </strong>
        <p>Report, clearance or pharmacy</p>
      </div>
      <div>
        <span>Chairs occupied</span>
        <strong>
          {occupied.length}
          <small>/ {chairCount}</small>
        </strong>
        <p>Actual starts confirmed by staff</p>
      </div>
    </section>
  );
}
