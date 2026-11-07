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
  appointment_minute: number | null;
  booked_start_minute: number | null;
  booked_chair: number | null;
  booking_status: 'none' | 'active' | 'displaced';
  ready_since_minute: number | null;
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
  schedule: Schedule;
  ghost_slots: GhostSlot[];
  demo_minute: number;
  scenario: 'manual' | 'ghost';
  mode: 'synthetic_demo';
}
export interface GhostSlot {
  booked_patient_id: string;
  chair: number;
  booked_start_minute: number;
  next_protected_minute: number;
  solver: 'cp_sat' | 'heuristic_fallback' | 'none';
  reason: string;
  replacement: {
    patient_id: string;
    priority: number;
    appointment_minute: number | null;
    ready_since_minute: number | null;
    duration_minutes: number;
    worst_case_same_chair_delay_minutes: number;
    reason: string;
  } | null;
  excluded: { patient_id: string; reason: string }[];
}
export interface ScheduleRecommendation {
  patient_id: string;
  chair: number;
  start_in_minutes: number;
  duration_minutes: number;
  priority: number;
  reason: string;
}
export interface Schedule {
  recommendations: ScheduleRecommendation[];
  pinned: { patient_id: string; chair: number }[];
  unscheduled: string[];
  assumptions: {
    nurses_for_starts: number;
    setup_minutes: number;
    horizon_minutes: number;
    active_chair_remaining_minutes: string;
  };
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
