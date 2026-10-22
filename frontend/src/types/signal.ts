export type ModulationType = 'BPSK' | 'QPSK' | '16-QAM';

export interface SignalParameters {
  modulation: ModulationType;
  snr_db: number;
  num_samples: number;
  sample_rate: number;
  carrier_frequency?: number;
}

export interface SignalProcessingData {
  modulation: ModulationType;
  snr_db: number;
  num_samples: number;
  sample_rate: number;
  signal_power: number;
  noise_power: number;
  i_samples: number[];
  q_samples: number[];
  fft_magnitude_db: number[];
  fft_frequencies: number[];
}
