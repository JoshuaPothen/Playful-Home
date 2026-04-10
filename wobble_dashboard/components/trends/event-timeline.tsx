'use client';

import type { WobbleEvent } from '@/lib/types';

interface EventTimelineProps {
  events: WobbleEvent[];
}

const TYPE_COLORS: Record<string, string> = {
  scene_change: '#9b6dff',
  proximity_change: '#4a9edd',
  session_start: '#34d399',
  session_end: '#f87171',
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function eventDescription(event: WobbleEvent): string {
  switch (event.type) {
    case 'scene_change':
      return `Scene → ${event.scene_name ?? `Scene ${event.scene}`}`;
    case 'proximity_change':
      return `${event.rocker ?? '?'} proximity change`;
    default:
      return event.type;
  }
}

export function EventTimeline({ events }: EventTimelineProps) {
  const displayEvents = events.slice(0, 100);

  return (
    <div className="rounded-lg border border-[var(--border)] p-4" style={{ background: 'var(--bg2)' }}>
      <p className="text-[0.6rem] text-zinc-500 tracking-[0.2em] uppercase mb-3">
        Event Log
      </p>
      {displayEvents.length === 0 ? (
        <div className="h-48 flex items-center justify-center">
          <p className="text-zinc-700 text-xs">No events</p>
        </div>
      ) : (
        <div className="max-h-[260px] overflow-y-auto space-y-1 pr-1 scrollbar-thin">
          {displayEvents.map((evt) => (
            <div
              key={evt.id}
              className="flex items-start gap-2 py-1 border-b border-zinc-900"
            >
              <div
                className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                style={{ background: TYPE_COLORS[evt.type] ?? '#71717a' }}
              />
              <div className="min-w-0 flex-1">
                <p className="text-xs text-zinc-300 truncate">
                  {eventDescription(evt)}
                </p>
                <p className="text-[0.5rem] text-zinc-600 font-mono">
                  {formatTimestamp(evt.timestamp)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
