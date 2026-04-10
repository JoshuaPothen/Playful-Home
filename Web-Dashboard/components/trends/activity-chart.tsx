'use client';

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { ROCKERS } from '@/lib/constants';
import type { ActivitySnapshot } from '@/lib/types';

interface ActivityChartProps {
  snapshots: ActivitySnapshot[];
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function ActivityChart({ snapshots }: ActivityChartProps) {
  const data = snapshots.map((s) => ({
    time: formatTime(s.timestamp),
    r1: s.r1_ema,
    r2: s.r2_ema,
    tx: s.tx_ema,
  }));

  return (
    <div className="rounded-lg border border-[var(--border)] p-4" style={{ background: 'var(--bg2)' }}>
      <p className="text-[0.6rem] text-zinc-500 tracking-[0.2em] uppercase mb-3">
        Wobble Activity (EMA)
      </p>
      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center">
          <p className="text-zinc-700 text-xs">No snapshot data</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data}>
            <XAxis
              dataKey="time"
              tick={{ fontSize: 9, fill: '#52525b' }}
              axisLine={{ stroke: '#27272a' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 9, fill: '#52525b' }}
              axisLine={{ stroke: '#27272a' }}
              tickLine={false}
              width={30}
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
            />
            <Area
              type="monotone"
              dataKey="r1"
              name={ROCKERS.r1.label}
              stroke={ROCKERS.r1.color}
              fill={ROCKERS.r1.color + '22'}
              strokeWidth={1.5}
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="r2"
              name={ROCKERS.r2.label}
              stroke={ROCKERS.r2.color}
              fill={ROCKERS.r2.color + '22'}
              strokeWidth={1.5}
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="tx"
              name={ROCKERS.tx.label}
              stroke={ROCKERS.tx.color}
              fill={ROCKERS.tx.color + '22'}
              strokeWidth={1.5}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
