export interface ModelConfig {
  id: number;
  name: string;
  provider_type: string;
  api_base?: string;
  model_name?: string;
  command_template?: string;
  model_path?: string;
  output_format: string;
  enabled: boolean;
  params_json: string;
}

export interface VoiceProfile {
  id: number;
  name: string;
  language: string;
  provider_type: string;
  model_id?: number;
  ref_audio_path?: string;
  ref_text?: string;
  default_params_json: string;
}

export interface Job {
  id: string;
  text: string;
  model_id: number;
  profile_id?: number;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  params_json: string;
  return_format: string;
  audio_path?: string;
  audio_url?: string;
  error_message?: string;
  duration?: number;
  created_at: string;
  finished_at?: string;
}

export interface GenerateRequest {
  text: string;
  model_id: number;
  profile_id?: number;
  params: Record<string, any>;
  return_format?: string;
}

export interface SpeakRequest {
  text: string;
  model_id?: number;
  profile_id?: number;
  params: Record<string, any>;
}

export interface SpeakResponse {
  job_id: string;
  status: string;
  audio_url?: string;
  duration?: number;
  error?: string;
}
