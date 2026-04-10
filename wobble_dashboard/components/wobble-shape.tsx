'use client';

import { useEffect, useRef, useState } from 'react';

interface WobbleShapeProps {
  gyro: [number, number, number];
  color: string;
  live: boolean;
}

// How much of the gap to close each frame (0–1). Lower = slower/smoother.
const LERP = 0.06;

// Scale rad/s → target degrees
const SCALE = 16;
const MAX_DEG = 30;

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

const WOBBLE_PATH =
  'M24.5 0C30.299 0 35 1.34315 35 3V38.3584C43.2772 42.2906 49 50.7267 49 60.5C49 74.031 38.031 85 24.5 85C10.969 85 0 74.031 0 60.5C0 50.7267 5.72283 42.2906 14 38.3584V3C14 1.34315 18.701 0 24.5 0Z';

export function WobbleShape({ gyro, color, live }: WobbleShapeProps) {
  const targetRef = useRef(0);
  const currentRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const [displayAngle, setDisplayAngle] = useState(0);

  // Update target whenever gyro changes
  targetRef.current = clamp(gyro[0] * SCALE, -MAX_DEG, MAX_DEG);

  // RAF loop: lerp current → target each frame
  useEffect(() => {
    function tick() {
      const delta = targetRef.current - currentRef.current;
      if (Math.abs(delta) > 0.01) {
        currentRef.current += delta * LERP;
        setDisplayAngle(currentRef.current);
      }
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Magnitude for glow (also lerp toward 0 when calm)
  const mag = Math.sqrt(gyro[0] ** 2 + gyro[1] ** 2 + gyro[2] ** 2);
  const glowStr = Math.min(mag / 3, 1);
  const glowBlur = 4 + glowStr * 12;
  const glowOpacity = 0.2 + glowStr * 0.55;
  const glowHex = Math.round(glowOpacity * 255).toString(16).padStart(2, '0');

  return (
    <div className="flex items-center justify-center w-full h-full">
      {/* Pivot at base center */}
      <div
        style={{
          transformOrigin: '50% 100%',
          transform: `rotateZ(${displayAngle}deg)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: live ? 1 : 0.35,
          transition: 'opacity 500ms',
        }}
      >
        <svg
          viewBox="0 0 49 85"
          width="100%"
          height="100%"
          style={{ maxHeight: '160px', maxWidth: '100px', overflow: 'visible' }}
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <radialGradient id={`fill-${color}`} cx="40%" cy="35%" r="65%">
              <stop offset="0%" stopColor={color} stopOpacity="0.22" />
              <stop offset="100%" stopColor={color} stopOpacity="0.05" />
            </radialGradient>
            <radialGradient id={`spec-${color}`} cx="36%" cy="28%" r="28%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
            </radialGradient>
          </defs>

          <path
            d={WOBBLE_PATH}
            fill={`url(#fill-${color})`}
            stroke={color}
            strokeWidth="1.5"
            strokeLinejoin="round"
            style={{
              filter: `drop-shadow(0 0 ${glowBlur}px ${color}${glowHex})`,
              transition: 'filter 300ms ease-out',
            }}
          />
          <path d={WOBBLE_PATH} fill={`url(#spec-${color})`} stroke="none" />
        </svg>
      </div>
    </div>
  );
}
