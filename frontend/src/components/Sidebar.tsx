import type { View } from '../types';
interface Props {
  view: View;
  onViewChange: (view: View) => void;
}
export function Sidebar({ view, onViewChange }: Props) {
  return (
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="OncoFlow home">
        <span className="brand-mark">
          o<span>+</span>
        </span>
        <span>
          OncoFlow<small>CLINIC OPERATIONS</small>
        </span>
      </a>
      <div className="workspace">
        <span className="tiny">WORKSPACE</span>
        <strong>Oncology day care</strong>
        <span>Single-unit prototype</span>
      </div>
      <nav aria-label="Main navigation">
        <button
          className={view === 'worklist' ? 'nav active' : 'nav'}
          onClick={() => onViewChange('worklist')}
        >
          <span>▤</span>Patient worklist
        </button>
        <button
          className={view === 'audit' ? 'nav active' : 'nav'}
          onClick={() => onViewChange('audit')}
        >
          <span>◷</span>Audit history
        </button>
      </nav>
      <div className="sidebar-bottom">
        <span className="tiny">CURRENT MVP</span>
        <p>Readiness & chair recovery</p>
        <small>Staff review each scheduling recommendation before a chair changes.</small>
      </div>
    </aside>
  );
}
