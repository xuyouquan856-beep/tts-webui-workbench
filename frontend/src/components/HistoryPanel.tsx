import React, { useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { Job } from '../types';
import { gsap } from 'gsap';
import { useGSAP } from '@gsap/react';

interface HistoryPanelProps {
  history: Job[];
  activeJobId: string | null;
  onSelectJob: (job: Job) => void;
  onReuseText: (text: string) => void;
  onReuseParams: (paramsJson: string, returnFormat: string) => void;
  onDeleteJob: (jobId: string, deleteAudio: boolean) => Promise<void>;
  onClearHistory: (deleteAudio: boolean) => Promise<void>;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  history,
  activeJobId,
  onSelectJob,
  onReuseText,
  onReuseParams,
  onDeleteJob,
  onClearHistory,
}) => {
  const listRef = useRef<HTMLDivElement>(null);

  // Modal states
  const [showDeleteModal, setShowDeleteModal] = useState<string | null>(null);
  const [showClearModal, setShowClearModal] = useState(false);
  const [deleteAudioFile, setDeleteAudioFile] = useState(false);

  // GSAP slide-in transition for new entries
  useGSAP(() => {
    if (history.length > 0) {
      gsap.fromTo('.history-item:first-child',
        { opacity: 0, y: -8, scale: 0.98 },
        { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: 'power2.out' }
      );
    }
  }, { scope: listRef, dependencies: [history.length] });

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
    <div className="card" style={{ flex: 1, minHeight: 0 }}>
      <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>📜 历史记录</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {history.length > 0 && (
            <button
              className="btn btn-secondary btn-sm"
              style={{
                padding: '2px 8px',
                fontSize: '0.7rem',
                color: 'var(--color-error)',
                border: '1.5px solid var(--border-color)',
                boxShadow: 'none',
                textTransform: 'none'
              }}
              onClick={() => {
                setDeleteAudioFile(false);
                setShowClearModal(true);
              }}
            >
              🗑️ 清空历史
            </button>
          )}
          <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
            数量: {history.length}
          </span>
        </div>
      </div>

      <div className="history-list" ref={listRef}>
        {history.length === 0 ? (
          <div style={{
            color: 'var(--text-muted)',
            textAlign: 'center',
            paddingTop: '60px',
            fontSize: '0.8rem',
            fontFamily: 'var(--font-mono)',
            lineHeight: '1.6'
          }}>
            暂无本地合成历史。<br />在中间区域输入并提交即可在此记录。
          </div>
        ) : (
          history.map((h) => {
            const isSelected = activeJobId === h.id;
            const dateStr = new Date(h.created_at + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

            // Extract original text from params if translated
            let originalText = '';
            try {
              if (h.params_json) {
                const parsed = JSON.parse(h.params_json);
                originalText = parsed.original_text || '';
              }
            } catch (e) {}

            return (
              <div
                key={h.id}
                className={`history-item ${isSelected ? 'active' : ''}`}
                onClick={() => onSelectJob(h)}
              >
                <div className="history-meta">
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem' }}>[{dateStr}]</span>
                  <span className={`status-badge status-${h.status}`}>{getStatusText(h.status)}</span>
                </div>

                <div className="history-text" style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  {originalText && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', borderBottom: '1px dashed var(--border-color)', paddingBottom: '3px', marginBottom: '2px' }}>
                      <span style={{ color: 'var(--color-primary)', opacity: 0.8, marginRight: '4px', fontWeight: 600 }}>原:</span>{originalText}
                    </div>
                  )}
                  <div>
                    {originalText && <span style={{ color: 'var(--color-success)', marginRight: '4px', fontWeight: 600 }}>译:</span>}
                    {h.text}
                  </div>
                </div>

                {h.status === 'succeeded' && h.duration && (
                  <div style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', borderTop: '1px solid oklch(1 0 0 / 0.03)', paddingTop: '4px', marginTop: '2px' }}>
                    <span>时长: {h.duration.toFixed(2)}秒</span>
                    <span>格式: {h.return_format.toUpperCase()}</span>
                  </div>
                )}

                <div className="history-actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '2px 6px', fontSize: '0.66rem', fontFamily: 'var(--font-mono)' }}
                    onClick={() => onReuseText(originalText || h.text)}
                  >
                    复用文本
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '2px 6px', fontSize: '0.66rem', fontFamily: 'var(--font-mono)' }}
                    onClick={() => onReuseParams(h.params_json, h.return_format)}
                  >
                    复用参数
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '2px 6px', fontSize: '0.66rem', fontFamily: 'var(--font-mono)', color: 'var(--color-error)' }}
                    onClick={() => {
                      setDeleteAudioFile(false);
                      setShowDeleteModal(h.id);
                    }}
                  >
                    删除
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && ReactDOM.createPortal(
        <div className="wizard-modal-overlay">
          <div className="wizard-modal-content" style={{ maxWidth: '360px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h4 style={{ margin: 0, fontSize: '0.98rem', color: 'var(--text-primary)' }}>⚠️ 确定删除这条历史记录吗？</h4>
            <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              此操作将把该条记录从本地数据库中清除，此过程不可逆。
            </p>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', color: 'var(--text-primary)', cursor: 'pointer', userSelect: 'none' }}>
              <input
                type="checkbox"
                checked={deleteAudioFile}
                onChange={(e) => setDeleteAudioFile(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              同时从本地磁盘删除生成的音频文件
            </label>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowDeleteModal(null)}>取消</button>
              <button
                className="btn btn-primary btn-sm"
                style={{ background: 'var(--color-error)', color: '#fff', boxShadow: 'none' }}
                onClick={async () => {
                  await onDeleteJob(showDeleteModal, deleteAudioFile);
                  setShowDeleteModal(null);
                }}
              >
                确认删除
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Clear All Confirmation Modal */}
      {showClearModal && ReactDOM.createPortal(
        <div className="wizard-modal-overlay">
          <div className="wizard-modal-content" style={{ maxWidth: '380px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h4 style={{ margin: 0, fontSize: '0.98rem', color: 'var(--color-error)' }}>🚨 危险操作：确认清空所有历史记录吗？</h4>
            <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              此操作将**永久清空**本地所有的 TTS 语音合成历史记录及排队任务！
            </p>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', color: 'var(--text-primary)', cursor: 'pointer', userSelect: 'none' }}>
              <input
                type="checkbox"
                checked={deleteAudioFile}
                onChange={(e) => setDeleteAudioFile(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              同时彻底删除本地磁盘中的全部生成音频文件
            </label>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowClearModal(false)}>取消</button>
              <button
                className="btn btn-primary btn-sm"
                style={{ background: 'var(--color-error)', color: '#fff', boxShadow: 'none' }}
                onClick={async () => {
                  await onClearHistory(deleteAudioFile);
                  setShowClearModal(false);
                }}
              >
                💥 确认清空全部
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default HistoryPanel;
