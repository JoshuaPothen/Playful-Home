'use client';

import { useRef } from 'react';

interface AccelBarsProps {
  accel: [number, number, number];
  color: string;
}

const AXES = ['X', 'Y', 'Z'] as const;
const MIN_MAX = 2; // minimum floor to avoid division by zero at rest

export function AccelBars({ accel, color }: AccelBarsProps) {
  const maxSeen = useRef<[number, number, number]>([MIN_MAX, MIN_MAX, MIN_MAX]);

  return (
    <div className="flex flex-col gap-2 justify-center h-full py-2">
      {AXES.map((axis, i) => {
        const raw = accel[i] ?? 0;
        const abs = Math.abs(raw);
        if (abs > maxSeen.current[i]) {
          maxSeen.current[i] = abs;
        }
        const pct = Math.min((abs / maxSeen.current[i]) * 100, 100);
        const barColor = color + 'cc'; // 80% opacity

        return (
          <div key={axis} className="flex items-center gap-2">
            <span className="text-[0.55rem] font-mono text-zinc-500 w-3 shrink-0">
              {axis}
            </span>
            <div
              className="flex-1 rounded-full overflow-hidden"
              style={{ background: 'rgba(255,255,255,0.05)', height: '6px' }}
            >
              <div
                className="h-full rounded-full transition-all duration-200"
                style={{
                  width: `${pct}%`,
                  background: barColor,
                }}
              />
            </div>
            <span className="text-[0.55rem] font-mono text-zinc-400 w-14 text-right shrink-0">
              {raw.toFixed(2)}<span className="text-zinc-600"> m/s²</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
