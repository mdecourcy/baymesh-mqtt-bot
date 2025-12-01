export type SubscriptionType = 'daily_low' | 'daily_avg' | 'daily_high';

export interface Subscription {
  id: number;
  user_id: number;
  username?: string;
  subscription_type: SubscriptionType;
  is_active: boolean;
  created_at: string;
}
