import type { Patient } from '../types';
export function ChairAvailability({
  patients,
  chairCount,
}: {
  patients: Patient[];
  chairCount: number;
}) {
  const occupied = patients.filter((p) => p.infusing);
  return (
    <section className="chairs" aria-label="Chair availability">
      <div>
        <span className="tiny">CHAIR AVAILABILITY</span>
        <small>Current occupancy</small>
      </div>
      <div className="chair-list">
        {Array.from({ length: chairCount }, (_, i) => {
          const current = occupied.find((p) => p.chair === i + 1);
          return (
            <div key={i} className={`chair ${current ? 'occupied' : ''}`}>
              <span>Chair {i + 1}</span>
              <strong>{current ? current.id : 'Available'}</strong>
            </div>
          );
        })}
      </div>
    </section>
  );
}
