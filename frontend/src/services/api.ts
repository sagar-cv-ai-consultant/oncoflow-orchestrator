import type {
  Snapshot,
  Patient,
  CommandAction,
  CommandFields,
  GhostSlot,
} from '../types';
/** HTTP boundary. UI components never construct fetch requests directly. */
export class ClinicApi {
  async getState(signal?: AbortSignal): Promise<Snapshot> {
    const response = await fetch('/api/state', { signal });
    if (!response.ok) throw new Error('Unable to load clinic state.');
    return response.json();
  }
  async sendCommand(
    patient: Patient,
    action: CommandAction,
    fields: CommandFields = {},
  ): Promise<void> {
    if (action === 'report_status' && fields.panel && fields.status) {
      const response = await fetch('/api/demo/webhook/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: crypto.randomUUID(),
          patient_id: patient.id,
          panel: fields.panel,
          source_sequence: patient.version + 1,
          report: {
            resourceType: 'DiagnosticReport',
            id: `demo-${patient.id}-${fields.panel}`,
            status: fields.status === 'pending' ? 'preliminary' : fields.status,
          },
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Status event failed.');
      return;
    }
    const response = await fetch(`/api/visits/${patient.id}/commands`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_id: crypto.randomUUID(),
        expected_version: patient.version,
        action,
        ...fields,
      }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Update failed.');
  }
  async approveGhost(slot: GhostSlot, revision: number): Promise<void> {
    if (!slot.replacement) throw new Error('No feasible replacement.');
    const response = await fetch('/api/ghost-slots/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_id: crypto.randomUUID(),
        expected_revision: revision,
        booked_patient_id: slot.booked_patient_id,
        replacement_id: slot.replacement.patient_id,
        chair: slot.chair,
      }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Proposal changed.');
  }
  async advanceClock(minute: number, revision: number): Promise<void> {
    const response = await fetch('/api/demo/clock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ minute, expected_revision: revision }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Clock update failed.');
  }
  async onboardDemo(revision: number): Promise<void> {
    const response = await fetch('/api/demo/onboard', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_id: crypto.randomUUID(),
        expected_revision: revision,
      }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Onboarding failed.');
  }
}
export const clinicApi = new ClinicApi();
