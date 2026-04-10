-- Wobble Activity & Trend Monitor — Supabase Schema
-- Run this in the Supabase SQL Editor to create all required tables.

-- ===== SESSIONS =====
create table if not exists sessions (
  id uuid default gen_random_uuid() primary key,
  session_id text unique not null,
  rocker text not null,
  started_at timestamptz not null,
  ended_at timestamptz,
  duration_s real,
  peak_magnitude real,
  wobble_seconds real,
  status text not null default 'active' check (status in ('active', 'ended'))
);

create index if not exists idx_sessions_started_at on sessions (started_at desc);
create index if not exists idx_sessions_rocker on sessions (rocker);

-- ===== EVENTS =====
create table if not exists events (
  id bigint generated always as identity primary key,
  type text not null,
  rocker text,
  scene int,
  scene_name text,
  detail jsonb,
  timestamp timestamptz default now()
);

create index if not exists idx_events_timestamp on events (timestamp desc);
create index if not exists idx_events_type on events (type);

-- ===== ACTIVITY SNAPSHOTS =====
create table if not exists activity_snapshots (
  id bigint generated always as identity primary key,
  timestamp timestamptz default now(),
  scene int,
  r1_ema real,
  r2_ema real,
  tx_ema real,
  r1_session_active boolean,
  r2_session_active boolean,
  tx_session_active boolean,
  r1_session_duration_s real,
  r2_session_duration_s real,
  tx_session_duration_s real,
  r1_distance real,
  r2_distance real,
  r1_live boolean,
  r2_live boolean,
  tx_live boolean
);

create index if not exists idx_snapshots_timestamp on activity_snapshots (timestamp desc);

-- ===== ROW LEVEL SECURITY =====
-- Enable RLS on all tables
alter table sessions enable row level security;
alter table events enable row level security;
alter table activity_snapshots enable row level security;

-- Public read-only for anon key (web dashboard)
create policy "anon read sessions" on sessions for select to anon using (true);
create policy "anon read events" on events for select to anon using (true);
create policy "anon read snapshots" on activity_snapshots for select to anon using (true);

-- Service key (used by Python processor) bypasses RLS automatically.
