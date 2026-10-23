import { useCallback, useEffect, useRef, useState } from 'react';
import { sendTestPacket } from '../api/monitoring';

/** A named network condition the transmitter reproduces. */
export interface LinkProfile {
  key: string;
  label: string;
  detail: string;
  /** Base delay between packets (ms). */
  intervalMs: number;
  /** Probability a sequence number is dropped before transmission. */
  lossProb: number;
  /** Simulated radio stall: every N packets the channel goes silent. */
  pauseEvery?: number;
  /** Duration of simulated radio stall (ms). */
  pauseMs?: number;
}

export const LINK_PROFILES: LinkProfile[] = [
  { key: 'clean', label: 'Clean steady', detail: 'No loss · stable RTT', intervalMs: 220, lossProb: 0 },
  { key: 'lossy', label: 'Lossy channel', detail: '~10% sequence loss', intervalMs: 220, lossProb: 0.1 },
  { key: 'bursty', label: 'Radio pauses', detail: 'Silence stalls every ~13 s', intervalMs: 200, lossProb: 0, pauseEvery: 60, pauseMs: 6000 },
];

export interface LinkStreamStats {
  sent: number;
  acked: number;
  failed: number;
  lastRttMs: number | null;
}

export interface LinkTestStream {
  running: boolean;
  profileKey: string;
  stats: LinkStreamStats;
  setProfile: (key: string) => void;
  start: (sessionId: string) => void;
  stop: (opts?: { silent?: boolean }) => void;
}

/**
 * Client-side link-test transmitter: streams numbered test packets to the
 * backend's packet ingest endpoint, carrying each packet's measured HTTP RTT
 * so real latency/jitter/loss statistics accumulate in the decision engine.
 */
export const useLinkTestStream = (): LinkTestStream => {
  const [running, setRunning] = useState(false);
  const [profileKey, setProfileKey] = useState<string>(LINK_PROFILES[0].key);
  const [stats, setStats] = useState<LinkStreamStats>({ sent: 0, acked: 0, failed: 0, lastRttMs: null });

  const runningRef = useRef(false);
  const seqRef = useRef(0);
  const lastRttRef = useRef<number | null>(null);
  const pausedUntilRef = useRef(0);
  const profileRef = useRef<LinkProfile>(LINK_PROFILES[0]);
  const sessionIdRef = useRef<string | null>(null);

  const setProfile = useCallback((key: string) => {
    setProfileKey(key);
    const next = LINK_PROFILES.find((p) => p.key === key);
    if (next) profileRef.current = next;
  }, []);

  const stop = useCallback((opts?: { silent?: boolean }) => {
    runningRef.current = false;
    setRunning(false);
    sessionIdRef.current = null;
    if (!opts?.silent) {
      // Reset counters so the next run starts clean
      setStats({ sent: 0, acked: 0, failed: 0, lastRttMs: null });
      seqRef.current = 0;
      lastRttRef.current = null;
    }
  }, []);

  const start = useCallback((sessionId: string) => {
    if (runningRef.current) return;
    sessionIdRef.current = sessionId;
    runningRef.current = true;
    setRunning(true);

    const tick = async () => {
      if (!runningRef.current) return;
      const profile = profileRef.current;
      const sessionId = sessionIdRef.current;
      if (!sessionId) {
        runningRef.current = false;
        setRunning(false);
        return;
      }

      // Simulated radio stall: skip sending entirely for pauseMs
      if (
        profile.pauseEvery &&
        seqRef.current > 0 &&
        seqRef.current % profile.pauseEvery === 0 &&
        Date.now() >= pausedUntilRef.current
      ) {
        pausedUntilRef.current = Date.now() + (profile.pauseMs ?? 5000);
        // Consume the boundary sequence so the gate cannot re-fire when the pause ends
        seqRef.current += 1;
      }

      if (Date.now() < pausedUntilRef.current) {
        setTimeout(tick, Math.min(250, profile.pauseMs ? (pausedUntilRef.current - Date.now()) : 250));
        return;
      }

      // Loss simulation: advance the sequence without sending it
      let sequence = ++seqRef.current;
      if (profile.lossProb > 0 && Math.random() < profile.lossProb) {
        sequence = ++seqRef.current; // next arriving packet reveals the gap as loss
      }

      const t0 = performance.now();
      try {
        await sendTestPacket({
          session_id: sessionId,
          sequence_number: sequence,
          sender_timestamp: Date.now(),
          payload_size: 512 + Math.floor(Math.random() * 256),
          client_rtt_ms: lastRttRef.current ?? undefined,
        });
        const rtt = performance.now() - t0;
        lastRttRef.current = rtt;
        setStats((s) => ({ ...s, sent: s.sent + 1, acked: s.acked + 1, lastRttMs: rtt }));
      } catch {
        setStats((s) => ({ ...s, sent: s.sent + 1, failed: s.failed + 1 }));
      }

      if (runningRef.current) {
        setTimeout(tick, profile.intervalMs);
      }
    };

    void tick();
  }, []);

  // Stop the stream when the component tree unmounts
  useEffect(() => () => { runningRef.current = false; }, []);

  return { running, profileKey, stats, setProfile, start, stop };
};
