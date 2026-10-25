/**
 * Stable per-device identity generated once in localStorage, analogous to a
 * hostname. Sent with the WS handshake (device_id + device_name) and with
 * session start requests so the backend can track one session pair per device.
 */

const DEVICE_ID_KEY = 'sps_device_id';
const DEVICE_NAME_KEY = 'sps_device_name';

let cached: string | null = null;

function localStorageRef(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readStorage(key: string): string | null {
  try {
    return localStorageRef()?.getItem(key) ?? null;
  } catch {
    // Private/blocked storage: fall back to a session-only identity
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    localStorageRef()?.setItem(key, value);
  } catch {
    // Storage unavailable: identity stays for this page load only
  }
}

function randomHex8(): string {
  const g = typeof window === 'undefined' ? globalThis : window;
  const cryptoApi =
    typeof g.crypto !== 'undefined' && 'getRandomValues' in g.crypto ? g.crypto : null;
  if (!cryptoApi) {
    // No WebCrypto (test env): derive from Math.random
    return Math.floor(Math.random() * 0xffffffff)
      .toString(16)
      .padStart(8, '0');
  }
  const bytes = new Uint8Array(4);
  cryptoApi.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function prettyName(id: string): string {
  return `Device-${id.slice(-4)}`;
}

/** Stable device id — generated on first use and persisted. */
export function getDeviceId(): string {
  if (cached) return cached;
  let id = readStorage(DEVICE_ID_KEY);
  if (!id) {
    id = `dev_${randomHex8()}`;
    writeStorage(DEVICE_ID_KEY, id);
  }
  cached = id;
  return id;
}

/** Human-readable device name — editable via the Devices panel. */
export function getDeviceName(): string {
  const cachedName = readStorage(DEVICE_NAME_KEY);
  return cachedName || prettyName(getDeviceId());
}

export function setDeviceName(name: string): void {
  writeStorage(DEVICE_NAME_KEY, name);
}
