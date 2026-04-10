'use client';

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { SCENE_INFO } from '@/lib/constants';

interface SceneDistributionProps {
  stats: {
    byScene: Record<number, number>;
  };
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

export function SceneDistribution({ stats }: SceneDistributionProps) {
  const data = Object.entries(stats.byScene).map(([scene, seconds]) => {
    const num = Number(scene);
    const info = SCENE_INFO[num] ?? { label: `Scene ${num}`, color: '#71717a' };
    return {
      name: info.label,
      seconds,
      displayTime: formatTime(seconds),
      color: info.color,
    };
  });

  const total = data.reduce((sum, d) => sum + d.seconds, 0);

  return (
    <div className="rounded-lg border border-[var(--border)] p-4" style={{ background: 'var(--bg2)' }}>
      <p className="text-[0.6rem] text-zinc-500 tracking-[0.2em] uppercase mb-3">
        Scene Distribution
      </p>
      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center">
          <p className="text-zinc-700 text-xs">No data</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Bar segments */}
          <div className="flex rounded-md overflow-hidden h-6">
            {data.map((d, i) => (
              <div
                key={i}
                className="h-full transition-all"
                style={{
                  width: `${total > 0 ? (d.seconds / total) * 100 : 0}%`,
                  background: d.color,
                  opacity: 0.7,
                  minWidth: d.seconds > 0 ? '2px' : 0,
                }}
              />
            ))}
          </div>

          {/* Legend */}
          <div className="space-y-2">
            {data.map((d, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ background: d.color }} />
                  <span className="text-xs text-zinc-400">{d.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-zinc-300">{d.displayTime}</span>
                  <span className="text-[0.55rem] text-zinc-600 font-mono w-10 text-right">
                    {total > 0 ? Math.round((d.seconds / total) * 100) : 0}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
