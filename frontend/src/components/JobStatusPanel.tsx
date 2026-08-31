import React from 'react';
import { Job } from '../types';

interface JobStatusPanelProps {
  job: Job | null;
  onClear: () => void;
}

export const JobStatusPanel: React.FC<JobStatusPanelProps> = ({ job, onClear }) => {
  if (!job) return null;

  const getStatusText = (status: string) => {
    switch (status) {
      case 'succeeded': return '成功';
      case 'failed': return '失败';
      case 'queued': return '排队';
      case 'running': return '合成中';
      default: return status;
    }
  };

  return (
    <div className="card" style={{ borderLeft: '3px solid var(--border-focus)', padding: '12px 14px' }}>
      <div className="card-title" style={{ border: 'none', padding: 0 }}>
        <span>⚡ 合成任务状态</span>
        <button
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.74rem', fontFamily: 'var(--font-mono)' }}
          onClick={onClear}
        >
          关闭
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '2px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>任务 ID:</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-primary)' }}>{job.id.substring(0, 16)}...</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>任务状态:</span>
          <span className={`status-badge status-${job.status}`}>{getStatusText(job.status)}</span>
        </div>

        {job.status === 'failed' && job.error_message && (
          <div style={{
            background: 'oklch(0.60 0.18 25 / 0.08)',
            border: '1px solid oklch(0.60 0.18 25 / 0.15)',
            color: '#f87171',
            padding: '8px',
            borderRadius: '4px',
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            marginTop: '6px'
          }}>
            <strong>处理失败错误原因:</strong><br />
            {job.error_message}
          </div>
        )}

        {(job.status === 'queued' || job.status === 'running') && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '4px' }}>
            <div style={{ height: '3px', width: '100%', background: 'rgba(0, 0, 0, 0.08)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: job.status === 'running' ? '70%' : '20%',
                background: 'linear-gradient(90deg, var(--color-primary), var(--color-accent))',
                borderRadius: '2px',
                animation: job.status === 'running' ? 'signalPulseRunning 1.5s infinite ease-in-out' : 'signalPulseWarning 1.5s infinite ease-in-out'
              }} />
            </div>
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textAlign: 'center' }}>
              {job.status === 'running' ? '服务器正在合成转码音频中...' : '客户端队列排队中，等待执行...'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
export default JobStatusPanel;
