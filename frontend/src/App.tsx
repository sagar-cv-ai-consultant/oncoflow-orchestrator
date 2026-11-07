import { useState } from 'react';
import type { Filter, View } from './types';
import { useClinic } from './hooks/useClinic';
import { Sidebar } from './components/Sidebar';
import { ClinicSummary } from './components/ClinicSummary';
import { ChairAvailability } from './components/ChairAvailability';
import { PatientWorklist } from './components/PatientWorklist';
import { PatientDetails } from './components/PatientDetails';
import { AuditHistory } from './components/AuditHistory';
import { ScheduleRecommendations } from './components/ScheduleRecommendations';
import { GhostSlots } from './components/GhostSlots';
export function App() {
  const {
    data,
    error,
    offline,
    busy,
    notice,
    updated,
    command,
    approveGhost,
    advanceClock,
    onboardDemo,
    clearFeedback,
  } = useClinic();
  const [selected, setSelected] = useState('OF-003');
  const [view, setView] = useState<View>('worklist');
  const [filter, setFilter] = useState<Filter>('all');
  const [query, setQuery] = useState('');
  const [chair, setChair] = useState('2');
  const patients = data?.patients ?? [];
  const patient = patients.find((p) => p.id === selected);
  function selectPatient(id: string) {
    setSelected(id);
    clearFeedback();
    if (window.innerWidth <= 980)
      requestAnimationFrame(() =>
        document
          .querySelector('.patient-detail')
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      );
  }
  function reviewRecommendation(id: string, recommendedChair: number) {
    setChair(String(recommendedChair));
    selectPatient(id);
  }
  return (
    <div className="shell">
      <Sidebar view={view} onViewChange={setView} />
      <main>
        <div className="demo-banner">
          <span className="demo-dot" />
          SYNTHETIC DEMO
          <span className="banner-description">
            Fictional patients. Local prototype for workflow review.
          </span>
        </div>
        <header>
          <div>
            <div className="eyebrow">ONCOLOGY DAY CARE / COORDINATOR</div>
            <h1>
              {view === 'worklist'
                ? 'A clearer view of the clinic day.'
                : 'Every change, accounted for.'}
            </h1>
            <p>
              {view === 'worklist'
                ? 'See who is ready, understand what is blocking progress, and coordinate the next step.'
                : 'Review the operational updates recorded during this demonstration.'}
            </p>
          </div>
          <div className="connection">
            <span className={offline ? 'status-dot off' : 'status-dot'} />
            {offline ? 'Connection lost' : 'Connected locally'}
            <small>
              {updated
                ? `Refreshed ${updated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
                : 'Connecting…'}
            </small>
          </div>
        </header>
        {offline && (
          <div className="alert error" role="alert">
            Cannot reach the local service. Updates are disabled until the connection
            returns.
          </div>
        )}
        {error && (
          <div className="alert error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="alert success" role="status">
            {notice}
          </div>
        )}
        {!data ? (
          <div className="empty">
            {offline
              ? 'Start the local service to load the clinic worklist.'
              : 'Loading the clinic day…'}
          </div>
        ) : (
          <>
            <ClinicSummary patients={patients} chairCount={data.chair_count} />
            {view === 'audit' ? (
              <AuditHistory events={data.events} />
            ) : (
              <>
                {data.scenario === 'ghost' ? (
                  <GhostSlots
                    slots={data.ghost_slots}
                    patients={patients}
                    schedule={data.schedule}
                    minute={data.demo_minute}
                    busy={busy || offline}
                    onApprove={approveGhost}
                    onAdvance={advanceClock}
                    onSelectPatient={selectPatient}
                    onReview={reviewRecommendation}
                    onOnboard={onboardDemo}
                  />
                ) : (
                  <ScheduleRecommendations
                    schedule={data.schedule}
                    patients={patients}
                    onReview={reviewRecommendation}
                  />
                )}
                <ChairAvailability patients={patients} chairCount={data.chair_count} />
                <div className="work-area">
                  <PatientWorklist
                    patients={patients}
                    selected={selected}
                    onSelect={selectPatient}
                    filter={filter}
                    onFilterChange={setFilter}
                    query={query}
                    onQueryChange={setQuery}
                  />
                  <PatientDetails
                    patient={patient}
                    patients={patients}
                    chairCount={data.chair_count}
                    busy={busy}
                    offline={offline}
                    onCommand={command}
                    chair={chair}
                    onChairChange={setChair}
                  />
                </div>
              </>
            )}
            <footer>
              OncoFlow Orchestrator{' '}
              <span>Operational support · Staff retain control</span>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
