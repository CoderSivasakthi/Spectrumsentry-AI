export interface Experiment {
  id: string;
  created_at: string;
  modulation: string;
  snr_db: number;
  sample_count: number;
  sample_rate: number;
  noise_type: string;
  signal_power?: number;
  noise_power?: number;
  predicted_modulation?: string;
  confidence?: number;
  inference_time_ms?: number;
  status: string;
  model_version?: string;
  iq_file_path?: string;
  spectrum_file_path?: string;
  feature_file_path?: string;
}
