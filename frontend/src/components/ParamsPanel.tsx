import React from 'react';

interface ParamsPanelProps {
  speed: number;
  onChangeSpeed: (val: number) => void;
  pitch: number;
  onChangePitch: (val: number) => void;
  temperature: number;
  onChangeTemperature: (val: number) => void;
  returnFormat: string;
  onChangeReturnFormat: (val: string) => void;
  payloadMode: string;
  onChangePayloadMode: (val: string) => void;
  showPayloadMode: boolean; // only for local_http provider
}

export const ParamsPanel: React.FC<ParamsPanelProps> = ({
  speed,
  onChangeSpeed,
  pitch,
  onChangePitch,
  temperature,
  onChangeTemperature,
  returnFormat,
  onChangeReturnFormat,
  payloadMode,
  onChangePayloadMode,
  showPayloadMode,
}) => {
  return (
    <div className="card">
      <div className="card-title">
        <span>🎛️ 声音合成参数</span>
      </div>

      <div className="params-grid">
        {/* Speed */}
        <div className="slider-group">
          <div className="slider-label">
            <span>语速 (Speed)</span>
            <span className="slider-val">{speed.toFixed(1)}x</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            className="slider-input"
            value={speed}
            onChange={(e) => onChangeSpeed(Number(e.target.value))}
          />
        </div>

        {/* Pitch */}
        <div className="slider-group">
          <div className="slider-label">
            <span>音调 (Pitch)</span>
            <span className="slider-val">{pitch.toFixed(1)}x</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            className="slider-input"
            value={pitch}
            onChange={(e) => onChangePitch(Number(e.target.value))}
          />
        </div>

        {/* Temperature */}
        <div className="slider-group">
          <div className="slider-label">
            <span>采样温度 (Temp)</span>
            <span className="slider-val">{temperature.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0.0"
            max="1.0"
            step="0.05"
            className="slider-input"
            value={temperature}
            onChange={(e) => onChangeTemperature(Number(e.target.value))}
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: showPayloadMode ? '1fr 1fr' : '1fr', gap: '12px', marginTop: '4px' }}>
        <div className="form-group">
          <label>音频输出格式</label>
          <select
            className="input-field"
            value={returnFormat}
            onChange={(e) => onChangeReturnFormat(e.target.value)}
          >
            <option value="wav">WAV (无损格式)</option>
            <option value="mp3">MP3 (压缩格式)</option>
            <option value="opus">OPUS (高压缩高效率)</option>
          </select>
        </div>

        {showPayloadMode && (
          <div className="form-group">
            <label>API 负载协议模式 (local_http)</label>
            <select
              className="input-field"
              value={payloadMode}
              onChange={(e) => onChangePayloadMode(e.target.value)}
            >
              <option value="openai_audio_speech">OpenAI 兼容协议</option>
              <option value="generic_json">通用 JSON 结构</option>
            </select>
          </div>
        )}
      </div>
    </div>
  );
};
export default ParamsPanel;
