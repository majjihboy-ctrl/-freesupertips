-- Run this in the Supabase SQL editor (Project → SQL Editor → New query).
--
-- Why: hybrid-scraper.js now writes a few new fields per match, and the
-- admin dashboard needs override columns to store manual tip edits.
-- Run this BEFORE the next scraper run / before visiting /admin.

alter table match_stats add column if not exists fixture_date timestamptz;
alter table match_stats add column if not exists status text default 'NS';
alter table match_stats add column if not exists home_score integer;
alter table match_stats add column if not exists away_score integer;

-- Admin dashboard overrides. Null = "use the scraper/derived value".
alter table match_stats add column if not exists admin_prediction text;
alter table match_stats add column if not exists admin_odds text;
alter table match_stats add column if not exists admin_confidence text;
alter table match_stats add column if not exists is_premium_override boolean;

create index if not exists idx_match_stats_fixture_date on match_stats (fixture_date);
create index if not exists idx_match_stats_status on match_stats (status);

-- match_stats needs a unique constraint on fixture_id for the scraper's
-- upsert(..., { onConflict: 'fixture_id' }) to work as an actual upsert
-- rather than always inserting new rows.
alter table match_stats add constraint if not exists match_stats_fixture_id_key unique (fixture_id);
