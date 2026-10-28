import type { AuditEvent } from '../types';
export function AuditHistory({ events }: { events: AuditEvent[] }) {
  return (
    <section className="audit-page">
      <div className="section-heading">
        <h2>Operational audit history</h2>
        <span>Latest {events.length} events · UTC stored</span>
      </div>
      <p className="subtle">
        Demo updates use a local operator label. Individual staff accounts are not
        implemented yet.
      </p>
      <table>
        <thead>
          <tr>
            <th>Recorded at</th>
            <th>Visit</th>
            <th>Update</th>
            <th>Actor</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.seq}>
              <td>{new Date(e.timestamp).toLocaleString()}</td>
              <td>{e.patient_id}</td>
              <td>
                {e.action === 'demo_seed'
                  ? 'Synthetic visit created'
                  : e.action.replaceAll('_', ' ')}
                {e.payload.panel
                  ? ` · ${String(e.payload.panel)}: ${String(e.payload.status)}`
                  : ''}
              </td>
              <td>{e.actor}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
