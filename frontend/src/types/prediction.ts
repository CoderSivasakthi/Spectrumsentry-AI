export interface PredictionResult {
  id?: number;
  experiment_id?: string;
  true_modulation?: string;
  predicted_modulation: string;
  confidence: number;
  probabilities?: Record<string, number>;
  inference_time_ms: number;
  model_name: string;
  model_version: string;
  timestamp?: string;
}
