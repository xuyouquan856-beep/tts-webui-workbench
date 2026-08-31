import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { VoiceProfile, ModelConfig } from '../types';
import { api } from '../api';
import { gsap } from 'gsap';
import { isExampleProfile } from '../utils/helpers';

interface VoiceProfilePanelProps {
  profiles: VoiceProfile[];
  models: ModelConfig[];
  selectedModelId: number;
  selectedProfileId: number | undefined;
  onSelectProfile: (id: number | undefined) => void;
  onRefreshProfiles: (newProfileId?: number) => void;
  showExamples: boolean;
  onDeleteProfile: (id: number, deleteRefAudio: boolean) => Promise<void>;
}

export const VoiceProfilePanel: React.FC<VoiceProfilePanelProps> = ({
  profiles,
  models,
  selectedModelId,
  selectedProfileId,
  onSelectProfile,
  onRefreshProfiles,
  showExamples,
  onDeleteProfile,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [targetDeleteProfile, setTargetDeleteProfile] = useState<VoiceProfile | null>(null);
  const [deleteRefAudioFile, setDeleteRefAudioFile] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [name, setName] = useState('');
  const [language, setLanguage] = useState('ja');
  const [modelId, setModelId] = useState<number | undefined>(undefined);
  const [refText, setRefText] = useState('');
  const [defaultParamsJson, setDefaultParamsJson] = useState('{}');
  const [errorMsg, setErrorMsg] = useState('');

  // Lock body scroll when modal is active
  useEffect(() => {
    if (showModal) {
      document.body.style.overflow = 'hidden';
      // GSAP timeline for entry
      gsap.fromTo('.modal-overlay',
        { opacity: 0 },
        { opacity: 1, duration: 0.2, ease: 'power2.out' }
      );
      gsap.fromTo('.modal-content',
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

  // Audio Upload State
  const [uploadProfileId, setUploadProfileId] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState('');

  const openCreateModal = () => {
    setName('');
    setLanguage('ja');
    setModelId(models.find(m => m.id === selectedModelId)?.id || models[0]?.id);
    setRefText('');
    setDefaultParamsJson('{}');
    setErrorMsg('');
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    // JSON Validation
    try {
      JSON.parse(defaultParamsJson);
    } catch {
      setErrorMsg('默认参数 JSON 结构无效，请检查语法。');
      return;
    }

    const selectedModel = models.find((m) => m.id === modelId);
    if (!selectedModel) {
      setErrorMsg('请选择一个有效的关联模型。');
      return;
    }

    const payload = {
      name,
      language,
      provider_type: selectedModel.provider_type,
      model_id: modelId,
      ref_text: refText || undefined,
      default_params_json: defaultParamsJson,
    };

    try {
      const created = await api.createProfile(payload);
      onRefreshProfiles(created.id);
      setShowModal(false);
    } catch (err: any) {
      setErrorMsg(err.message || '创建声音配置失败。');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadAudio = async (profileId: number) => {
    if (!selectedFile) return;
    setUploadStatus('正在上传...');
    try {
      await api.uploadReferenceAudio(profileId, selectedFile);
      setUploadStatus('音频上传克隆成功！');
      setSelectedFile(null);
      setUploadProfileId(null);
      onRefreshProfiles(profileId);
      setTimeout(() => setUploadStatus(''), 3000);
    } catch (err: any) {
      setUploadStatus(`上传失败: ${err.message}`);
    }
  };

  // 1. Filtering logic based on showExamples
  const filteredProfiles = profiles.filter((p) => {
    if (p.id === selectedProfileId) return true; // Always show active selection
    if (!showExamples && isExampleProfile(p)) return false; // Hide seed examples by name
    return true;
  });

  // 2. Grouping profiles by associated model/provider
  const grouped: { [key: string]: { label: string; items: VoiceProfile[] } } = {};
  filteredProfiles.forEach((p) => {
    const linkedModel = models.find((m) => m.id === p.model_id);
    const key = p.model_id ? `model-${p.model_id}` : `provider-${p.provider_type}`;
    const label = linkedModel ? `${linkedModel.name}` : `其他提供商: ${p.provider_type}`;
    if (!grouped[key]) {
      grouped[key] = { label, items: [] };
    }
    grouped[key].items.push(p);
  });

  // 3. Mismatch warning strip
  const activeProfile = profiles.find((p) => p.id === selectedProfileId);
  const isProfileMismatch = activeProfile && activeProfile.model_id !== selectedModelId;

  return (
    <div className="card">
      <div className="card-title">
        <span>🗣️ 声音配置</span>
        <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }} onClick={openCreateModal}>
          ＋ 添加
        </button>
      </div>

      <div className="form-group">
        <label>当前激活声音</label>
        <select
          className="input-field"
          value={selectedProfileId || ''}
          onChange={(e) => onSelectProfile(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">不使用声音配置（标准输出）</option>
          {filteredProfiles.map((p) => {
            const linkedModel = models.find(m => m.id === p.model_id);
            return (
              <option key={p.id} value={p.id}>
                {p.name} [{p.language.toUpperCase()}] ({linkedModel?.name || p.provider_type})
              </option>
            );
          })}
        </select>

        {isProfileMismatch && (
          <div style={{
            color: '#f87171',
            background: 'oklch(0.60 0.18 25 / 0.08)',
            border: '1px solid oklch(0.60 0.18 25 / 0.15)',
            padding: '8px 10px',
            borderRadius: '6px',
            fontSize: '0.74rem',
            fontFamily: 'var(--font-mono)',
            marginTop: '6px',
            lineHeight: '1.4',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px'
          }}>
            <span>⚠️ 当前声音关联的模型与激活的模型不一致！</span>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              声音关联模型 ID: {activeProfile?.model_id} | 当前激活模型 ID: {selectedModelId}
            </span>
          </div>
        )}
      </div>

      <div className="profile-grid-list" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '4px' }}>
        {Object.values(grouped).map((group) => (
          <div key={group.label} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              fontFamily: 'var(--font-mono)',
              padding: '2px 4px',
              borderBottom: '1px solid var(--border-color)'
            }}>
              {group.label}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {group.items.map((p) => {
                const isSelected = selectedProfileId === p.id;
                const hasRefAudio = !!p.ref_audio_path;
                const linkedModel = models.find((m) => m.id === p.model_id);
                const isExample = isExampleProfile(p);

                return (
                  <div
                    key={p.id}
                    className={`profile-card-item ${isSelected ? 'profile-card-selected' : ''}`}
                    style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '6px', padding: '10px' }}
                    onClick={() => onSelectProfile(p.id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        {isSelected && <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-primary)', boxShadow: '0 0 6px var(--color-primary-glow)' }} />}
                        <span>{p.name}</span>
                        <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          [{p.language.toUpperCase()}]
                        </span>
                        {isExample && (
                          <span style={{ fontSize: '0.58rem', fontFamily: 'var(--font-mono)', background: 'oklch(1 0 0 / 0.05)', color: 'var(--text-muted)', padding: '1px 4px', borderRadius: '3px', border: '1px solid oklch(1 0 0 / 0.05)' }}>
                            示例
                          </span>
                        )}
                      </div>
                      <div style={{
                        fontSize: '0.64rem',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        color: hasRefAudio ? 'var(--color-success)' : 'var(--text-muted)',
                        border: `1px solid ${hasRefAudio ? 'rgba(52, 211, 153, 0.3)' : 'var(--border-color)'}`,
                        background: hasRefAudio ? 'rgba(52, 211, 153, 0.05)' : 'transparent',
                        padding: '1px 5px',
                        borderRadius: '3px'
                      }}>
                        {hasRefAudio ? '已配音频' : '无参考音频'}
                      </div>
                    </div>

                    <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      模型: {linkedModel?.name || `ID: ${p.model_id}`} | {p.provider_type}
                    </div>

                    {p.ref_text && (
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', background: 'rgba(0, 0, 0, 0.03)', padding: '5px 8px', borderRadius: '4px', fontStyle: 'italic', borderLeft: '2px solid var(--color-primary)' }}>
                        文本: "{p.ref_text}"
                      </div>
                    )}

                    {/* Upload reference Audio section */}
                    {uploadProfileId === p.id ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '8px', background: 'rgba(0, 0, 0, 0.01)', border: '1px solid var(--border-color)', borderRadius: '6px', marginTop: '4px' }} onClick={(e) => e.stopPropagation()}>
                        <input type="file" accept="audio/*" onChange={handleFileChange} style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }} />
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '4px' }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => setUploadProfileId(null)}>取消</button>
                          <button className="btn btn-primary btn-sm" disabled={!selectedFile} onClick={() => handleUploadAudio(p.id)}>上传</button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px', marginTop: '2px' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.66rem', padding: '2px 6px', fontFamily: 'var(--font-mono)' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setUploadProfileId(p.id);
                          }}
                        >
                          {hasRefAudio ? '重新克隆音频' : '上传克隆音频'}
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.66rem', padding: '2px 6px', fontFamily: 'var(--font-mono)', color: 'var(--color-error)' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteRefAudioFile(false);
                            setTargetDeleteProfile(p);
                          }}
                        >
                          删除
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {uploadStatus && (
        <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
          {uploadStatus}
        </div>
      )}

      {showModal && ReactDOM.createPortal(
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="model-modal-header">
              <span>🗣️ 新建声音配置</span>
              <button
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.1rem' }}
                onClick={() => setShowModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', minHeight: 0 }}>
              {errorMsg && (
                <div style={{ color: 'var(--color-error)', fontSize: '0.8rem', fontWeight: 500, padding: '0 20px', flexShrink: 0 }}>
                  ⚠️ {errorMsg}
                </div>
              )}

              {/* Scrollable Form Body */}
              <div className="model-modal-body">
                <div className="form-group">
                  <label>声音名称 *</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="例如：我的合成声音"
                  />
                </div>

                <div className="form-group">
                  <label>语言类型代号 *</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    placeholder="例如：zh, ja, en"
                  />
                </div>

                <div className="form-group">
                  <label>关联模型 *</label>
                  <select
                    className="input-field"
                    value={modelId || ''}
                    onChange={(e) => setModelId(Number(e.target.value))}
                  >
                    <option value="">-- 请选择目标模型 --</option>
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.provider_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>参考音频转录文本 (可选)</label>
                  <input
                    type="text"
                    className="input-field"
                    value={refText}
                    onChange={(e) => setRefText(e.target.value)}
                    placeholder="输入参考音频中所说的内容文本..."
                  />
                </div>

                <div className="form-group">
                  <label>声音专属参数 JSON (可选)</label>
                  <textarea
                    className="input-field"
                    rows={3}
                    style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', resize: 'vertical' }}
                    value={defaultParamsJson}
                    onChange={(e) => setDefaultParamsJson(e.target.value)}
                    placeholder='{"emotion": "happy", "temperature": 0.8}'
                  />
                </div>
              </div>

              {/* Sticky Footer */}
              <div className="modal-footer">
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
      {/* Voice Profile Delete Confirmation Modal */}
      {targetDeleteProfile && ReactDOM.createPortal(
        <div className="wizard-modal-overlay">
          <div className="wizard-modal-content" style={{ maxWidth: '360px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h4 style={{ margin: 0, fontSize: '0.98rem', color: 'var(--text-primary)' }}>
              {isExampleProfile(targetDeleteProfile) ? '🚨 这是系统示例声音，确定删除吗？' : '⚠️ 确定删除这个声音配置吗？'}
            </h4>
            <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              删除该声音配置将无法还原，但此操作**不会**删除您的历史生成记录和已生成的音频文件。
            </p>

            {targetDeleteProfile.ref_audio_path && (
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', color: 'var(--text-primary)', cursor: 'pointer', userSelect: 'none' }}>
                <input
                  type="checkbox"
                  checked={deleteRefAudioFile}
                  onChange={(e) => setDeleteRefAudioFile(e.target.checked)}
                  style={{ cursor: 'pointer' }}
                />
                同时删除关联的克隆参考音频文件
              </label>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={isDeleting}
                onClick={() => {
                  setTargetDeleteProfile(null);
                  setDeleteRefAudioFile(false);
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
                  try {
                    await onDeleteProfile(targetDeleteProfile.id, deleteRefAudioFile);
                    setTargetDeleteProfile(null);
                    setDeleteRefAudioFile(false);
                  } catch (err) {
                    // Handled in parent toast
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
export default VoiceProfilePanel;
