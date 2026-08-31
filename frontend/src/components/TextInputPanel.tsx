import React, { useRef, useState } from 'react';

interface TextInputPanelProps {
  text: string;
  onChangeText: (text: string) => void;
  onGenerate: (overrideText?: string) => void;
  onSpeakDirect: (overrideText?: string) => void;
  isLoading: boolean;
  activeProviderType: string;

  // Translation props
  autoTranslate: boolean;
  onChangeAutoTranslate: (val: boolean) => void;
  translatedText: string;
  translationStyle: string;
  onChangeTranslationStyle: (val: string) => void;
  onTranslatePreview: () => Promise<string>;
  onReplaceWithJapanese: () => Promise<void>;
  translationError: string;
}

export const TextInputPanel: React.FC<TextInputPanelProps> = ({
  text,
  onChangeText,
  onGenerate,
  onSpeakDirect,
  isLoading,
  activeProviderType,
  autoTranslate,
  onChangeAutoTranslate,
  translatedText,
  translationStyle,
  onChangeTranslationStyle,
  onTranslatePreview,
  onReplaceWithJapanese,
  translationError,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'common' | 'emotion' | 'style' | 'prosody' | 'sfx'>('common');

  // 日语预设语句
  const greetings = [
    { label: 'おかえりなさい (欢迎回家)', text: 'おかえりなさい、マスター。' },
    { label: 'お疲れさま (辛苦了)', text: '今日もお疲れさまでした。' },
    { label: '無理しないで (请勿勉强)', text: '無理しないでくださいね。' },
    { label: 'えへへ (嘿嘿)', text: 'えへへ、少し嬉しいです。' },
  ];

  // Grouped Higgs inline tags data
  const commonTags = [
    { label: '温柔日常', tag: '<|emotion:affection|><|prosody:expressive_low|>' },
    { label: '元气开心', tag: '<|emotion:enthusiasm|><|prosody:expressive_high|>' },
    { label: '困惑思考', tag: '<|emotion:confusion|><|sfx:humming|>んー…' },
    { label: '害羞低语', tag: '<|emotion:shame|><|style:whispering|>' },
    { label: '悲伤抽泣', tag: '<|emotion:sadness|><|sfx:sniff|>すんっ' },
    { label: '惊讶高音', tag: '<|emotion:surprise|><|prosody:pitch_high|>' },
    { label: '冷静平淡', tag: '<|emotion:contentment|><|prosody:expressive_low|>' },
    { label: '生气喊话', tag: '<|emotion:anger|><|style:shouting|>' },
  ];

  const emotionTags = [
    { label: '得意/狂喜', tag: '<|emotion:elation|>' },
    { label: '好玩/逗乐', tag: '<|emotion:amusement|>' },
    { label: '热情/兴奋', tag: '<|emotion:enthusiasm|>' },
    { label: '坚定/决心', tag: '<|emotion:determination|>' },
    { label: '骄傲/自豪', tag: '<|emotion:pride|>' },
    { label: '满足/舒适', tag: '<|emotion:contentment|>' },
    { label: '温柔/喜爱', tag: '<|emotion:affection|>' },
    { label: '松一口气', tag: '<|emotion:relief|>' },
    { label: '沉思/思考', tag: '<|emotion:contemplation|>' },
    { label: '困惑/疑问', tag: '<|emotion:confusion|>' },
    { label: '惊讶/惊奇', tag: '<|emotion:surprise|>' },
    { label: '敬畏/惊叹', tag: '<|emotion:awe|>' },
    { label: '渴望/期盼', tag: '<|emotion:longing|>' },
    { label: '激动/唤醒', tag: '<|emotion:arousal|>' },
    { label: '生气/愤怒', tag: '<|emotion:anger|>' },
    { label: '害怕/恐惧', tag: '<|emotion:fear|>' },
    { label: '厌恶/排斥', tag: '<|emotion:disgust|>' },
    { label: '痛苦/怨恨', tag: '<|emotion:bitterness|>' },
    { label: '悲伤/忧郁', tag: '<|emotion:sadness|>' },
    { label: '害羞/羞耻', tag: '<|emotion:shame|>' },
    { label: '无奈/无助', tag: '<|emotion:helplessness|>' },
  ];

  const styleTags = [
    { label: '唱歌', tag: '<|style:singing|>' },
    { label: '呐喊', tag: '<|style:shouting|>' },
    { label: '耳语', tag: '<|style:whispering|>' },
  ];

  const prosodyTags = [
    { label: '极慢速', tag: '<|prosody:speed_very_slow|>' },
    { label: '较慢速', tag: '<|prosody:speed_slow|>' },
    { label: '较快速', tag: '<|prosody:speed_fast|>' },
    { label: '极快速', tag: '<|prosody:speed_very_fast|>' },
    { label: '普通停顿', tag: '<|prosody:pause|>' },
    { label: '长停顿', tag: '<|prosody:long_pause|>' },
    { label: '低沉音调', tag: '<|prosody:pitch_low|>' },
    { label: '高亢音调', tag: '<|prosody:pitch_high|>' },
    { label: '高表现力', tag: '<|prosody:expressive_high|>' },
    { label: '低表现力', tag: '<|prosody:expressive_low|>' },
  ];

  const sfxTags = [
    { label: '咳嗽 (こほん)', tag: '<|sfx:cough|>こほん' },
    { label: '笑声 (ふふっ)', tag: '<|sfx:laughter|>ふふっ' },
    { label: '哭泣 (うぅ…)', tag: '<|sfx:crying|>うぅ…' },
    { label: '尖叫 (きゃっ)', tag: '<|sfx:screaming|>きゃっ' },
    { label: '打嗝 (げぷっ)', tag: '<|sfx:burping|>げぷっ' },
    { label: '哼唱 (んー…)', tag: '<|sfx:humming|>んー…' },
    { label: '叹气 (はぁ…)', tag: '<|sfx:sigh|>はぁ…' },
    { label: '吸鼻 (すんっ)', tag: '<|sfx:sniff|>すんっ' },
    { label: '喷嚏 (くしゅ)', tag: '<|sfx:sneeze|>くしゅん' },
  ];

  const isAtBeginning = (tag: string): boolean => {
    // pause, long_pause, and sfx tags should be inserted at current cursor position
    if (tag.includes('prosody:pause') || tag.includes('prosody:long_pause')) {
      return false;
    }
    if (tag.startsWith('<|sfx:')) {
      return false;
    }
    return true;
  };

  const insertTag = (tag: string) => {
    const textarea = textareaRef.current;
    const insertAtStart = isAtBeginning(tag);

    if (insertAtStart) {
      // Insert at the very beginning of the entire text
      onChangeText(tag + text);
      setTimeout(() => {
        if (textarea) {
          textarea.focus();
          textarea.setSelectionRange(tag.length, tag.length);
        }
      }, 0);
      return;
    }

    // Insert at cursor position
    if (!textarea) {
      onChangeText(text + tag);
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const currentText = textarea.value;

    const newText = currentText.substring(0, start) + tag + currentText.substring(end);
    onChangeText(newText);

    // Reposition cursor right after the inserted tag
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + tag.length, start + tag.length);
    }, 0);
  };

  const handlePreviewClick = async () => {
    try {
      await onTranslatePreview();
      setShowPreviewModal(true);
    } catch {
      // Error handled in parent
    }
  };

  return (
    <div className="card" style={{ gap: '16px' }}>
      <div className="card-title">
        <span>📝 文本输入 (TTS Synthesis Text)</span>
        <span style={{ fontSize: '0.74rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
          字数: {text.length}
        </span>
      </div>

      <div className="textarea-wrapper">
        <textarea
          ref={textareaRef}
          className="main-textarea"
          value={text}
          onChange={(e) => onChangeText(e.target.value)}
          placeholder="请输入合成文本... 也可在下方工具条进行日语预处理或插入控制标签。"
          disabled={isLoading}
        />
      </div>

      {/* 日语翻译预处理 (紧凑型工具条) */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '6px',
        marginTop: '-8px',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>🇯🇵 日语预处理</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontSize: '0.68rem', userSelect: 'none', color: 'var(--text-muted)' }}>
            <input
              type="checkbox"
              checked={autoTranslate}
              onChange={(e) => onChangeAutoTranslate(e.target.checked)}
              style={{ width: '12px', height: '12px', cursor: 'pointer' }}
            />
            <span>自动翻译后生成</span>
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <select
            className="input-field"
            value={translationStyle}
            onChange={(e) => onChangeTranslationStyle(e.target.value)}
            disabled={isLoading}
            style={{ padding: '2px 6px', fontSize: '0.68rem', height: '24px', width: '90px', margin: 0 }}
          >
            {['自然口语', '桌宠温柔', '元气少女', '冷淡角色', '正式旁白'].map((style) => (
              <option key={style} value={style}>
                {style}
              </option>
            ))}
          </select>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ padding: '2px 8px', fontSize: '0.68rem', height: '24px' }}
            disabled={isLoading || !text.trim()}
            onClick={handlePreviewClick}
          >
            翻译预览
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ padding: '2px 8px', fontSize: '0.68rem', height: '24px' }}
            disabled={isLoading || !text.trim()}
            onClick={onReplaceWithJapanese}
          >
            替换为日语
          </button>
        </div>
      </div>

      {/* Translation error banner if any */}
      {translationError && (
        <div style={{
          color: '#f87171',
          background: 'oklch(0.60 0.18 25 / 0.08)',
          border: '1px solid oklch(0.60 0.18 25 / 0.15)',
          padding: '8px 10px',
          borderRadius: '6px',
          fontSize: '0.72rem',
          fontFamily: 'var(--font-mono)',
          marginTop: '-4px'
        }}>
          ⚠️ {translationError}
        </div>
      )}

      {/* Greetings section */}
      <div className="shortcut-section">
        <div className="shortcut-label">常用预设语句（日语示范）</div>
        <div className="shortcut-row" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
          {greetings.map((g, i) => (
            <button
              key={i}
              className="template-btn"
              disabled={isLoading}
              onClick={() => onChangeText(g.text)}
            >
              🇯🇵 {g.label}
            </button>
          ))}
        </div>
      </div>

      {/* Emotion/Tag controls — provider-aware */}
      {activeProviderType === 'higgs_api' && (
        <div className="shortcut-section" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          <div className="shortcut-label" style={{ marginBottom: '6px', color: 'var(--color-primary)' }}>✨ Higgs 控制标签选色板 (快捷输入)</div>

          {/* Tab Selector */}
          <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
            {(['common', 'emotion', 'style', 'prosody', 'sfx'] as const).map((tab) => {
              const labels = {
                common: '常用组合',
                emotion: '情绪',
                style: '风格',
                prosody: '停顿/语速/音调',
                sfx: '音效'
              };
              const isActive = activeTab === tab;
              return (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  style={{
                    padding: '3px 8px',
                    fontSize: '0.66rem',
                    fontFamily: 'var(--font-mono)',
                    border: '1px solid ' + (isActive ? 'var(--color-primary)' : 'transparent'),
                    background: isActive ? 'rgba(91, 127, 245, 0.08)' : 'transparent',
                    color: isActive ? 'var(--color-primary)' : 'var(--text-secondary)',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    outline: 'none'
                  }}
                >
                  {labels[tab]}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="shortcut-row" style={{
            gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
            maxHeight: '120px',
            overflowY: 'auto',
            paddingRight: '2px',
            gap: '4px'
          }}>
            {activeTab === 'common' && commonTags.map((t, i) => (
              <button
                key={i}
                type="button"
                className="tag-btn"
                disabled={isLoading}
                onClick={() => insertTag(t.tag)}
                style={{ fontSize: '0.68rem', padding: '5px' }}
              >
                🧩 {t.label}
              </button>
            ))}

            {activeTab === 'emotion' && emotionTags.map((t, i) => (
              <button
                key={i}
                type="button"
                className="tag-btn"
                disabled={isLoading}
                onClick={() => insertTag(t.tag)}
                style={{ fontSize: '0.68rem', padding: '5px' }}
              >
                🎭 {t.label}
              </button>
            ))}

            {activeTab === 'style' && styleTags.map((t, i) => (
              <button
                key={i}
                type="button"
                className="tag-btn"
                disabled={isLoading}
                onClick={() => insertTag(t.tag)}
                style={{ fontSize: '0.68rem', padding: '5px' }}
              >
                🎙️ {t.label}
              </button>
            ))}

            {activeTab === 'prosody' && prosodyTags.map((t, i) => (
              <button
                key={i}
                type="button"
                className="tag-btn"
                disabled={isLoading}
                onClick={() => insertTag(t.tag)}
                style={{ fontSize: '0.68rem', padding: '5px' }}
              >
                ⏱️ {t.label}
              </button>
            ))}

            {activeTab === 'sfx' && sfxTags.map((t, i) => (
              <button
                key={i}
                type="button"
                className="tag-btn"
                disabled={isLoading}
                onClick={() => insertTag(t.tag)}
                style={{ fontSize: '0.68rem', padding: '5px' }}
              >
                🔊 {t.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {activeProviderType === 'piper' && (
        <div style={{
          padding: '8px 12px',
          background: 'rgba(91, 127, 245, 0.05)',
          border: '1px solid rgba(91, 127, 245, 0.12)',
          borderRadius: '6px',
          fontSize: '0.72rem',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
        }}>
          ℹ️ 当前 Piper 模型不支持 Higgs 情绪标签，可通过文本语气和语速调整表达情绪。
        </div>
      )}
      {(activeProviderType === 'local_http' || activeProviderType === 'local_command') && (
        <div style={{
          padding: '8px 12px',
          background: 'rgba(91, 127, 245, 0.05)',
          border: '1px solid rgba(91, 127, 245, 0.12)',
          borderRadius: '6px',
          fontSize: '0.72rem',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
        }}>
          ℹ️ 当前本地模型的情绪控制取决于该模型自身接口配置。
        </div>
      )}

      {/* Buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '4px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
        <button
          className="btn btn-primary"
          style={{
            animation: isLoading ? 'speakPulseRunning 1.5s infinite ease-in-out' : 'none'
          }}
          disabled={isLoading || !text.trim()}
          onClick={() => onGenerate()}
        >
          {isLoading ? '正在入队...' : '🚀 加入队列生成'}
        </button>

        <button
          className="btn btn-secondary"
          style={{
            border: '1px dashed var(--color-accent)',
            color: 'var(--color-accent)',
            animation: isLoading ? 'speakPulseRunning 1.5s infinite ease-in-out' : 'none'
          }}
          disabled={isLoading || !text.trim()}
          onClick={() => onSpeakDirect()}
        >
          🐾 直接试听
        </button>
      </div>

      {/* Preview Modal Portal/Overlay */}
      {showPreviewModal && (
        <div className="wizard-modal-overlay">
          <div className="wizard-modal-content" style={{ maxWidth: '500px', width: '90%', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', background: 'var(--modal-bg)', border: '1px solid var(--border-color)', borderRadius: '12px', boxShadow: '0 20px 40px rgba(0,0,0,0.08)' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>🇯🇵 日语翻译预览</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>原始输入文本</span>
              <div style={{ background: 'var(--bg-input)', padding: '10px', borderRadius: '6px', fontSize: '0.78rem', color: 'var(--text-primary)', border: '1px solid var(--border-color)', maxHeight: '100px', overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                {text}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>翻译后的日语文本 (语气风格: {translationStyle})</span>
              <div style={{ background: 'var(--bg-input)', padding: '10px', borderRadius: '6px', fontSize: '0.78rem', color: 'var(--color-primary)', border: '1px solid var(--border-color)', maxHeight: '100px', overflowY: 'auto', fontWeight: 600, whiteSpace: 'pre-wrap' }}>
                {translatedText}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowPreviewModal(false)}>
                关闭
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => {
                  onChangeText(translatedText);
                  setShowPreviewModal(false);
                }}
              >
                应用并替换原始文本
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default TextInputPanel;
