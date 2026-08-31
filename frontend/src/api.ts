import { 
  ModelConfig, 
  VoiceProfile, 
  Job, 
  GenerateRequest, 
  SpeakRequest, 
  SpeakResponse 
} from './types';

// Detect Tauri and return the active API base URL
export function getApiBase(): string {
  const isTauri = typeof window !== 'undefined' && (
    (window as any).__TAURI__ !== undefined || 
    (window as any).__TAURI_METADATA__ !== undefined ||
    (window as any).__TAURI_INTERNALS__ !== undefined ||
    (window as any).__TAURI_IPC__ !== undefined ||
    window.location.protocol === 'tauri:' ||
    window.location.protocol === 'asset:' ||
    window.location.hostname === 'tauri.localhost'
  );
  if (isTauri) {
    const customPort = localStorage.getItem('desktop_backend_port') || '8765';
    return `http://127.0.0.1:${customPort}`;
  }
  return '';
}

// Resolve any API path or audio path to a full URL if in desktop mode
export function resolveUrl(path: string): string {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  return getApiBase() + path;
}

// Utility helper to handle HTTP responses
async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('text/html')) {
    const htmlText = await response.text();
    const snippet = htmlText.substring(0, 200);
    throw new Error(
      `API Routing Error: Received HTML instead of JSON. The frontend is communicating with the HTML asset server instead of the FastAPI backend. \n` +
      `Request URL: ${response.url}\n` +
      `Base URL detected: ${getApiBase()}\n` +
      `Response Preview: ${snippet}...`
    );
  }

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `HTTP Error ${response.status}`;
    try {
      const parsed = JSON.parse(errorText);
      if (parsed.detail) {
        if (typeof parsed.detail === 'object') {
          errorMessage = JSON.stringify(parsed.detail);
        } else {
          errorMessage = parsed.detail;
        }
      }
    } catch {
      errorMessage = errorText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  const text = await response.text();
  try {
    return JSON.parse(text) as T;
  } catch (err: any) {
    if (text.trim().startsWith('<!doctype') || text.trim().startsWith('<html') || text.trim().startsWith('<!DOCTYPE')) {
      throw new Error(
        `API Routing Error: Received HTML instead of JSON. The frontend is communicating with the HTML asset server instead of the FastAPI backend. \n` +
        `Request URL: ${response.url}\n` +
        `Base URL detected: ${getApiBase()}\n` +
        `Response Preview: ${text.substring(0, 200)}...`
      );
    }
    throw new Error(`JSON Parse Error: ${err.message}. Raw Response: ${text.substring(0, 200)}`);
  }
}

export const api = {
  // --- Providers ---
  async getProviders(): Promise<string[]> {
    const res = await fetch(`${getApiBase()}/api/providers`);
    return handleResponse<string[]>(res);
  },

  // --- Models ---
  async getModels(): Promise<ModelConfig[]> {
    const res = await fetch(`${getApiBase()}/api/models`);
    return handleResponse<ModelConfig[]>(res);
  },

  async createModel(model: Omit<ModelConfig, 'id'>): Promise<ModelConfig> {
    const res = await fetch(`${getApiBase()}/api/models`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(model),
    });
    return handleResponse<ModelConfig>(res);
  },

  async updateModel(id: number, model: Omit<ModelConfig, 'id'>): Promise<ModelConfig> {
    const res = await fetch(`${getApiBase()}/api/models/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(model),
    });
    return handleResponse<ModelConfig>(res);
  },

  // --- Profiles ---
  async getProfiles(): Promise<VoiceProfile[]> {
    const res = await fetch(`${getApiBase()}/api/profiles`);
    return handleResponse<VoiceProfile[]>(res);
  },

  async createProfile(profile: Omit<VoiceProfile, 'id'>): Promise<VoiceProfile> {
    const res = await fetch(`${getApiBase()}/api/profiles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    return handleResponse<VoiceProfile>(res);
  },

  async uploadReferenceAudio(profileId: number, file: File): Promise<VoiceProfile> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${getApiBase()}/api/profiles/${profileId}/upload-reference`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<VoiceProfile>(res);
  },

  // --- Generation ---
  async generateSpeech(req: GenerateRequest): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${getApiBase()}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<{ job_id: string; status: string }>(res);
  },

  async getJobStatus(jobId: string): Promise<Job> {
    const res = await fetch(`${getApiBase()}/api/jobs/${jobId}`);
    return handleResponse<Job>(res);
  },

  async getHistory(): Promise<Job[]> {
    const res = await fetch(`${getApiBase()}/api/history`);
    return handleResponse<Job[]>(res);
  },

  // --- Speak Direct ---
  async speakDirect(req: SpeakRequest): Promise<SpeakResponse> {
    const res = await fetch(`${getApiBase()}/api/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<SpeakResponse>(res);
  },

  // --- Translation Preprocessing ---
  async translateText(text: string, style: string): Promise<{ original_text: string; translated_text: string; target_language: string; style: string }> {
    const res = await fetch(`${getApiBase()}/api/translate/japanese`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, style }),
    });
    return handleResponse<{ original_text: string; translated_text: string; target_language: string; style: string }>(res);
  },

  // --- Deletion APIs ---
  async deleteHistoryItem(jobId: string, deleteAudio: boolean): Promise<{ status: string; message: string }> {
    const res = await fetch(`${getApiBase()}/api/history/${jobId}?delete_audio_files=${deleteAudio}`, {
      method: 'DELETE'
    });
    return handleResponse<{ status: string; message: string }>(res);
  },

  async clearHistory(deleteAudio: boolean): Promise<{ status: string; deleted_records_count: number; deleted_files_count: number; failed_files_count: number; message: string }> {
    const res = await fetch(`${getApiBase()}/api/history?delete_audio_files=${deleteAudio}`, {
      method: 'DELETE'
    });
    return handleResponse<{ status: string; deleted_records_count: number; deleted_files_count: number; failed_files_count: number; message: string }>(res);
  },

  async deleteModel(modelId: number): Promise<{ status: string; message: string }> {
    const res = await fetch(`${getApiBase()}/api/models/${modelId}`, {
      method: 'DELETE'
    });
    return handleResponse<{ status: string; message: string }>(res);
  },

  async deleteProfile(profileId: number, deleteRefAudio: boolean): Promise<{ status: string; message: string }> {
    const res = await fetch(`${getApiBase()}/api/profiles/${profileId}?delete_reference_audio=${deleteRefAudio}`, {
      method: 'DELETE'
    });
    return handleResponse<{ status: string; message: string }>(res);
  }
};
export default api;
