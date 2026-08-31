import React from 'react';

interface ProviderPanelProps {
  providers: string[];
}

export const ProviderPanel: React.FC<ProviderPanelProps> = ({ providers }) => {
  return (
    <div className="card" style={{ padding: '12px' }}>
      <div className="card-title" style={{ fontSize: '0.74rem', border: 'none', padding: 0 }}>
        <span>📡 接口插线板 (Providers)</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
        {providers.map((p) => (
          <span
            key={p}
            style={{
              fontSize: '0.68rem',
              fontFamily: 'var(--font-mono)',
              background: 'rgba(0, 0, 0, 0.02)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              padding: '2px 8px',
              borderRadius: '12px',
              fontWeight: 500,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'var(--color-success)', boxShadow: '0 0 4px var(--color-success-glow)' }} />
            {p.toUpperCase()}
          </span>
        ))}
      </div>
    </div>
  );
};
export default ProviderPanel;
