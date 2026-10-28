import type { Snapshot, Patient, CommandAction, CommandFields } from '../types';
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
}
export const clinicApi = new ClinicApi();
