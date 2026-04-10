'use client';

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ROCKERS } from '@/lib/constants';
import type { Session } from '@/lib/types';

interface SessionChartProps {
  sessions: Session[];
}

const ROCKER_COLORS: Record<string, string> = {
  r1: ROCKERS.r1.color,
  r2: ROCKERS.r2.color,
  tx: ROCKERS.tx.color,
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function SessionChart({ sessions }: SessionChartProps) {
  const now = Date.now();
  const data = sessions.map((s) => {
    const dur = s.status === 'ended' && s.duration_s != null
      ? s.duration_s
      : (now - new Date(s.started_at).getTime()) / 1000;
    return {
      label: formatTime(s.started_at),
      duration: Math.round(dur),
      rocker: s.rocker,
      color: ROCKER_COLORS[s.rocker] ?? '#71717a',
    };
  });

  return (
    <div className="rounded-lg border border-[var(--border)] p-4" style={{ background: 'var(--bg2)' }}>
      <p className="text-[0.6rem] text-zinc-500 tracking-[0.2em] uppercase mb-3">
        Session Durations
      </p>
      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center">
          <p className="text-zinc-700 text-xs">No sessions yet</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data}>
            <XAxis
              dataKey="label"
              tick={{ fontSize: 9, fill: '#52525b' }}
              axisLine={{ stroke: '#27272a' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 9, fill: '#52525b' }}
              axisLine={{ stroke: '#27272a' }}
              tickLine={false}
              width={35}
              label={{ value: 'sec', angle: -90, position: 'insideLeft', style: { fontSize: 9, fill: '#52525b' } }}
            />
            <Tooltip
              contentStyle={{
                background: '#09091680',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 8,
                fontSize: 11,
                backdropFilter: 'blur(8px)',
              }}
              labelStyle={{ color: '#a1a1aa' }}
              itemStyle={{ color: '#e4e4e7' }}
              formatter={(value) => [`${value}s`, 'Duration']}
            />
            <Bar dataKey="duration" radius={[3, 3, 0, 0]}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} fillOpacity={0.7} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
