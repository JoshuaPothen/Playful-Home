'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { WobbleShape } from './wobble-shape';
import { AccelBars } from './accel-bars';
import { gyroMag, formatDist } from '@/lib/utils';

interface RockerCardProps {
  rockerKey: string;
  name: string;
  color: string;
  live: boolean;
  source: 'primary' | 'backup';
  isolated?: boolean;
  accel: [number, number, number];
  gyro: [number, number, number];
  distance?: number;
  sessionActive?: boolean;
  sessionDuration?: number;
  wobbleEma?: number;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function RockerCard({
  name,
  color,
  live,
  source,
  isolated,
  accel,
  gyro,
  distance,
  sessionActive,
  sessionDuration,
  wobbleEma,
}: RockerCardProps) {
  const mag = gyroMag(gyro);

  return (
    <Card
      className="flex flex-col border-[var(--border)] transition-opacity duration-500 gap-0"
      style={{
        background: 'var(--bg2)',
        opacity: live ? 1 : 0.3,
      }}
    >
      <CardHeader className="pb-1 pt-2 px-4">
        <div className="flex items-center gap-2">
          <span
            className="font-semibold text-base tracking-widest"
            style={{ color }}
          >
            {name}
          </span>
          <Badge
            variant="outline"
            className="text-[0.55rem] tracking-wider border-zinc-700 text-zinc-400 px-1.5 py-0"
          >
            {source}
          </Badge>
          {isolated && (
            <Badge
              className="text-[0.55rem] tracking-wider px-1.5 py-0"
              style={{ background: color + '33', color, border: `1px solid ${color}66` }}
            >
              ISO
            </Badge>
          )}
          <div
            className="ml-auto w-1.5 h-1.5 rounded-full transition-all duration-300"
            style={
              live
                ? { background: '#34d399', boxShadow: '0 0 5px #34d399' }
                : { background: '#27272a' }
            }
          />
        </div>
      </CardHeader>

      <CardContent className="flex flex-col px-4 pb-4 pt-1 gap-3">
        {/* Wobble shape */}
        <div className="h-[160px]">
          <WobbleShape gyro={gyro} color={color} live={live} />
        </div>

        {/* Accel bars */}
        <div className="min-h-[60px]">
          <AccelBars accel={accel} color={color} />
        </div>

        <Separator className="bg-[var(--border)]" />

        {/* Metrics */}
        <div className="flex items-center justify-between">
          {distance !== undefined ? (
            <div className="flex flex-col gap-0.5">
              <span className="text-[0.5rem] text-zinc-500 tracking-wider uppercase">Dist</span>
              <span className="text-sm text-zinc-200 font-mono">{formatDist(distance)}</span>
            </div>
          ) : (
            <div />
          )}
          <div className="flex flex-col gap-0.5 items-end">
            <span className="text-[0.5rem] text-zinc-500 tracking-wider uppercase">Gyro</span>
            <span className="text-sm text-zinc-200 font-mono">{mag.toFixed(1)} <span className="text-zinc-500 text-[0.55rem]">rad/s</span></span>
          </div>
        </div>

        {/* Session indicator */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={
                sessionActive
                  ? {
                      background: color,
                      boxShadow: `0 0 6px ${color}`,
                      animation: 'pulse 1.5s ease-in-out infinite',
                    }
                  : { background: '#27272a' }
              }
            />
            {sessionActive ? (
              <span className="text-xs font-mono" style={{ color }}>
                {formatDuration(sessionDuration ?? 0)}
              </span>
            ) : (
              <span className="text-[0.6rem] text-zinc-600 tracking-wider uppercase">
                IDLE
              </span>
            )}
          </div>
          {wobbleEma !== undefined && (
            <div className="flex flex-col gap-0.5 items-end">
              <span className="text-[0.5rem] text-zinc-500 tracking-wider uppercase">EMA</span>
              <span className="text-xs text-zinc-400 font-mono">{wobbleEma.toFixed(2)}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
