import type { Stage, Location, CommandAction } from './types';
export const labels: Record<Stage, string> = {
  awaiting_reports: 'Awaiting reports',
  ready_for_consult: 'Ready for consult',
  with_doctor: 'With doctor',
  awaiting_clearance: 'Awaiting clearance',
  awaiting_pharmacy: 'Awaiting pharmacy',
  ready_for_chair: 'Ready for chair',
  infusing: 'Infusing',
  discharged: 'Discharged',
  no_show: 'No-show',
};
export const locations: Record<Location, string> = {
  waiting_room: 'Waiting room',
  nearby: 'Waiting nearby',
  with_team: 'With care team',
  left: 'Left clinic',
};
export const actions: Partial<Record<Stage, { action: CommandAction; label: string }>> =
  {
    ready_for_consult: { action: 'start_consult', label: 'Start consultation' },
    with_doctor: { action: 'finish_consult', label: 'Complete consultation' },
    awaiting_clearance: { action: 'clearance', label: 'Record clinician clearance' },
    awaiting_pharmacy: { action: 'pharmacy_ready', label: 'Mark pharmacy ready' },
    ready_for_chair: { action: 'start_infusion', label: 'Assign chair & start' },
    infusing: { action: 'finish_infusion', label: 'Complete infusion & discharge' },
  };
