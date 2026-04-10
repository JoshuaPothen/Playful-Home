'use client';

import { useEffect, useState } from 'react';

const WORDS = ['PLAYFUL', 'HOME'];
const ROCKER_COLORS = ['#c97a3a', '#7a8fc0', '#7855d8'];
const TOTAL_DURATION = 2800; // ms before fade-out begins

export function IntroOverlay() {
  const [phase, setPhase] = useState<'playing' | 'fading' | 'done'>('playing');

  useEffect(() => {
    const fadeTimer = setTimeout(() => setPhase('fading'), TOTAL_DURATION);
    const doneTimer = setTimeout(() => setPhase('done'), TOTAL_DURATION + 700);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(doneTimer);
    };
  }, []);

  if (phase === 'done') return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center"
      style={{
        background: '#050510',
        animation: phase === 'fading' ? 'intro-fade-out 700ms ease-in forwards' : undefined,
      }}
    >
      {/* Radial glow behind wordmark */}
      <div
        className="absolute"
        style={{
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(120,85,216,0.12) 0%, transparent 70%)',
          animation: 'intro-glow-pulse 2s ease-in-out infinite',
        }}
      />

      {/* Wordmark — staggered letter entrance */}
      <div className="relative flex flex-col items-center gap-0 leading-none">
        {WORDS.map((word, wi) => (
          <div key={wi} className="flex items-center gap-[0.12em]">
            {word.split('').map((letter, li) => {
              const globalIndex = wi === 0 ? li : WORDS[0].length + 1 + li;
              return (
                <span
                  key={li}
                  className="text-[2rem] sm:text-[3.5rem] md:text-[5rem] font-semibold text-zinc-100 leading-none"
                  style={{
                    opacity: 0,
                    animation: `intro-letter-in 500ms cubic-bezier(0.16, 1, 0.3, 1) ${200 + globalIndex * 80}ms forwards`,
                    letterSpacing: '0.1em',
                  }}
                >
                  {letter}
                </span>
              );
            })}
          </div>
        ))}
      </div>

      {/* Three rocker color lines — staggered draw */}
      <div className="flex flex-col items-center gap-[3px] mt-5">
        {ROCKER_COLORS.map((color, i) => (
          <div
            key={i}
            className="h-[2px] rounded-full"
            style={{
              width: i === 1 ? 120 : i === 0 ? 90 : 60,
              background: color,
              transformOrigin: 'left center',
              transform: 'scaleX(0)',
              animation: `intro-line-draw 600ms cubic-bezier(0.16, 1, 0.3, 1) ${900 + i * 150}ms forwards`,
              boxShadow: `0 0 12px ${color}66`,
            }}
          />
        ))}
      </div>

      {/* Three dots representing rockers — ping in */}
      <div className="flex items-center gap-3 mt-6">
        {ROCKER_COLORS.map((color, i) => (
          <div
            key={i}
            className="w-[6px] h-[6px] rounded-full"
            style={{
              background: color,
              transform: 'scale(0)',
              animation: `intro-dot-ping 400ms cubic-bezier(0.16, 1, 0.3, 1) ${1600 + i * 120}ms forwards`,
              boxShadow: `0 0 8px ${color}88`,
            }}
          />
        ))}
      </div>

      {/* Subtitle */}
      <p
        className="mt-6 text-[0.6rem] uppercase text-zinc-500 font-light"
        style={{
          opacity: 0,
          animation: `intro-subtitle-in 800ms cubic-bezier(0.16, 1, 0.3, 1) 2000ms forwards`,
        }}
      >
        live dashboard
      </p>
    </div>
  );
}
