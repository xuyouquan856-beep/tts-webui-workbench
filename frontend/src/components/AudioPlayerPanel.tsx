import React, { useEffect, useRef } from 'react';
import { Job } from '../types';
import { resolveUrl } from '../api';

interface AudioPlayerPanelProps {
  job: Job | null;
}

export const AudioPlayerPanel: React.FC<AudioPlayerPanelProps> = ({ job }) => {
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (job && audioRef.current) {
      audioRef.current.load();
      audioRef.current.play().catch(() => {
        // Autoplay blocked by browser policy, user needs to click play
      });
    }
  }, [job]);

  if (!job || job.status !== 'succeeded' || !job.audio_url) return null;

  return (
    <div className="player-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
        <span style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-success)', display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-success)', boxShadow: '0 0 6px var(--color-success-glow)' }} />
          🔊 监听到音频输出
        </span>
        <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
          {job.duration ? `${job.duration.toFixed(2)}秒` : '0.00秒'} | {job.return_format.toUpperCase()}
        </span>
      </div>

      {(() => {
        let originalText = '';
        try {
          if (job.params_json) {
            const parsed = JSON.parse(job.params_json);
            originalText = parsed.original_text || '';
          }
        } catch (e) {}

        return (
          <div className="player-text" style={{ fontStyle: 'italic', fontSize: '0.82rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {originalText && (
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--color-primary)', marginRight: '4px', fontWeight: 600 }}>[原输入]</span> "{originalText}"
              </div>
            )}
            <div>
              {originalText && <span style={{ color: 'var(--color-success)', marginRight: '4px', fontWeight: 600 }}>[合成文]</span>}
              "{job.text}"
            </div>
          </div>
        );
      })()}

      {/* Decorative waveform representation bars */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '2px', height: '14px', margin: '4px 0', padding: '0 4px' }}>
        <div style={{ flex: 1, height: '30%', background: 'var(--color-primary-glow)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '60%', background: 'var(--color-primary-glow)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '40%', background: 'var(--color-accent-glow)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '80%', background: 'var(--color-primary)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '50%', background: 'var(--color-accent)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '90%', background: 'var(--color-success)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '30%', background: 'var(--color-primary)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '70%', background: 'var(--color-accent)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '40%', background: 'var(--color-primary-glow)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '50%', background: 'var(--color-accent-glow)', borderRadius: '1px' }} />
        <div style={{ flex: 1, height: '20%', background: 'var(--color-primary-glow)', borderRadius: '1px' }} />
      </div>

      {/* Standard audio element */}
      <audio ref={audioRef} controls src={resolveUrl(job.audio_url)}>
        您的浏览器不支持播放该音频。
      </audio>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: '6px' }}>
        <span>任务ID: {job.id.substring(0, 8)}...</span>
        <a 
          href={resolveUrl(job.audio_url)} 
          download={`tts_${job.id}.${job.return_format}`}
          className="btn btn-secondary btn-sm"
          style={{ textTransform: 'uppercase', fontSize: '0.66rem', padding: '1px 6px', fontFamily: 'var(--font-mono)' }}
        >
          下载音频
        </a>
      </div>
    </div>
  );
};
export default AudioPlayerPanel;
