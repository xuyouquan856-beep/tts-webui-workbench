import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { ModelConfig } from '../types';
import { api } from '../api';
import { gsap } from 'gsap';
import { isExampleModel } from '../utils/helpers';
import { LocalTTSWizard } from './LocalTTSWizard';

interface ModelConfigPanelProps {
  models: ModelConfig[];
  selectedModelId: number;
  onSelectModel: (id: number) => void;
  onRefreshModels: (newModelId?: number) => void;
  providers: string[];
  showExamples: boolean;
  onDeleteModel: (id: number) => Promise<void>;
}

export const ModelConfigPanel: React.FC<ModelConfigPanelProps> = ({
  models,
  selectedModelId,
  onSelectModel,
  onRefreshModels,
  providers,
  showExamples,
  onDeleteModel,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelConfig | null>(null);
  const [dummyCollapsed, setDummyCollapsed] = useState(true);
  const [showWizard, setShowWizard] = useState(false);

  // Deletion state
  const [targetDeleteModel, setTargetDeleteModel] = useState<ModelConfig | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  // Form State
  const [name, setName] = useState('');
  const [providerType, setProviderType] = useState('dummy');
  const [apiBase, setApiBase] = useState('');
  const [modelName, setModelName] = useState('');
  const [commandTemplate, setCommandTemplate] = useState('');
  const [modelPath, setModelPath] = useState('');
  const [outputFormat, setOutputFormat] = useState('wav');
  const [enabled, setEnabled] = useState(true);
  const [paramsJson, setParamsJson] = useState('{}');
  const [errorMsg, setErrorMsg] = useState('');

  // Lock body scroll when modal is active
  useEffect(() => {
    if (showModal) {
      document.body.style.overflow = 'hidden';
      // Entrance animation using GSAP
      gsap.fromTo('.model-modal-overlay',
        { opacity: 0 },
        { opacity: 1, duration: 0.2, ease: 'power2.out' }
      );
      gsap.fromTo('.model-modal-content',
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

  const openCreateModal = () => {
    setEditingModel(null);
    setName('');
    setProviderType('dummy');
    setApiBase('');
    setModelName('');
    setCommandTemplate('');
    setModelPath('');
    setOutputFormat('wav');
    setEnabled(true);
    setParamsJson('{}');
    setErrorMsg('');
    setShowModal(true);
  };

  const openEditModal = (model: ModelConfig) => {
    setEditingModel(model);
    setName(model.name);
    setProviderType(model.provider_type);
    setApiBase(model.api_base || '');
    setModelName(model.model_name || '');
    setCommandTemplate(model.command_template || '');
    setModelPath(model.model_path || '');
    setOutputFormat(model.output_format);
    setEnabled(model.enabled);
    setParamsJson(model.params_json);
    setErrorMsg('');
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    // JSON Validation
    try {
      JSON.parse(paramsJson);
    } catch {
      setErrorMsg('默认参数 JSON 结构无效，请检查语法。');
      return;
    }

    const payload = {
      name,
      provider_type: providerType,
      api_base: apiBase || undefined,
      model_name: modelName || undefined,
      command_template: commandTemplate || undefined,
      model_path: modelPath || undefined,
      output_format: outputFormat,
      enabled,
      params_json: paramsJson,
    };

    try {
      let savedModel: ModelConfig;
      if (editingModel) {
        savedModel = await api.updateModel(editingModel.id, payload);
      } else {
        savedModel = await api.createModel(payload);
      }
      onRefreshModels(savedModel.id);
      setShowModal(false);
    } catch (err: any) {
      setErrorMsg(err.message || '保存模型配置失败。');
    }
  };

  // 1. Filtering logic based on showExamples
  const filteredModels = models.filter((m) => {
    if (m.id === selectedModelId) return true; // Always show currently active
    if (!showExamples && isExampleModel(m)) return false;
    return true;
  });

  // 2. Group definitions
  const groupDefinitions = [
    { type: 'higgs_api', label: '云端 API', badge: '云端' },
    { type: 'local_http', label: '本地 HTTP', badge: '本地' },
    { type: 'local_command', label: '本地命令', badge: '本地' },
    { type: 'piper', label: 'Piper 本地', badge: '本地' },
    { type: 'dummy', label: '调试/示例', badge: '调试' },
  ];

  // 3. Grouping models
  const grouped = groupDefinitions.map(group => {
    const groupModels = filteredModels.filter(m => m.provider_type === group.type);
    return {
      ...group,
      items: groupModels
    };
  }).filter(group => group.items.length > 0);

  return (
    <div className="card">
      <div className="card-title">
        <span>🤖 模型配置</span>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: '0.72rem', fontFamily: 'var(--font-mono)', cursor: 'pointer' }} onClick={() => setShowWizard(true)}>
            🧙 引导配置
          </button>
          <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: '0.72rem', fontFamily: 'var(--font-mono)', cursor: 'pointer' }} onClick={openCreateModal}>
            ＋ 添加
          </button>
        </div>
      </div>

      <div className="form-group">
        <label>当前激活模型</label>
        <select
          className="input-field"
          value={selectedModelId}
          onChange={(e) => onSelectModel(Number(e.target.value))}
        >
          {filteredModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} {!m.enabled ? '(已禁用)' : ''} ({m.provider_type})
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '4px' }}>
        {grouped.map((group) => {
          const isDummy = group.type === 'dummy';
          const isCollapsed = isDummy && dummyCollapsed;

          return (
            <div key={group.type} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  color: 'var(--text-secondary)',
                  textTransform: 'uppercase',
                  fontFamily: 'var(--font-mono)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '2px 4px',
                  borderBottom: '1px solid var(--border-color)',
                  cursor: isDummy ? 'pointer' : 'default',
                  userSelect: 'none'
                }}
                onClick={() => {
                  if (isDummy) {
                    setDummyCollapsed(!dummyCollapsed);
                  }
                }}
              >
                <span>{group.label}</span>
                <span style={{ fontSize: '0.58rem', color: 'var(--text-muted)', background: 'rgba(0, 0, 0, 0.03)', padding: '1px 5px', borderRadius: '3px', border: '1px solid var(--border-color)' }}>
                  {group.badge} {isDummy && (dummyCollapsed ? ' 展开 ＋' : ' 收起 －')}
                </span>
              </div>

              {!isCollapsed && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingLeft: '2px' }}>
                  {group.items.map((m) => {
                    const isSelected = selectedModelId === m.id;
                    const isExample = isExampleModel(m);
                    return (
                      <div
                        key={m.id}
                        className={`profile-card-item ${isSelected ? 'profile-card-selected' : ''}`}
                        style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px' }}
                        onClick={() => onSelectModel(m.id)}
                      >
                        <div style={{ flex: 1, minWidth: 0, marginRight: '8px' }}>
                          <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                            {isSelected && <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-accent)', boxShadow: '0 0 6px var(--color-accent-glow)' }} />}
                            <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{m.name}</span>
                            {isExample && (
                              <span style={{ fontSize: '0.58rem', fontFamily: 'var(--font-mono)', background: 'rgba(0, 0, 0, 0.05)', color: 'var(--text-muted)', padding: '1px 4px', borderRadius: '3px', border: '1px solid var(--border-color)' }}>
                                示例
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                            {m.provider_type} | {m.output_format} {!m.enabled ? '(已禁用)' : ''}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '3px 8px', fontSize: '0.7rem' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditModal(m);
                            }}
                          >
                            编辑
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '3px 8px', fontSize: '0.7rem', color: 'var(--color-error)' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteError('');
                              setTargetDeleteModel(m);
                            }}
                          >
                            删除
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Centered Modal Overlay Portal */}
      {showModal && ReactDOM.createPortal(
        <div className="model-modal-overlay">
          <div className="model-modal-content">
            <div className="model-modal-header">
              <h3>{editingModel ? '编辑模型配置' : '添加模型配置'}</h3>
              <button className="model-modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>

            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
              {errorMsg && (
                <div style={{ color: 'var(--color-error)', fontSize: '0.8rem', fontWeight: 500, padding: '0 20px', flexShrink: 0 }}>
                  ⚠️ {errorMsg}
                </div>
              )}

              {/* Scrollable Form Body */}
              <div className="model-modal-body">
                <div className="form-group">
                  <label>配置名称 *</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="例如：云端 Higgs 引擎"
                  />
                </div>

                <div className="form-group">
                  <label>TTS 提供商 *</label>
                  <select
                    className="input-field"
                    value={providerType}
                    onChange={(e) => setProviderType(e.target.value)}
                  >
                    {['dummy', 'higgs_api', 'local_http', 'local_command', 'piper'].map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Conditional rendering based on providerType */}
                {(providerType === 'higgs_api' || providerType === 'local_http') && (
                  <div className="form-group">
                    <label>API 基址 / 终结点 (HTTP/HTTPS 链接)</label>
                    <input
                      type="text"
                      className="input-field"
                      value={apiBase}
                      onChange={(e) => setApiBase(e.target.value)}
                      placeholder={providerType === 'higgs_api' ? "例如：https://api.boson.ai/v1/audio/speech" : "例如：http://127.0.0.1:8000/v1/audio/speech"}
                    />
                  </div>
                )}

                {providerType === 'piper' && (
                  <div className="form-group">
                    <label>Piper 执行命令或可执行文件路径</label>
                    <input
                      type="text"
                      className="input-field"
                      value={apiBase}
                      onChange={(e) => setApiBase(e.target.value)}
                      placeholder="例如：piper"
                    />
                  </div>
                )}

                {(providerType === 'higgs_api' || providerType === 'local_http') && (
                  <div className="form-group">
                    <label>模型参数名称 (API 参数)</label>
                    <input
                      type="text"
                      className="input-field"
                      value={modelName}
                      onChange={(e) => setModelName(e.target.value)}
                      placeholder={providerType === 'higgs_api' ? "例如：higgs-audio-v3-tts" : "例如：default"}
                    />
                  </div>
                )}

                {providerType === 'local_command' && (
                  <div className="form-group">
                    <label>执行命令模板</label>
                    <input
                      type="text"
                      className="input-field"
                      value={commandTemplate}
                      onChange={(e) => setCommandTemplate(e.target.value)}
                      placeholder='例如：python infer.py --text "{text}" --out "{output_path}" --model "{model_path}"'
                    />
                  </div>
                )}

                {(providerType === 'local_command' || providerType === 'piper') && (
                  <div className="form-group">
                    <label>本地模型权重文件路径</label>
                    <input
                      type="text"
                      className="input-field"
                      value={modelPath}
                      onChange={(e) => setModelPath(e.target.value)}
                      placeholder={providerType === 'piper' ? "例如：data/models/zh_CN-huayan-medium.onnx" : "例如：data/models/voice.pth"}
                    />
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label>首选输出格式</label>
                    <select
                      className="input-field"
                      value={outputFormat}
                      onChange={(e) => setOutputFormat(e.target.value)}
                    >
                      <option value="wav">wav</option>
                      <option value="mp3">mp3</option>
                      <option value="opus">opus</option>
                    </select>
                  </div>

                  <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '8px', paddingTop: '20px' }}>
                    <input
                      type="checkbox"
                      id="model_enabled"
                      checked={enabled}
                      onChange={(e) => setEnabled(e.target.checked)}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                    <label htmlFor="model_enabled" style={{ cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.74rem', textTransform: 'uppercase' }}>已启用</label>
                  </div>
                </div>

                <div className="form-group">
                  <label>默认缺省参数 JSON</label>
                  <textarea
                    className="input-field"
                    rows={3}
                    style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', resize: 'vertical' }}
                    value={paramsJson}
                    onChange={(e) => setParamsJson(e.target.value)}
                    placeholder='{"speed": 1.0, "pitch": 1.0}'
                  />
                </div>
              </div>

              {/* Sticky Footer */}
              <div className="model-modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  取消
                </button>
                <button type="submit" className="btn btn-primary">
                  保存配置
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}
      <LocalTTSWizard
        showModal={showWizard}
        onClose={() => setShowWizard(false)}
        onRefreshModels={onRefreshModels}
        models={models}
      />

      {/* Model Delete Confirmation Modal */}
      {targetDeleteModel && ReactDOM.createPortal(
        <div className="wizard-modal-overlay">
          <div className="wizard-modal-content" style={{ maxWidth: '380px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h4 style={{ margin: 0, fontSize: '0.98rem', color: 'var(--text-primary)' }}>
              {isExampleModel(targetDeleteModel) ? '🚨 这是系统示例配置，确定删除吗？' : '⚠️ 确定删除这个模型配置吗？'}
            </h4>
            <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              删除该模型配置将无法还原，但此操作**不会**删除您的历史生成记录和已生成的音频文件。
            </p>

            {deleteError && (
              <div style={{ color: 'var(--color-error)', fontSize: '0.74rem', fontWeight: 600, background: 'rgba(255, 94, 98, 0.08)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-error)' }}>
                {deleteError}
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={isDeleting}
                onClick={() => {
                  setTargetDeleteModel(null);
                  setDeleteError('');
                }}
              >
                取消
              </button>
              <button
                className="btn btn-primary btn-sm"
                style={{ background: 'var(--color-error)', color: '#fff', boxShadow: 'none' }}
                disabled={isDeleting}
                onClick={async () => {
                  setIsDeleting(true);
                  setDeleteError('');
                  try {
                    await onDeleteModel(targetDeleteModel.id);
                    setTargetDeleteModel(null);
                  } catch (err: any) {
                    let displayMsg = err.message;
                    try {
                      const parsed = JSON.parse(err.message);
                      if (parsed.code === 'BLOCKED_BY_PROFILES') {
                        const listStr = parsed.profiles.map((p: any) => `${p.name} (ID: ${p.id})`).join('、');
                        displayMsg = `${parsed.message}${listStr}`;
                      }
                    } catch (e) {}
                    setDeleteError(displayMsg);
                  } finally {
                    setIsDeleting(false);
                  }
                }}
              >
                {isDeleting ? '正在删除...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};
export default ModelConfigPanel;
