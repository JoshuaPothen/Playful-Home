export interface WobbleState {
  scene: number;
  r1_distance: number;
  r2_distance: number;
  r1_isolated: boolean;
  r2_isolated: boolean;
  r1_accel: [number, number, number];
  r2_accel: [number, number, number];
  tx_accel: [number, number, number];
  r1_gyro: [number, number, number];
  r2_gyro: [number, number, number];
  tx_gyro: [number, number, number];
  hue_bulbs: string[];
  r1_source: 'primary' | 'backup';
  r2_source: 'primary' | 'backup';
  tx_source: 'primary' | 'backup';
  r1_live: boolean;
  r2_live: boolean;
  tx_live: boolean;
  close_threshold: number;
  far_threshold: number;
  // Activity fields
  r1_session_active: boolean;
  r2_session_active: boolean;
  tx_session_active: boolean;
  r1_session_duration: number;
  r2_session_duration: number;
  tx_session_duration: number;
  r1_wobble_ema: number;
  r2_wobble_ema: number;
  tx_wobble_ema: number;
}

export interface TriggerEvent {
  type:
    | 'scene_change'
    | 'r1_isolated'
    | 'r2_isolated'
    | 'r1_returned'
    | 'r2_returned';
}

export interface Session {
  id: string;
  session_id: string;
  rocker: string;
  started_at: string;
  ended_at: string | null;
  duration_s: number | null;
  peak_magnitude: number | null;
  wobble_seconds: number | null;
  status: 'active' | 'ended';
}

export interface WobbleEvent {
  id: number;
  type: string;
  rocker: string | null;
  scene: number | null;
  scene_name: string | null;
  detail: Record<string, unknown> | null;
  timestamp: string;
}

export interface ActivitySnapshot {
  id: number;
  timestamp: string;
  scene: number;
  r1_ema: number;
  r2_ema: number;
  tx_ema: number;
  r1_session_active: boolean;
  r2_session_active: boolean;
  tx_session_active: boolean;
  r1_session_duration_s: number;
  r2_session_duration_s: number;
  tx_session_duration_s: number;
  r1_distance: number;
  r2_distance: number;
  r1_live: boolean;
  r2_live: boolean;
  tx_live: boolean;
}
