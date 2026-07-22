-- Run this in the Supabase SQL editor (Project → SQL Editor → New query).
--
-- Accumulators: an admin-curated bundle of picks (e.g. "Today's 3-fold
-- Accumulator") built from matches already in match_stats. No RLS is
-- set up here, matching match_stats' existing setup (writes go through
-- the client with the admin's session, same pattern already in use for
-- editing match_stats from /admin).

create table if not exists accumulators (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  is_premium boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Join table: which matches belong to which accumulator, and in what
-- order. Deliberately does NOT snapshot the prediction text — it's
-- always derived live from match_stats (admin_prediction or Bzzoiro's
-- own data) at render time, same as everywhere else on the site, so an
-- accumulator never goes stale relative to the match it references.
create table if not exists accumulator_matches (
  id uuid primary key default gen_random_uuid(),
  accumulator_id uuid not null references accumulators(id) on delete cascade,
  fixture_id bigint not null,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  unique (accumulator_id, fixture_id)
);

create index if not exists idx_accumulator_matches_accumulator_id on accumulator_matches (accumulator_id);
