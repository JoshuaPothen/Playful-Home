'use client';

import { BULB_LABELS, ROCKERS, SCENE_INFO } from '@/lib/constants';
import { resolveHue } from '@/lib/utils';
import type { WobbleState } from '@/lib/types';

interface ScenePanelProps {
  state: WobbleState | null;
}

interface BulbOrbProps {
  colour: string;
  label: string;
}

function BulbOrb({ colour, label }: BulbOrbProps) {
  const hex = resolveHue(colour);
  const isOff = !colour || colour === 'off';

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className="w-20 h-20 rounded-full transition-all duration-500"
        style={{
          backgroundColor: isOff ? '#0d0d1a' : hex,
          boxShadow: isOff ? 'none' : `0 0 60px 24px ${hex}66`,
        }}
      />
      <span className="text-[0.5rem] tracking-widest text-zinc-500 uppercase">
        {label}
      </span>
    </div>
  );
}

export function ScenePanel({ state }: ScenePanelProps) {
  const scene = state?.scene ?? 0;
  const sceneInfo = SCENE_INFO[scene] ?? SCENE_INFO[0];
  const bulbs = state?.hue_bulbs ?? [];

  const liveness: Record<string, boolean> = {
    r1: state?.r1_live ?? false,
    r2: state?.r2_live ?? false,
    tx: state?.tx_live ?? false,
  };

  return (
    <section className="flex flex-col items-center justify-center gap-6 border-b border-[var(--border)] py-6 px-8">
      {/* Connection indicators */}
      <div className="flex items-center gap-6">
        {(Object.entries(ROCKERS) as [string, { label: string; color: string }][]).map(
          ([key, rocker]) => (
            <div key={key} className="flex items-center gap-1.5">
              <div
                className="w-2 h-2 rounded-full transition-all duration-300"
                style={
                  liveness[key]
                    ? { background: '#34d399', boxShadow: '0 0 6px #34d399' }
                    : { background: '#27272a' }
                }
              />
              <span className="text-[0.6rem] text-zinc-500 tracking-wider">
                {rocker.label}
              </span>
            </div>
          )
        )}
      </div>

      <div
        className="rounded-full px-3 py-1 text-xs tracking-widest border transition-colors duration-500"
        style={{ color: sceneInfo.color, borderColor: sceneInfo.color }}
      >
        {sceneInfo.label}
      </div>
      <div className="grid grid-cols-4 gap-8">
        {BULB_LABELS.map((label, i) => (
          <BulbOrb key={label} colour={bulbs[i] ?? ''} label={label} />
        ))}
      </div>
    </section>
  );
}
