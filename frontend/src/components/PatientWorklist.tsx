import type { Patient, Filter } from '../types';
import { labels, locations } from '../constants';
interface Props {
  patients: Patient[];
  selected: string;
  onSelect: (id: string) => void;
  filter: Filter;
  onFilterChange: (filter: Filter) => void;
  query: string;
  onQueryChange: (query: string) => void;
}
export function PatientWorklist({
  patients,
  selected,
  onSelect,
  filter,
  onFilterChange,
  query,
  onQueryChange,
}: Props) {
  const shown = patients.filter(
    (p) =>
      (filter === 'all' ||
        (filter === 'blocked'
          ? ['awaiting_reports', 'awaiting_clearance', 'awaiting_pharmacy'].includes(
              p.stage,
            )
          : filter === 'ready'
            ? ['ready_for_consult', 'ready_for_chair'].includes(p.stage)
            : p.infusing)) &&
      `${p.id} ${p.alias}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <section className="worklist">
      <div className="section-heading">
        <h2>
          Patient worklist <span>{patients.length}</span>
        </h2>
        <label className="search">
          <span>⌕</span>
          <input
            aria-label="Search patients"
            placeholder="Search visit or patient"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
          />
        </label>
      </div>
      <div className="filters" role="group" aria-label="Filter patient worklist">
        {[
          ['all', 'All visits'],
          ['blocked', 'Blocked'],
          ['ready', 'Ready'],
          ['infusing', 'Infusing'],
        ].map(([value, label]) => (
          <button
            key={value}
            className={filter === value ? 'selected' : ''}
            onClick={() => onFilterChange(value as Filter)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Patient / visit</th>
              <th>Current step</th>
              <th>Waiting location</th>
              <th>Arrived</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((p) => (
              <tr key={p.id} className={selected === p.id ? 'selected-row' : ''}>
                <td>
                  <button
                    className="patient-select"
                    onClick={() => onSelect(p.id)}
                    aria-label={`Open ${p.id}`}
                  >
                    <strong>{p.alias}</strong>
                    <small>
                      {p.id}
                      {p.priority > 0 && (
                        <span className="priority">Staff priority</span>
                      )}
                    </small>
                  </button>
                </td>
                <td>
                  <span className={`badge ${p.stage}`}>{labels[p.stage]}</span>
                </td>
                <td className="location">
                  <span className={`location-dot ${p.location}`} />
                  {locations[p.location]}
                </td>
                <td className="arrival">{p.arrival}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {shown.length === 0 && (
          <div className="empty">No visits match this filter.</div>
        )}
      </div>
      <div className="list-footer">
        Select a patient to review prerequisites and update their visit.
        <span>All data is fictional</span>
      </div>
    </section>
  );
}
