import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { ModelConfig } from '../types';
import { api } from '../api';
import { gsap } from 'gsap';

interface LocalTTSWizardProps {
  showModal: boolean;
  onClose: () => void;
  onRefreshModels: (newModelId?: number) => void;
  models: ModelConfig[];
}

type Mode = 'piper' | 'local_http' | 'local_command';

export const LocalTTSWizard: React.FC<LocalTTSWizardProps> = ({
  showModal,
  onClose,
  onRefreshModels,
  models,
}) => {
  const [activeMode, setActiveMode] = useState<Mode>('piper');

  // Form Fields
  const [name, setName] = useState('');
  // Mode-specific fields
  const [apiBase, setApiBase] = useState(''); // used for piper executable path or http endpoint url
  const [modelPath, setModelPath] = useState(''); // used for piper .onnx path or local script .pth path
  const [modelName, setModelName] = useState('default'); // used for local_http model name parameter
  const [payloadMode, setPayloadMode] = useState('openai_audio_speech'); // used for local_http protocol
  const [commandTemplate, setCommandTemplate] = useState(''); // used for local_command template

  // State trackers
  const [createdModelId, setCreatedModelId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [testStatus, setTestStatus] = useState<'idle' | 'saving' | 'generating' | 'polling' | 'success' | 'failed'>('idle');
  const [testResultMsg, setTestResultMsg] = useState('');
  const [testJobId, setTestJobId] = useState<string | null>(null);

  // Lock body scroll when modal is active
  useEffect(() => {
    if (showModal) {
      document.body.style.overflow = 'hidden';
      // GSAP animations for modal entry
      gsap.fromTo('.wizard-modal-overlay',
        { opacity: 0 },
        { opacity: 1, duration: 0.2, ease: 'power2.out' }
      );
      gsap.fromTo('.wizard-modal-content',
        { scale: 0.96, y: 15, opacity: 0 },
        { scale: 1, y: 0, opacity: 1, duration: 0.3, ease: 'power3.out' }
      );
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [showModal]);

  // Reset fields when switching modes
  const handleModeChange = (mode: Mode) => {
    setActiveMode(mode);
    setErrorMsg('');
    setTestStatus('idle');
    setTestResultMsg('');
    setCreatedModelId(null);
    setTestJobId(null);

    // Initial placeholder values
    if (mode === 'piper') {
      setName('本地 Piper ONNX 引擎');
      setApiBase('piper');
      setModelPath('data/models/zh_CN-huayan-medium.onnx');
    } else if (mode === 'local_http') {
      setName('本地 HTTP 音频服务');
      setApiBase('http://127.0.0.1:5000/v1/audio/speech');
      setModelName('default');
      setPayloadMode('openai_audio_speech');
    } else if (mode === 'local_command') {
      setName('本地命令行推理脚本');
      setCommandTemplate('python C:\\tts-models\\infer.py --text "{text}" --out "{output_path}" --model "{model_path}"');
      setModelPath('data/models/voice.pth');
    }
  };

  // Set default values once on initial open
  useEffect(() => {
    if (showModal) {
      handleModeChange('piper');
    }
  }, [showModal]);

  // Form Validation
  const validateForm = (): boolean => {
    if (!name.trim()) {
      setErrorMsg('配置名称不能为空。');
      return false;
    }

    if (activeMode === 'piper') {
      if (!apiBase.trim()) {
        setErrorMsg('Piper 执行命令/路径为必填项（例如：piper）。');
        return false;
      }
      if (!modelPath.trim()) {
        setErrorMsg('本地 ONNX 模型文件路径为必填项。');
        return false;
      }
      if (!modelPath.endsWith('.onnx')) {
        setErrorMsg('ONNX 模型文件路径必须以 .onnx 结尾。');
        return false;
      }
    } else if (activeMode === 'local_http') {
      if (!apiBase.trim()) {
        setErrorMsg('API 终结点 (HTTP URL) 为必填项。');
        return false;
      }
      if (!apiBase.startsWith('http://') && !apiBase.startsWith('https://')) {
        setErrorMsg('API 终结点必须以 http:// 或 https:// 开头。');
        return false;
      }
    } else if (activeMode === 'local_command') {
      if (!commandTemplate.trim()) {
        setErrorMsg('执行命令模板为必填项。');
        return false;
      }
      if (!commandTemplate.includes('{text}')) {
        setErrorMsg('命令模板必须包含文本占位符 {text}。');
        return false;
      }
      if (!commandTemplate.includes('{output_path}')) {
        setErrorMsg('命令模板必须包含输出音频路径占位符 {output_path}。');
        return false;
      }
    }

    return true;
  };

  // Compile payload to send to FastAPI
  const getPayload = () => {
    if (activeMode === 'piper') {
      return {
        name,
        provider_type: 'piper',
        api_base: apiBase,
        model_path: modelPath,
        output_format: 'wav',
        enabled: true,
        params_json: '{}',
      };
    } else if (activeMode === 'local_http') {
      return {
        name,
        provider_type: 'local_http',
        api_base: apiBase,
        model_name: modelName,
        output_format: 'mp3',
        enabled: true,
        params_json: JSON.stringify({ payload_mode: payloadMode }),
      };
    } else {
      return {
        name,
        provider_type: 'local_command',
        command_template: commandTemplate,
        model_path: modelPath || undefined,
        output_format: 'wav',
        enabled: true,
        params_json: '{}',
      };
    }
  };

  // Silent Save model config
  const saveConfig = async (): Promise<number | null> => {
    setErrorMsg('');
    if (!validateForm()) return null;

    setTestStatus('saving');
    const payload = getPayload();

    try {
      if (createdModelId) {
        // Reuse and update config to prevent duplicate rows on retry
        await api.updateModel(createdModelId, payload);
        onRefreshModels(createdModelId);
        localStorage.setItem('active_model_id', createdModelId.toString());
        return createdModelId;
      } else {
        // Create new config
        const created = await api.createModel(payload);
        setCreatedModelId(created.id);
        onRefreshModels(created.id);
        localStorage.setItem('active_model_id', created.id.toString());
        return created.id;
      }
    } catch (err: any) {
      setErrorMsg(`保存配置失败: ${err.message}`);
      setTestStatus('failed');
      return null;
    }
  };

  // Save and Test configuration
  const handleSaveAndTest = async () => {
    const savedId = await saveConfig();
    if (!savedId) return;

    setTestStatus('generating');
    try {
      const testText = "本地语音合成测试。";
      const res = await api.generateSpeech({
        text: testText,
        model_id: savedId,
        params: {},
        return_format: activeMode === 'local_http' ? 'mp3' : 'wav',
      });

      setTestJobId(res.job_id);
      setTestStatus('polling');
      pollTestJob(res.job_id);
    } catch (err: any) {
      setTestStatus('failed');
      setTestResultMsg(`发送测试合成指令失败: ${err.message}`);
    }
  };

  // Poll Job Status for test result
  const pollTestJob = (jobId: string) => {
    let attempts = 0;
    const maxAttempts = 30; // 30 seconds timeout

    const timer = setInterval(async () => {
      attempts++;
      try {
        const job = await api.getJobStatus(jobId);
        if (job.status === 'succeeded') {
          clearInterval(timer);
          setTestStatus('success');
          setTestResultMsg('测试成功！已自动选中该配置，且测试音频已成功生成至右侧历史记录。');
          // Refresh list to show test job in archive
          onRefreshModels(createdModelId || undefined);
        } else if (job.status === 'failed') {
          clearInterval(timer);
          setTestStatus('failed');
          setTestResultMsg(`合成失败。后台返回错误: ${job.error_message}`);
        }
      } catch (err: any) {
        clearInterval(timer);
        setTestStatus('failed');
        setTestResultMsg(`轮询生成任务状态出错: ${err.message}`);
      }

      if (attempts >= maxAttempts) {
        clearInterval(timer);
        setTestStatus('failed');
        setTestResultMsg('测试超时：音频生成时间过长，请检查本地环境依赖或可执行指令是否正常。');
      }
    }, 1000);
  };

  if (!showModal) return null;

  return ReactDOM.createPortal(
    <div className="wizard-modal-overlay">
      <div className="wizard-modal-content" style={{ display: 'flex', flexDirection: 'column', maxHeight: '86dvh', width: '90%', maxWidth: '620px', background: 'var(--modal-bg)', border: '1px solid var(--border-color)', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 20px 48px rgba(0,0,0,0.08)' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-color)', flexShrink: 0 }}>
          <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>🧙 本地 TTS 引导配置向导</h3>
          <button style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.2rem' }} onClick={onClose}>✕</button>
        </div>

        {/* Tab selection */}
        <div style={{ display: 'flex', padding: '8px 20px', gap: '8px', background: 'rgba(0, 0, 0, 0.01)', borderBottom: '1px solid var(--border-color)', flexShrink: 0 }}>
          <button
            type="button"
            className={`btn ${activeMode === 'piper' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '6px 12px', fontSize: '0.76rem', borderRadius: '6px' }}
            onClick={() => handleModeChange('piper')}
          >
            Piper 本地 ONNX
          </button>
          <button
            type="button"
            className={`btn ${activeMode === 'local_http' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '6px 12px', fontSize: '0.76rem', borderRadius: '6px' }}
            onClick={() => handleModeChange('local_http')}
          >
            本地 HTTP 服务
          </button>
          <button
            type="button"
            className={`btn ${activeMode === 'local_command' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '6px 12px', fontSize: '0.76rem', borderRadius: '6px' }}
            onClick={() => handleModeChange('local_command')}
          >
            本地命令行脚本
          </button>
        </div>

        {/* Form Body */}
        <div className="model-modal-body" style={{ flex: 1, overflowY: 'auto', padding: '20px', minHeight: 0 }}>
          {errorMsg && (
            <div style={{ color: 'var(--color-error)', fontSize: '0.78rem', fontWeight: 500, background: 'rgba(248, 113, 113, 0.08)', padding: '8px 12px', borderRadius: '6px', marginBottom: '14px', border: '1px solid rgba(248, 113, 113, 0.15)' }}>
              ⚠️ {errorMsg}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div className="form-group">
              <label>配置显示名称 *</label>
              <input
                type="text"
                required
                className="input-field"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：本地 Piper 引擎"
              />
            </div>

            {/* PIPER MODE */}
            {activeMode === 'piper' && (
              <>
                <div className="form-group">
                  <label>Piper 执行命令或可执行文件路径 *</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={apiBase}
                    onChange={(e) => setApiBase(e.target.value)}
                    placeholder="系统 PATH 环境变量已配置则填 piper，否则填绝对路径"
                  />
                </div>

                <div className="form-group">
                  <label>本地 .onnx 模型文件路径 *</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={modelPath}
                    onChange={(e) => setModelPath(e.target.value)}
                    placeholder="例如：data/models/zh_CN-huayan-medium.onnx"
                  />
                </div>

                <div style={{ fontSize: '0.74rem', background: 'oklch(0.62 0.16 120 / 0.06)', border: '1px solid oklch(0.62 0.16 120 / 0.12)', color: 'oklch(0.72 0.16 120)', padding: '10px 14px', borderRadius: '6px', lineHeight: '1.4' }}>
                  💡 <strong>提示：</strong><br />
                  1. 请确保您的 <strong>.onnx</strong> 模型权重文件与对应的 <strong>.onnx.json</strong> 配置文件放置在<strong>同一个文件夹</strong>中，且文件名必须完全一致（仅扩展名不同）。<br />
                  2. 引擎运行时将根据这两个文件在本地直接进行高速 CPU 推理，不依赖任何网络连接。
                </div>
              </>
            )}

            {/* LOCAL HTTP MODE */}
            {activeMode === 'local_http' && (
              <>
                <div className="form-group">
                  <label>API 终结点 (Endpoint URL) *</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={apiBase}
                    onChange={(e) => setApiBase(e.target.value)}
                    placeholder="例如：http://127.0.0.1:5000/v1/audio/speech"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label>负载协议模式</label>
                    <select
                      className="input-field"
                      value={payloadMode}
                      onChange={(e) => setPayloadMode(e.target.value)}
                    >
                      <option value="openai_audio_speech">OpenAI 兼容协议 (/v1/audio/speech)</option>
                      <option value="generic_json">通用 JSON 结构 (Generic JSON)</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label>模型标识 (Model Parameter)</label>
                    <input
                      type="text"
                      className="input-field"
                      value={modelName}
                      onChange={(e) => setModelName(e.target.value)}
                      placeholder="发送至 API 的 model 字段值"
                    />
                  </div>
                </div>

                <div style={{ fontSize: '0.74rem', background: 'oklch(0.62 0.16 120 / 0.06)', border: '1px solid oklch(0.62 0.16 120 / 0.12)', color: 'oklch(0.72 0.16 120)', padding: '10px 14px', borderRadius: '6px', lineHeight: '1.4' }}>
                  💡 <strong>提示与支持格式：</strong><br />
                  1. 本地 HTTP 模式常用于对接 GPT-SoVITS、ChatTTS、CosyVoice 等本地部署的 HTTP 服务接口。<br />
                  2. 服务接口响应应当返回直接的可播放二进制音频流（如 WAV/MP3 媒体流），或符合 Base64 格式的规范音频数据载荷。
                </div>
              </>
            )}

            {/* LOCAL COMMAND MODE */}
            {activeMode === 'local_command' && (
              <>
                <div className="form-group">
                  <label>命令执行模板 *</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={commandTemplate}
                    onChange={(e) => setCommandTemplate(e.target.value)}
                    placeholder='例如：python infer.py --text "{text}" --out "{output_path}"'
                  />
                </div>

                <div className="form-group">
                  <label>本地模型路径 (可选参数)</label>
                  <input
                    type="text"
                    className="input-field"
                    value={modelPath}
                    onChange={(e) => setModelPath(e.target.value)}
                    placeholder="对应 {model_path} 占位符的内容"
                  />
                </div>

                <div style={{ fontSize: '0.74rem', background: 'oklch(0.62 0.16 120 / 0.06)', border: '1px solid oklch(0.62 0.16 120 / 0.12)', color: 'oklch(0.72 0.16 120)', padding: '10px 14px', borderRadius: '6px', lineHeight: '1.4', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div>
                    🛠️ <strong>占位符映射说明（在命令执行时将被自动替换）：</strong><br />
                    • <code style={{ color: '#fff' }}>{"{text}"}</code>：待合成文本输入（自动处理 shell 转义防止注入）<br />
                    • <code style={{ color: '#fff' }}>{"{output_path}"}</code>：后端指定保存的本地音频文件写入路径（<strong>必填</strong>）<br />
                    • <code style={{ color: '#fff' }}>{"{model_path}"}</code>：对应上方“本地模型路径”输入的内容<br />
                    • <code style={{ color: '#fff' }}>{"{ref_audio_path}"}</code> 和 <code style={{ color: '#fff' }}>{"{ref_text}"}</code>：配置了克隆声音时的参考音频物理路径与文本
                  </div>
                  <div style={{ borderTop: '1px solid oklch(0.62 0.16 120 / 0.15)', paddingTop: '6px' }}>
                    ⚠️ <strong>性能与环境建议：</strong><br />
                    复杂的 TTS 神经网络权重推理耗费较大。建议命令模板中指定其外部的专属 Python 虚拟环境（如：<code style={{ color: '#fff' }}>C:\tts-models\venv\Scripts\python.exe infer.py ...</code>），请勿污染和挤占 WebUI 后台自身的精简 Python 环境。
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Test Status Banner */}
          {testStatus !== 'idle' && (
            <div style={{
              marginTop: '16px',
              padding: '12px 16px',
              borderRadius: '6px',
              fontSize: '0.8rem',
              background: testStatus === 'success' ? 'rgba(52, 211, 153, 0.08)' : testStatus === 'failed' ? 'rgba(248, 113, 113, 0.08)' : 'rgba(91, 127, 245, 0.06)',
              border: `1px solid ${testStatus === 'success' ? 'rgba(52, 211, 153, 0.2)' : testStatus === 'failed' ? 'rgba(248, 113, 113, 0.2)' : 'rgba(91, 127, 245, 0.12)'}`,
              color: testStatus === 'success' ? 'var(--color-success)' : testStatus === 'failed' ? 'var(--color-error)' : 'var(--text-primary)',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                {(testStatus === 'saving' || testStatus === 'generating' || testStatus === 'polling') && (
                  <div style={{ border: '2px solid transparent', borderLeftColor: 'currentColor', borderRadius: '50%', width: '12px', height: '12px', animation: 'spin 0.8s linear infinite', marginRight: '4px' }} />
                )}
                {testStatus === 'saving' && '正在保存向导配置...'}
                {testStatus === 'generating' && '已发送测试指令，正在初始化音频合成任务...'}
                {testStatus === 'polling' && '音频正在本地合成与转码中，请耐心等候...'}
                {testStatus === 'success' && '✓ 合成测试通过'}
                {testStatus === 'failed' && '⚠️ 测试失败'}
              </div>
              {testResultMsg && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {testResultMsg}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', borderTop: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.01)', flexShrink: 0 }}>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={testStatus === 'saving' || testStatus === 'generating' || testStatus === 'polling'}
            onClick={onClose}
          >
            关闭向导
          </button>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={testStatus === 'saving' || testStatus === 'generating' || testStatus === 'polling'}
              onClick={async () => {
                const savedId = await saveConfig();
                if (savedId) {
                  setTestStatus('success');
                  setTestResultMsg('配置保存成功！已自动切换并选中此配置。');
                }
              }}
            >
              仅保存
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={testStatus === 'saving' || testStatus === 'generating' || testStatus === 'polling'}
              onClick={handleSaveAndTest}
            >
              保存并测试配置
            </button>
          </div>
        </div>
      </div>
      <style>{`
        .wizard-modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: var(--modal-overlay);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 9999;
          backdrop-filter: blur(8px);
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>,
    document.body
  );
};
export default LocalTTSWizard;
