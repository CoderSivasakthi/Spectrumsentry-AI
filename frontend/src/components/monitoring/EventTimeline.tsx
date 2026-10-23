import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { Clock, CalendarClock } from 'lucide-react';

const TYPE_DOT: Record<string, string> = {
  success: 'dot--ok',
  warning: 'dot--warn',
  critical: 'dot--crit',
  info: 'dot--info',
};

export const EventTimeline: React.FC = () => {
  const { timeline } = useMonitoring();

  return (
    <section className="card" style={{ display: 'flex', flexDirection: 'column' }}>
      <header className="card__header row--between row">
        <div>
          <h3 className="card__title">Recent Event Timeline</h3>
          <p className="card__sub">State transitions in chronological order</p>
        </div>
        <span className="badge">{timeline.length} events</span>
      </header>

      <div
        className="card__body"
        style={{ maxHeight: 300, overflowY: 'auto', paddingRight: 4, flex: 1 }}
      >
        {timeline.length > 0 ? (
          timeline.map((item, idx) => (
            <div key={item.id || idx} className="timeline-row">
              <span className={`dot ${TYPE_DOT[item.type] || 'dot--info'}`} style={{ marginTop: 5 }} />
              <div style={{ minWidth: 0 }}>
                <div className="row--between row" style={{ alignItems: 'baseline' }}>
                  <span
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 500,
                      color: 'var(--text-1)',
                    }}
                  >
                    {item.title}
                  </span>
                </div>
                {item.details && (
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)', marginTop: 2 }}>
                    {item.details}
                  </p>
                )}
              </div>
              <span className="timeline-row__time" style={{ marginTop: 2 }}>
                {item.timestamp}
              </span>
            </div>
          ))
        ) : (
          <div className="pane-state" style={{ paddingBlock: 'var(--space-6)' }}>
            <span className="pane-state__icon">
              <Clock size={18} />
            </span>
            <p className="pane-state__title">No events recorded yet</p>
            <p className="pane-state__hint">
              State transitions and alerts will appear here in chronological order.
            </p>
          </div>
        )}
      </div>

      <div className="card__footer row--between row">
        <span>Rolling buffer — last 30 events</span>
        <CalendarClock size={12} style={{ color: 'var(--text-4)' }} />
      </div>
    </section>
  );
};
