export interface BridgeResponse {
  ok: boolean;
  error?: string;
  ports?: string[];
  default?: string | null;
  registers?: { address: number; value: number }[];
  tx?: string;
  rx?: string;
  result?: {
    old_id: number;
    new_id: number;
    before: { humidity: number; temperature: number };
    after: { humidity: number; temperature: number };
    old_id_still_alive: boolean;
  };
  [key: string]: unknown;
}

export interface BridgeEvent {
  event: 'log' | 'id' | 'reading' | 'error';
  id?: number;
  humidity?: number;
  temperature?: number;
  message?: string;
  level?: string;
  stage?: string;
}

declare global {
  interface Window {
    bridge: {
      send: (cmd: string, payload?: Record<string, unknown>) => Promise<BridgeResponse>;
      onEvent: (callback: (event: BridgeEvent) => void) => () => void;
      showError: (title: string, message: string) => Promise<void>;
    };
  }
}

export function send(cmd: string, payload: Record<string, unknown> = {}): Promise<BridgeResponse> {
  return window.bridge.send(cmd, payload);
}

export interface LogEntry {
  ts: string;
  message: string;
  level: string;
}

export interface Sample {
  t: number;
  humidity: number;
  temperature: number;
}

export type StatusLevel = 'idle' | 'ok' | 'warn' | 'error';

export interface AppState {
  connected: boolean;
  currentId: number | null;
  status: { text: string; level: StatusLevel };
  reading: { humidity: number; temperature: number } | null;
  samples: Sample[];
  logs: LogEntry[];
}
