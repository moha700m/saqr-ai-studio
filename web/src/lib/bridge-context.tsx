import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { bridge, getToken, setToken, type HardwarePayload, type Health } from './bridge';

type Status = 'checking' | 'online' | 'offline';

interface BridgeState {
  status: Status;
  paired: boolean;
  health: Health | null;
  hardware: HardwarePayload | null;
  error: string | null;
  connect: (code: string) => Promise<void>;
  disconnect: () => Promise<void>;
  refresh: () => Promise<void>;
  loadHardware: () => Promise<void>;
}

const Context = createContext<BridgeState | null>(null);

export function BridgeProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('checking');
  const [paired, setPaired] = useState(Boolean(getToken()));
  const [health, setHealth] = useState<Health | null>(null);
  const [hardware, setHardware] = useState<HardwarePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const payload = await bridge.health();
      setHealth(payload);
      setStatus('online');
      if (getToken()) {
        try {
          await bridge.session();
          setPaired(true);
        } catch {
          setPaired(false);
        }
      } else {
        setPaired(false);
      }
    } catch {
      setStatus('offline');
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 15000);
    return () => clearInterval(timer);
  }, [refresh]);

  const connect = useCallback(async (code: string) => {
    setError(null);
    const result = await bridge.pair(code);
    setToken(result.token);
    setPaired(true);
    await refresh();
  }, [refresh]);

  const disconnect = useCallback(async () => {
    try {
      await bridge.revoke();
    } catch {
      /* already gone */
    }
    setToken(null);
    setPaired(false);
    setHardware(null);
  }, []);

  const loadHardware = useCallback(async () => {
    try {
      setHardware(await bridge.hardware());
    } catch (err) {
      setError((err as Error).message);
      throw err;
    }
  }, []);

  const value = useMemo(
    () => ({ status, paired, health, hardware, error, connect, disconnect, refresh, loadHardware }),
    [status, paired, health, hardware, error, connect, disconnect, refresh, loadHardware],
  );

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useBridge(): BridgeState {
  const value = useContext(Context);
  if (!value) throw new Error('useBridge must be used inside BridgeProvider');
  return value;
}
