import React, { useState, useEffect, useRef } from 'react';
import { ModelConfig, VoiceProfile, Job } from './types';
import { api, getApiBase } from './api';
import { gsap } from 'gsap';
import { useGSAP } from '@gsap/react';

import { ModelConfigPanel } from './components/ModelConfigPanel';
import { VoiceProfilePanel } from './components/VoiceProfilePanel';
import { ProviderPanel } from './components/ProviderPanel';
import { TextInputPanel } from './components/TextInputPanel';
import { ParamsPanel } from './components/ParamsPanel';
import { JobStatusPanel } from './components/JobStatusPanel';
import { AudioPlayerPanel } from './components/AudioPlayerPanel';
import { HistoryPanel } from './components/HistoryPanel';
import { isExampleModel, isExampleProfile } from './utils/helpers';

export const App: React.FC = () => {
  // Global API states
  const [providers, setProviders] = useState<string[]>([]);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [history, setHistory] = useState<Job[]>([]);

  // Selection states (initialize from localStorage)
  const [selectedModelId, setSelectedModelId] = useState<number>(() => {
    const saved = localStorage.getItem('active_model_id');
    return saved ? Number(saved) : 1;
  });
  const [selectedProfileId, setSelectedProfileId] = useState<number | undefined>(() => {
    const saved = localStorage.getItem('active_profile_id');
    return saved ? Number(saved) : undefined;
  });

  // Example filtering switch (default false)
  const [showExamples, setShowExamples] = useState<boolean>(() => {
    return localStorage.getItem('show_examples') === 'true';
  });

  // Input states
  const [text, setText] = useState('お帰りなさい、マスター。');
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(1.0);
  const [temperature, setTemperature] = useState(0.8);
  const [returnFormat, setReturnFormat] = useState('wav');
  const [payloadMode, setPayloadMode] = useState('openai_audio_speech');

  // Job tracker states
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [playingJob, setPlayingJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Translation states
  const [autoTranslate, setAutoTranslate] = useState(false);
  const [translatedText, setTranslatedText] = useState('');
  const [translationStyle, setTranslationStyle] = useState('自然口语');
  const [translationError, setTranslationError] = useState('');

  // Toast notification states
  const [toastText, setToastText] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error' | 'info'>('info');

  const [isBackendReady, setIsBackendReady] = useState(false);
  const [readinessError, setReadinessError] = useState<string | null>(null);

  // Background states
  const [showBgSettings, setShowBgSettings] = useState(false);
  const [bgImageUrl, setBgImageUrl] = useState(() => {
    return localStorage.getItem('custom_bg_url') || '';
  });
  const [bgOpacity, setBgOpacity] = useState(() => {
    const saved = localStorage.getItem('custom_bg_opacity');
    return saved ? Number(saved) : 0.25;
  });

  const [cardOpacity, setCardOpacity] = useState(() => {
    const saved = localStorage.getItem('custom_card_opacity');
    return saved ? Number(saved) : 1.0;
  });

  // Animation scope ref
  const containerRef = useRef<HTMLDivElement>(null);

  // Save selected model & profile on change
  const handleSelectModel = (id: number) => {
    setSelectedModelId(id);
    localStorage.setItem('active_model_id', id.toString());
  };

  const handleSelectProfile = (id: number | undefined) => {
    setSelectedProfileId(id);
    if (id !== undefined) {
      localStorage.setItem('active_profile_id', id.toString());
    } else {
      localStorage.removeItem('active_profile_id');
    }
  };

  // Toggle show examples
  const handleToggleExamples = (val: boolean) => {
    setShowExamples(val);
    localStorage.setItem('show_examples', val.toString());
  };

  // Initialize
  useEffect(() => {
    checkBackendReadiness();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F11') {
        e.preventDefault();
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch((err) => {
            console.error('Failed to enter fullscreen:', err);
          });
        } else {
          document.exitFullscreen().catch((err) => {
            console.error('Failed to exit fullscreen:', err);
          });
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const checkBackendReadiness = async () => {
    const isTauri = typeof window !== 'undefined' && (
      (window as any).__TAURI__ !== undefined ||
      (window as any).__TAURI_METADATA__ !== undefined ||
      (window as any).__TAURI_INTERNALS__ !== undefined ||
      (window as any).__TAURI_IPC__ !== undefined ||
      window.location.protocol === 'tauri:' ||
      window.location.protocol === 'asset:' ||
      window.location.hostname === 'tauri.localhost'
    );

    if (!isTauri) {
      setIsBackendReady(true);
      loadAllData();
      return;
    }

    // Tauri mode: poll /api/health with a timeout
    const start = Date.now();
    const timeout = 15000; // 15 seconds

    const check = async () => {
      try {
        const base = getApiBase();
        const res = await fetch(`${base}/api/health`);
        if (res.ok) {
          setIsBackendReady(true);
          loadAllData();
          return;
        }
      } catch (err) {
        // ignore and retry
      }

      if (Date.now() - start > timeout) {
        setReadinessError("等待后台侧车服务启动超时。请确保后台已运行。");
        return;
      }

      setTimeout(check, 300);
    };

    check();
  };

  const showToast = (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToastText(msg);
    setToastType(type);
    setTimeout(() => setToastText(''), 4000);
  };

  const loadAllData = async (targetModelId?: number, targetProfileId?: number) => {
    try {
      const pList = await api.getProviders();
      setProviders(pList);

      const mList = await api.getModels();
      setModels(mList);

      const profList = await api.getProfiles();
      setProfiles(profList);

      const histList = await api.getHistory();
      setHistory(histList);

      // Now restore or update selectedModelId
      let currentModelId = selectedModelId;
      if (targetModelId !== undefined) {
        currentModelId = targetModelId;
      } else {
        const savedModelId = localStorage.getItem('active_model_id');
        if (savedModelId) {
          const id = Number(savedModelId);
          if (mList.some(m => m.id === id)) {
            currentModelId = id;
          }
        }
      }
      // If currentModelId is not in the list, fallback
      if (!mList.some(m => m.id === currentModelId) && mList.length > 0) {
        // Try to find a non-example enabled model first (excluding dummy)
        const nonExampleEnabled = mList.find(m => m.enabled && !isExampleModel(m) && m.provider_type !== 'dummy');
        // If not found, any non-example model (excluding dummy)
        const nonExample = mList.find(m => !isExampleModel(m) && m.provider_type !== 'dummy');
        // If not found, any enabled non-dummy model
        const enabledNonDummy = mList.find(m => m.enabled && m.provider_type !== 'dummy');
        // If not found, any non-dummy model
        const nonDummy = mList.find(m => m.provider_type !== 'dummy');
        // Fallback to any enabled model
        const enabledAny = mList.find(m => m.enabled);

        const fallback = nonExampleEnabled || nonExample || enabledNonDummy || nonDummy || enabledAny || mList[0];
        currentModelId = fallback.id;
      }
      setSelectedModelId(currentModelId);
      localStorage.setItem('active_model_id', currentModelId.toString());

      // Now restore or update selectedProfileId
      let currentProfileId = selectedProfileId;
      if (targetProfileId !== undefined) {
        currentProfileId = targetProfileId;
      } else {
        const savedProfileId = localStorage.getItem('active_profile_id');
        if (savedProfileId) {
          const id = Number(savedProfileId);
          if (profList.some(p => p.id === id)) {
            currentProfileId = id;
          }
        }
      }
      // If currentProfileId is not in the list, fallback
      if (currentProfileId !== undefined && !profList.some(p => p.id === currentProfileId)) {
        // Try to find a profile that is not System Beep (provider_type !== 'dummy')
        const nonDummyProfile = profList.find(p => p.provider_type !== 'dummy');
        // Fallback to any profile
        const fallbackProfile = nonDummyProfile || profList[0];

        currentProfileId = fallbackProfile ? fallbackProfile.id : undefined;
      }
      setSelectedProfileId(currentProfileId);
      if (currentProfileId !== undefined) {
        localStorage.setItem('active_profile_id', currentProfileId.toString());
      } else {
        localStorage.removeItem('active_profile_id');
      }
    } catch (err: any) {
      showToast(`加载数据失败: ${err.message}`, 'error');
    }
  };

  const handleDeleteModel = async (modelId: number): Promise<void> => {
    try {
      await api.deleteModel(modelId);
      showToast('模型配置已删除', 'success');
      // If the model was active, remove and fallback
      if (selectedModelId === modelId) {
        localStorage.removeItem('active_model_id');
      }
      await loadAllData(undefined, selectedProfileId);
    } catch (err: any) {
      let displayMsg = err.message;
      try {
        const parsed = JSON.parse(err.message);
        if (parsed.code === 'BLOCKED_BY_PROFILES') {
          const listStr = parsed.profiles.map((p: any) => `${p.name} (ID: ${p.id})`).join('、');
          displayMsg = `${parsed.message}${listStr}`;
        }
      } catch (e) {}
      showToast(displayMsg, 'error');
      throw err;
    }
  };

  const handleDeleteProfile = async (profileId: number, deleteRefAudio: boolean): Promise<void> => {
    try {
      const res = await api.deleteProfile(profileId, deleteRefAudio);
      if (isSelectedProfileDeleted(profileId)) {
        localStorage.removeItem('active_profile_id');
      }
      if (res.status === 'partial_success') {
        showToast(res.message, 'info');
      } else {
        showToast('声音配置已删除', 'success');
      }
      await loadAllData(selectedModelId, undefined);
    } catch (err: any) {
      showToast(`删除声音配置失败: ${err.message}`, 'error');
      throw err;
    }
  };

  const isSelectedProfileDeleted = (profileId: number) => {
    return selectedProfileId === profileId;
  };

  const handleDeleteJob = async (jobId: string, deleteAudio: boolean): Promise<void> => {
    try {
      const res = await api.deleteHistoryItem(jobId, deleteAudio);
      if (res.status === 'partial_success') {
        showToast(res.message, 'info');
      } else {
        showToast('历史记录已删除', 'success');
      }

      // Clear player state if currently playing
      if (playingJob && playingJob.id === jobId) {
        setPlayingJob(null);
      }
      if (activeJob && activeJob.id === jobId) {
        setActiveJob(null);
      }

      // Reload history
      const hist = await api.getHistory();
      setHistory(hist);
    } catch (err: any) {
      showToast(`删除历史记录失败: ${err.message}`, 'error');
    }
  };

  const handleClearHistory = async (deleteAudio: boolean): Promise<void> => {
    try {
      const res = await api.clearHistory(deleteAudio);
      if (res.status === 'partial_success') {
        showToast(res.message, 'info');
      } else {
        showToast('历史记录已清空', 'success');
      }

      // Clear player state
      setPlayingJob(null);
      setActiveJob(null);

      // Reload history
      const hist = await api.getHistory();
      setHistory(hist);
    } catch (err: any) {
      showToast(`清空历史记录失败: ${err.message}`, 'error');
    }
  };

  const handleTranslatePreview = async (): Promise<string> => {
    if (!text.trim()) {
      showToast('原始文本不能为空', 'error');
      throw new Error('原始文本不能为空');
    }
    setIsLoading(true);
    setTranslationError('');
    try {
      const res = await api.translateText(text, translationStyle);
      setTranslatedText(res.translated_text);
      showToast('翻译预览成功！', 'success');
      return res.translated_text;
    } catch (err: any) {
      setTranslationError(err.message);
      showToast(`翻译失败: ${err.message}`, 'error');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const handleReplaceWithJapanese = async () => {
    try {
      const translated = await handleTranslatePreview();
      setText(translated);
      showToast('已成功替换原始文本为日语！', 'success');
    } catch (err) {
      // Handled in preview function
    }
  };

  // Job Polling Loop
  const pollJobStatus = (jobId: string) => {
    const timer = setInterval(async () => {
      try {
        const job = await api.getJobStatus(jobId);
        setActiveJob(job);

        if (job.status === 'succeeded') {
          clearInterval(timer);
          setIsLoading(false);
          setPlayingJob(job);
          showToast('音频合成成功！', 'success');
          // Refresh lists
          const hist = await api.getHistory();
          setHistory(hist);
        } else if (job.status === 'failed') {
          clearInterval(timer);
          setIsLoading(false);
          showToast(`任务失败: ${job.error_message}`, 'error');
          // Refresh lists
          const hist = await api.getHistory();
          setHistory(hist);
        }
      } catch (err: any) {
        clearInterval(timer);
        setIsLoading(false);
        showToast(`轮询任务状态失败: ${err.message}`, 'error');
      }
    }, 1000);
  };

  // Generate Queue handler
  const handleGenerate = async (overrideText?: string) => {
    setIsLoading(true);
    setActiveJob(null);
    setPlayingJob(null);
    setTranslationError('');

    const params: Record<string, any> = {
      speed,
      pitch,
      temperature,
    };

    // If local_http is active, append the payload_mode
    const selectedModel = models.find((m) => m.id === selectedModelId);
    if (selectedModel?.provider_type === 'local_http') {
      params['payload_mode'] = payloadMode;
    }

    let textToSynthesize = overrideText || text;

    if (!overrideText && autoTranslate) {
      showToast('正在进行日语翻译预处理...', 'info');
      try {
        const res = await api.translateText(text, translationStyle);
        setTranslatedText(res.translated_text);
        textToSynthesize = res.translated_text;
        showToast('翻译完成，开始生成语音...', 'success');
      } catch (err: any) {
        setIsLoading(false);
        setTranslationError(err.message);
        showToast(`翻译失败: ${err.message}`, 'error');
        return;
      }
    }

    try {
      const req = {
        text: textToSynthesize,
        model_id: selectedModelId,
        profile_id: selectedProfileId,
        params,
        return_format: returnFormat,
      };

      const res = await api.generateSpeech(req);
      showToast(`已加入合成队列！任务 ID: ${res.job_id}`, 'success');

      // Create a local dummy job to represent queued state in UI before polling returns first response
      const initialJobState: Job = {
        id: res.job_id,
        text: textToSynthesize,
        model_id: selectedModelId,
        profile_id: selectedProfileId,
        status: 'queued',
        params_json: JSON.stringify(params),
        return_format: returnFormat,
        created_at: new Date().toISOString(),
      };
      setActiveJob(initialJobState);

      // Start polling
      pollJobStatus(res.job_id);
    } catch (err: any) {
      setIsLoading(false);
      showToast(`加入队列失败: ${err.message}`, 'error');
    }
  };

  // Speak direct handler (pet integration test)
  const handleSpeakDirect = async (overrideText?: string) => {
    setIsLoading(true);
    setActiveJob(null);
    setPlayingJob(null);
    setTranslationError('');

    const params: Record<string, any> = {
      speed,
      pitch,
      temperature,
    };

    const selectedModel = models.find((m) => m.id === selectedModelId);
    if (selectedModel?.provider_type === 'local_http') {
      params['payload_mode'] = payloadMode;
    }

    let textToSynthesize = overrideText || text;

    if (!overrideText && autoTranslate) {
      showToast('正在进行日语翻译预处理...', 'info');
      try {
        const res = await api.translateText(text, translationStyle);
        setTranslatedText(res.translated_text);
        textToSynthesize = res.translated_text;
        showToast('翻译完成，开始即时合成...', 'success');
      } catch (err: any) {
        setIsLoading(false);
        setTranslationError(err.message);
        showToast(`翻译失败: ${err.message}`, 'error');
        return;
      }
    }

    showToast('直接试听：正在即时合成音频...', 'info');

    try {
      const req = {
        text: textToSynthesize,
        model_id: selectedModelId,
        profile_id: selectedProfileId,
        params,
      };

      const res = await api.speakDirect(req);

      if (res.status === 'succeeded' && res.audio_url) {
        showToast('直接试听合成完成！', 'success');

        // Refresh lists
        const hist = await api.getHistory();
        setHistory(hist);

        // Setup direct job to play audio
        const finishedJob = hist.find(h => h.id === res.job_id) || {
          id: res.job_id,
          text: textToSynthesize,
          model_id: selectedModelId,
          profile_id: selectedProfileId,
          status: 'succeeded' as const,
          params_json: JSON.stringify(params),
          return_format: returnFormat,
          audio_url: res.audio_url,
          duration: res.duration,
          created_at: new Date().toISOString(),
        };
        setPlayingJob(finishedJob);
      } else {
        showToast(`直接试听失败: ${res.error}`, 'error');
        const hist = await api.getHistory();
        setHistory(hist);
        const failedJob = hist.find(h => h.id === res.job_id);
        if (failedJob) {
          setActiveJob(failedJob);
        }
      }
    } catch (err: any) {
      showToast(`直接试听失败: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Re-use options
  const handleReuseParams = (paramsJson: string, format: string) => {
    try {
      const parsed = JSON.parse(paramsJson);
      if (parsed.speed !== undefined) setSpeed(parsed.speed);
      if (parsed.pitch !== undefined) setPitch(parsed.pitch);
      if (parsed.temperature !== undefined) setTemperature(parsed.temperature);
      if (parsed.payload_mode !== undefined) setPayloadMode(parsed.payload_mode);
      setReturnFormat(format);
      showToast('已复用历史声音合成参数。', 'success');
    } catch {
      showToast('无法复用参数：无效的 JSON。', 'error');
    }
  };

  // Tasteful GSAP Animation for Workspace Loading
  useGSAP(() => {
    if (isBackendReady) {
      gsap.from('.left-sidebar-scroll > *', {
        x: -15,
        opacity: 0,
        duration: 0.45,
        stagger: 0.08,
        ease: 'power2.out',
        clearProps: 'all'
      });

      gsap.from('.center-workspace-scroll > *', {
        y: 12,
        opacity: 0,
        duration: 0.45,
        stagger: 0.08,
        ease: 'power2.out',
        clearProps: 'all'
      });

      gsap.from('.workbench-grid > *:last-child > *', {
        x: 15,
        opacity: 0,
        duration: 0.45,
        stagger: 0.08,
        ease: 'power2.out',
        clearProps: 'all'
      });
    }
  }, { scope: containerRef, dependencies: [isBackendReady] });

  const selectedModel = models.find((m) => m.id === selectedModelId);
  const showPayloadMode = selectedModel?.provider_type === 'local_http';

  if (!isBackendReady) {
    return (
      <div className="app-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100dvh', flexDirection: 'column', gap: '20px', background: 'var(--bg-main)' }}>
        <div className="card" style={{ padding: '40px', maxWidth: '500px', width: '90%', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center' }}>
          <h1 style={{ fontSize: '1.35rem', marginBottom: '5px', color: 'var(--text-primary)', fontFamily: 'var(--font-title)' }}>🎙️ TTS WebUI 工作台</h1>
          {readinessError ? (
            <>
              <div style={{ color: 'var(--color-error)', fontSize: '2rem' }}>⚠️</div>
              <p style={{ color: 'var(--text-primary)', fontSize: '0.86rem', lineHeight: '1.5' }}>{readinessError}</p>
              <button className="btn btn-primary" onClick={() => { setReadinessError(null); checkBackendReadiness(); }}>
                重新尝试连接
              </button>
            </>
          ) : (
            <>
              <div className="spinner" style={{ border: '3px solid rgba(0,0,0,0.06)', borderLeftColor: 'var(--border-focus)', borderRadius: '50%', width: '36px', height: '36px', animation: 'spin 1s linear infinite' }} />
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', fontFamily: 'var(--font-mono)' }}>工作台服务启动中...</p>
            </>
          )}
        </div>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="app-container" ref={containerRef} style={{ '--card-opacity': cardOpacity } as React.CSSProperties}>
      {/* Header */}
      <div className="header">
        <h1>🎙️ TTS 音频工作台</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            className="btn btn-secondary btn-sm"
            style={{ padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px', textTransform: 'none' }}
            onClick={() => setShowBgSettings(true)}
          >
            🖼️ 背景设置
          </button>
          <div className="header-status">
            <div className="status-dot" />
            <span>系统就绪</span>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="workbench-grid">
        {/* Left Column: Configurations Navigation */}
        <div className="left-sidebar-scroll">
          {/* 显示示例配置切换开关 */}
          <div className="card" style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexDirection: 'row', flexShrink: 0 }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>显示示例配置</span>
            <label style={{ margin: 0, display: 'inline-flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={showExamples}
                onChange={(e) => handleToggleExamples(e.target.checked)}
                style={{ display: 'none' }}
              />
              <span style={{
                width: '32px',
                height: '16px',
                borderRadius: '8px',
                background: showExamples ? 'var(--color-primary)' : 'rgba(0, 0, 0, 0.12)',
                display: 'inline-block',
                position: 'relative',
                transition: 'var(--transition-smooth)'
              }}>
                <span style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#fff',
                  display: 'block',
                  position: 'absolute',
                  top: '2px',
                  left: showExamples ? '18px' : '2px',
                  transition: 'var(--transition-smooth)'
                }} />
              </span>
            </label>
          </div>

          <ModelConfigPanel
            models={models}
            selectedModelId={selectedModelId}
            onSelectModel={handleSelectModel}
            onRefreshModels={(newModelId) => loadAllData(newModelId, selectedProfileId)}
            providers={providers}
            showExamples={showExamples}
            onDeleteModel={handleDeleteModel}
          />
          <VoiceProfilePanel
            profiles={profiles}
            models={models}
            selectedModelId={selectedModelId}
            selectedProfileId={selectedProfileId}
            onSelectProfile={handleSelectProfile}
            onRefreshProfiles={(newProfileId) => loadAllData(selectedModelId, newProfileId)}
            showExamples={showExamples}
            onDeleteProfile={handleDeleteProfile}
          />
          <ProviderPanel providers={providers} />
        </div>

        {/* Middle Column: Text synthesis workspace */}
        <div className="center-workspace-scroll">
          <TextInputPanel
            text={text}
            onChangeText={setText}
            onGenerate={handleGenerate}
            onSpeakDirect={handleSpeakDirect}
            isLoading={isLoading}
            activeProviderType={selectedModel?.provider_type || ''}
            autoTranslate={autoTranslate}
            onChangeAutoTranslate={setAutoTranslate}
            translatedText={translatedText}
            translationStyle={translationStyle}
            onChangeTranslationStyle={setTranslationStyle}
            onTranslatePreview={handleTranslatePreview}
            onReplaceWithJapanese={handleReplaceWithJapanese}
            translationError={translationError}
          />

          <ParamsPanel
            speed={speed}
            onChangeSpeed={setSpeed}
            pitch={pitch}
            onChangePitch={setPitch}
            temperature={temperature}
            onChangeTemperature={setTemperature}
            returnFormat={returnFormat}
            onChangeReturnFormat={setReturnFormat}
            payloadMode={payloadMode}
            onChangePayloadMode={setPayloadMode}
            showPayloadMode={showPayloadMode}
          />
        </div>

        {/* Right Column: Output Inspector & History */}
        <div className="right-sidebar">
          <JobStatusPanel
            job={activeJob}
            onClear={() => setActiveJob(null)}
          />

          <AudioPlayerPanel
            job={playingJob}
          />

          <HistoryPanel
            history={history}
            activeJobId={playingJob?.id || null}
            onSelectJob={(job) => {
              setActiveJob(job);
              if (job.status === 'succeeded') {
                setPlayingJob(job);
              } else {
                setPlayingJob(null);
              }
            }}
            onReuseText={setText}
            onReuseParams={handleReuseParams}
            onDeleteJob={handleDeleteJob}
            onClearHistory={handleClearHistory}
          />
        </div>
      </div>

      {/* Toast notifications */}
      {toastText && (
        <div className={`toast-msg toast-${toastType}`}>
          <span>{toastType === 'success' ? '✓' : toastType === 'error' ? '⚠️' : 'ℹ️'}</span>
          <span>{toastText}</span>
        </div>
      )}

      {/* Background Image Layer */}
      {bgImageUrl && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundImage: `url(${bgImageUrl})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            opacity: bgOpacity,
            pointerEvents: 'none',
            zIndex: -1,
            transition: 'opacity 0.2s ease'
          }}
        />
      )}

      {/* Background Settings Modal */}
      {showBgSettings && (
        <div className="wizard-modal-overlay">
          <div className="wizard-modal-content" style={{ maxWidth: '420px', width: '90%', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>🖼️ 自定义背景设置</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>图片 URL (支持网络链接)</label>
              <input
                type="text"
                className="input-field"
                value={bgImageUrl}
                onChange={(e) => setBgImageUrl(e.target.value)}
                placeholder="https://images.unsplash.com/... 或粘贴图片链接"
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>📤 上传本地图片作为背景</label>
              <input
                type="file"
                accept="image/*"
                className="input-field"
                style={{ padding: '6px 10px', fontSize: '0.76rem', cursor: 'pointer' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const reader = new FileReader();
                  reader.onload = (event) => {
                    const base64String = event.target?.result as string;
                    setBgImageUrl(base64String);
                  };
                  reader.readAsDataURL(file);
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)' }}>
                <span>背景不透明度 (Opacity)</span>
                <span>{Math.round(bgOpacity * 100)}%</span>
              </label>
              <input
                type="range"
                min="0.05"
                max="1.0"
                step="0.05"
                className="slider-input"
                value={bgOpacity}
                onChange={(e) => setBgOpacity(Number(e.target.value))}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)' }}>
                <span>功能区框不透明度 (Card Opacity)</span>
                <span>{Math.round(cardOpacity * 100)}%</span>
              </label>
              <input
                type="range"
                min="0.2"
                max="1.0"
                step="0.05"
                className="slider-input"
                value={cardOpacity}
                onChange={(e) => setCardOpacity(Number(e.target.value))}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>二次元精选推荐预设</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ textTransform: 'none', padding: '6px' }}
                  onClick={() => setBgImageUrl('https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=1000')}
                >
                  🎐 梦幻动漫插画
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ textTransform: 'none', padding: '6px' }}
                  onClick={() => setBgImageUrl('https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?q=80&w=1000')}
                >
                  🌸 樱花日系古风
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ textTransform: 'none', padding: '6px' }}
                  onClick={() => setBgImageUrl('https://images.unsplash.com/photo-1541562232579-512a21360020?q=80&w=1000')}
                >
                  🌌 星空动漫原画
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ textTransform: 'none', padding: '6px', color: 'var(--color-error)' }}
                  onClick={() => setBgImageUrl('')}
                >
                  ❌ 重置默认网点
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button
                className="btn btn-primary"
                onClick={() => {
                  localStorage.setItem('custom_bg_url', bgImageUrl);
                  localStorage.setItem('custom_bg_opacity', String(bgOpacity));
                  localStorage.setItem('custom_card_opacity', String(cardOpacity));
                  setShowBgSettings(false);
                }}
              >
                保存配置并关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
