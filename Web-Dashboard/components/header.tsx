'use client';

import Link from 'next/link';
import type { WobbleState } from '@/lib/types';

interface HeaderProps {
  state: WobbleState | null;
}

export function Header({ state }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between px-4 sm:px-6 h-12 sm:h-16 border-b border-[var(--border)] shrink-0" style={{ background: 'var(--bg)' }}>
      {/* Logo */}
      <span className="font-semibold tracking-[0.42em] text-sm sm:text-[18px] text-zinc-100">
        PLAYFUL HOME
      </span>

      {/* Right side: nav links */}
      <div className="flex items-center gap-6">
        <Link
          href="/trends"
          className="text-sm sm:text-[18px] text-zinc-500 tracking-[0.3em] uppercase hover:text-zinc-300 transition-colors"
        >
          TRENDS
        </Link>
        <Link
          href="/about"
          className="text-sm sm:text-[18px] text-zinc-500 tracking-[0.3em] uppercase hover:text-zinc-300 transition-colors"
        >
          ABOUT
        </Link>
      </div>
    </header>
  );
}
