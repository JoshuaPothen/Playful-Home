'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import type { Session, WobbleEvent, ActivitySnapshot } from '@/lib/types';

export type TimeRange = '1h' | '6h' | '24h' | '7d' | 'all';

export interface TrendStats {
  totalSessions: number;
  totalPlayTime: number;
  avgDuration: number;
  longestSession: number;
  byRocker: Record<string, { sessions: number; totalTime: number; avgDuration: number; longest: number }>;
  byScene: Record<number, number>; // scene → total seconds
}

export interface TrendData {
  sessions: Session[];
  snapshots: ActivitySnapshot[];
  events: WobbleEvent[];
  stats: TrendStats;
  isLoading: boolean;
  error: string | null;
  connected: boolean;
}

function rangeToISO(range: TimeRange): string | null {
  if (range === 'all') return null;
  const ms: Record<string, number> = {
    '1h': 3600_000,
    '6h': 21600_000,
    '24h': 86400_000,
    '7d': 604800_000,
  };
  return new Date(Date.now() - ms[range]).toISOString();
}

function computeStats(sessions: Session[], snapshots: ActivitySnapshot[]): TrendStats {
  // Count ALL sessions (active + ended) for totals
  const totalSessions = sessions.length;

  // For time stats, use ended sessions' duration_s, and estimate active sessions from started_at
  let totalPlayTime = 0;
  let longestSession = 0;
  const now = Date.now();
  for (const s of sessions) {
    const dur = s.status === 'ended' && s.duration_s != null
      ? s.duration_s
      : (now - new Date(s.started_at).getTime()) / 1000; // estimate active session duration
    totalPlayTime += dur;
    longestSession = Math.max(longestSession, dur);
  }
  const avgDuration = totalSessions > 0 ? totalPlayTime / totalSessions : 0;

  const byRocker: TrendStats['byRocker'] = {};
  for (const s of sessions) {
    const r = s.rocker;
    if (!byRocker[r]) byRocker[r] = { sessions: 0, totalTime: 0, avgDuration: 0, longest: 0 };
    byRocker[r].sessions++;
    const dur = s.status === 'ended' && s.duration_s != null
      ? s.duration_s
      : (now - new Date(s.started_at).getTime()) / 1000;
    byRocker[r].totalTime += dur;
    byRocker[r].longest = Math.max(byRocker[r].longest, dur);
  }
  for (const r of Object.values(byRocker)) {
    r.avgDuration = r.sessions > 0 ? r.totalTime / r.sessions : 0;
  }

  const byScene: Record<number, number> = {};
  for (let i = 0; i < snapshots.length; i++) {
    const snap = snapshots[i];
    const scene = snap.scene;
    byScene[scene] = (byScene[scene] ?? 0) + 30; // each snapshot ≈ 30s
  }

  return { totalSessions, totalPlayTime, avgDuration, longestSession, byRocker, byScene };
}

export function useTrendData(timeRange: TimeRange): TrendData {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [snapshots, setSnapshots] = useState<ActivitySnapshot[]>([]);
  const [events, setEvents] = useState<WobbleEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const connected = supabase !== null;

  const fetchData = useCallback(async () => {
    if (!supabase) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    const since = rangeToISO(timeRange);

    try {
      const [sessRes, snapRes, evtRes] = await Promise.all([
        since
          ? supabase.from('sessions').select('*').gte('started_at', since).order('started_at', { ascending: true })
          : supabase.from('sessions').select('*').order('started_at', { ascending: true }),
        since
          ? supabase.from('activity_snapshots').select('*').gte('timestamp', since).order('timestamp', { ascending: true })
          : supabase.from('activity_snapshots').select('*').order('timestamp', { ascending: true }).limit(1000),
        since
          ? supabase.from('events').select('*').gte('timestamp', since).order('timestamp', { ascending: false })
          : supabase.from('events').select('*').order('timestamp', { ascending: false }).limit(500),
      ]);

      // Surface any query errors
      const errors = [sessRes.error, snapRes.error, evtRes.error].filter(Boolean);
      if (errors.length > 0) {
        setError(errors.map((e) => e!.message).join('; '));
      }

      setSessions((sessRes.data ?? []) as Session[]);
      setSnapshots((snapRes.data ?? []) as ActivitySnapshot[]);
      setEvents((evtRes.data ?? []) as WobbleEvent[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setIsLoading(false);
  }, [timeRange]);

  useEffect(() => {
    fetchData();
    // Re-fetch every 30s to stay in sync with snapshot interval
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const stats = computeStats(sessions, snapshots);

  return { sessions, snapshots, events, stats, isLoading, error, connected };
}
