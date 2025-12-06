export interface Message {
  id: number;
  message_id: string;
  sender_id: number;
  sender_name: string;
  sender_user_id?: number | null;
  gateway_count: number;
  hop_start?: number | null;
  hop_limit?: number | null;
  hops_travelled?: number | null;
  rssi?: number | null;
  snr?: number | null;
  timestamp: string;
}

export interface GatewayInfo {
  gateway_id: string;
  gateway_name?: string | null;
  created_at: string;
}

export interface GatewayHistory {
  gateway_id: string;
  gateway_name?: string | null;
  message_count: number;
  first_seen: string;
  last_seen: string;
}

export interface GatewayPercentiles {
  p50: number;
  p90: number;
  p95: number;
  p99: number;
  sample_size: number;
}

export interface DetailedMessage extends Message {
  payload?: string | null;
  gateways: GatewayInfo[];
}
