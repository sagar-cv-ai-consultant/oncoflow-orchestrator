export type Stage =
  | 'awaiting_reports'
  | 'ready_for_consult'
  | 'with_doctor'
  | 'awaiting_clearance'
  | 'awaiting_pharmacy'
  | 'ready_for_chair'
  | 'infusing'
  | 'discharged'
  | 'no_show';
export type ReportStatus =
  | 'pending'
  | 'final'
  | 'corrected'
  | 'cancelled'
  | 'entered-in-error';
export type Location = 'waiting_room' | 'nearby' | 'with_team' | 'left';
export type View = 'worklist' | 'audit';
export type Filter = 'all' | 'blocked' | 'ready' | 'infusing';
export interface Patient {
  id: string;
  alias: string;
  priority: number;
  panels: Record<string, ReportStatus>;
  stage: Stage;
  blockers: string[];
  location: Location;
  version: number;
  chair: number | null;
  arrival: string;
  infusing: boolean;
  in_consult: boolean;
  closed: string | null;
}
export interface AuditEvent {
  seq: number;
  patient_id: string;
  timestamp: string;
  action: string;
  actor: string;
  payload: Record<string, unknown>;
}
export interface Snapshot {
  patients: Patient[];
  events: AuditEvent[];
  revision: number;
  chair_count: number;
  mode: 'synthetic_demo';
}
export type CommandAction =
  | 'report_status'
  | 'start_consult'
  | 'finish_consult'
  | 'clearance'
  | 'pharmacy_ready'
  | 'start_infusion'
  | 'finish_infusion'
  | 'location'
  | 'no_show';
export interface CommandFields {
  panel?: 'CBC' | 'CMP';
  status?: ReportStatus;
  chair?: number;
  location?: Location;
}
export type PatientAction = (
  patient: Patient,
  action: CommandAction,
  fields?: CommandFields,
) => Promise<void>;
