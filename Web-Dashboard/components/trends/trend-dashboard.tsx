'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTrendData, type TimeRange } from '@/hooks/use-trend-data';
import { SummaryCards } from './summary-cards';
import { ActivityChart } from './activity-chart';
import { SessionChart } from './session-chart';
import { SceneDistribution } from './scene-distribution';
import { EventTimeline } from './event-timeline';

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '1h', label: '1H' },
  { value: '6h', label: '6H' },
  { value: '24h', label: '24H' },
  { value: '7d', label: '7D' },
  { value: 'all', label: 'ALL' },
];

export function TrendDashboard() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const { sessions, snapshots, events, stats, isLoading, error, connected } = useTrendData(timeRange);

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)' }}>
      {/* Header */}
      <header className="sticky top-0 z-40 flex flex-wrap items-center justify-between gap-2 px-4 sm:px-6 py-2 sm:h-16 border-b border-[var(--border)]" style={{ background: 'var(--bg)' }}>
        <div className="flex items-center gap-4">
          <Link href="/" className="font-semibold tracking-[0.42em] text-sm sm:text-[18px] text-zinc-100 hover:text-white transition-colors">
            PLAYFUL HOME
          </Link>
          <span className="text-zinc-600">/</span>
          <span className="text-sm sm:text-[18px] text-zinc-400 tracking-[0.3em] uppercase">TRENDS</span>
        </div>

        {/* Time range selector */}
        <div className="flex items-center gap-1 bg-zinc-900 rounded-md p-0.5">
          {TIME_RANGES.map((r) => (
            <button
              key={r.value}
              onClick={() => setTimeRange(r.value)}
              className="px-3 py-1 text-[0.6rem] tracking-wider font-mono rounded transition-all"
              style={
                timeRange === r.value
                  ? { background: '#7855d8', color: 'white' }
                  : { color: '#71717a' }
              }
            >
              {r.label}
            </button>
          ))}
        </div>
      </header>

      {/* Content */}
      <div className="p-4 space-y-4 max-w-7xl mx-auto">
        {/* Connection / error banners */}
        {!connected && (
          <div className="rounded-lg border border-amber-900/50 bg-amber-950/30 p-4 text-sm text-amber-300">
            <p className="font-semibold mb-1">Supabase not configured</p>
            <p className="text-amber-400/70 text-xs font-mono">
              Create <code>wobble_dashboard/.env.local</code> with:
            </p>
            <pre className="text-[0.6rem] text-amber-400/50 mt-2 leading-relaxed">
{`NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...`}
            </pre>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-3 text-xs text-red-400 font-mono">
            Query error: {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-zinc-600 text-xs tracking-[0.3em] uppercase animate-pulse">
              LOADING TREND DATA
            </p>
          </div>
        ) : (
          <>
            <SummaryCards stats={stats} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ActivityChart snapshots={snapshots} />
              <SessionChart sessions={sessions} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <SceneDistribution stats={stats} />
              <EventTimeline events={events} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
