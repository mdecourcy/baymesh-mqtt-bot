export interface Message {
  id: number;
  message_id: string;
  sender_id: number;
  sender_name: string;
  sender_user_id?: number | null;
  gateway_count: number;
  rssi?: number | null;
  snr?: number | null;
  timestamp: string;
}

export interface GatewayInfo {
  gateway_id: string;
  gateway_name?: string | null;
  created_at: string;
}

export interface DetailedMessage extends Message {
  payload?: string | null;
  gateways: GatewayInfo[];
}
