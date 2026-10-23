/** Ideal reference points of each supported modulation in normalized I/Q space. */
export const REFERENCE_POINTS: Record<string, [number, number][]> = {
  BPSK: [
    [-0.85, 0],
    [0.85, 0],
  ],
  QPSK: [
    [-0.6, -0.6],
    [0.6, -0.6],
    [-0.6, 0.6],
    [0.6, 0.6],
  ],
  '16-QAM': (() => {
    const levels = [-0.75, -0.25, 0.25, 0.75];
    const pts: [number, number][] = [];
    for (const i of levels) for (const q of levels) pts.push([i, q]);
    return pts;
  })(),
};
