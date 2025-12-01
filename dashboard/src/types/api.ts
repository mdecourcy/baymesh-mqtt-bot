import type { Message } from './message';
import type { Subscription, SubscriptionType } from './subscription';

export interface HourlyStat {
  hour: number;
  average_gateways: number;
  max_gateways: number;
  min_gateways: number;
  message_count: number;
  p50_gateways?: number | null;
  p90_gateways?: number | null;
  p95_gateways?: number | null;
  p99_gateways?: number | null;
}

export interface DailyStatsResponse {
  date: string;
  average_gateways: number;
  max_gateways: number;
  min_gateways: number;
  message_count: number;
  start_timestamp?: string | null;
  end_timestamp?: string | null;
  p50_gateways?: number | null;
  p90_gateways?: number | null;
  p95_gateways?: number | null;
  p99_gateways?: number | null;
}

export interface HealthResponse {
  status: 'ok' | 'warning' | 'critical';
  database: string;
  mqtt: string;
  timestamp: string;
  details?: {
    database?: { status: string; latency_ms?: number };
    mqtt?: { server?: string; topic?: string; connected?: boolean; message_count?: number; uptime?: string; reconnects?: number };
    scheduler?: { next_run?: string; last_run?: string; recipients?: number; last_error?: string | null };
  };
}

export interface SubscribePayload {
  userId: number;
  username?: string;
  subscriptionType: SubscriptionType;
}

export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export type MessagesResponse = Message[];
export type SubscriptionsResponse = Subscription[];
