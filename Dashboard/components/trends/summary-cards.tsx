'use client';

import { ROCKERS } from '@/lib/constants';

interface SummaryCardsProps {
  stats: {
    totalSessions: number;
    totalPlayTime: number;
    avgDuration: number;
    longestSession: number;
    byRocker: Record<string, { sessions: number; totalTime: number; avgDuration: number; longest: number }>;
  };
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] p-4" style={{ background: 'var(--bg2)' }}>
      <p className="text-[0.55rem] text-zinc-500 tracking-[0.2em] uppercase mb-1">{label}</p>
      <p className="text-xl font-semibold text-zinc-100 font-mono">{value}</p>
      {sub && <p className="text-[0.55rem] text-zinc-600 mt-1">{sub}</p>}
    </div>
  );
}

export function SummaryCards({ stats }: SummaryCardsProps) {
  return (
    <div className="space-y-3">
      {/* Overall stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total Sessions" value={String(stats.totalSessions)} />
        <StatCard label="Total Play Time" value={formatTime(stats.totalPlayTime)} />
        <StatCard label="Avg Duration" value={formatTime(stats.avgDuration)} />
        <StatCard label="Longest Session" value={formatTime(stats.longestSession)} />
      </div>

      {/* Per-rocker breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {(['r1', 'r2', 'tx'] as const).map((key) => {
          const rocker = ROCKERS[key];
          const data = stats.byRocker[key];
          return (
            <div
              key={key}
              className="rounded-lg border p-3"
              style={{ background: 'var(--bg2)', borderColor: rocker.color + '33' }}
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full" style={{ background: rocker.color }} />
                <span className="text-[0.6rem] tracking-[0.2em] uppercase" style={{ color: rocker.color }}>
                  {rocker.label}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-[0.5rem] text-zinc-600">Sessions</p>
                  <p className="font-mono text-zinc-300">{data?.sessions ?? 0}</p>
                </div>
                <div>
                  <p className="text-[0.5rem] text-zinc-600">Total</p>
                  <p className="font-mono text-zinc-300">{formatTime(data?.totalTime ?? 0)}</p>
                </div>
                <div>
                  <p className="text-[0.5rem] text-zinc-600">Avg</p>
                  <p className="font-mono text-zinc-300">{formatTime(data?.avgDuration ?? 0)}</p>
                </div>
                <div>
                  <p className="text-[0.5rem] text-zinc-600">Longest</p>
                  <p className="font-mono text-zinc-300">{formatTime(data?.longest ?? 0)}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
