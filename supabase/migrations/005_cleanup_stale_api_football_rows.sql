-- Run this in the Supabase SQL editor (Project → SQL Editor → New query).
--
-- Cleans up leftover rows from before the switch to Bzzoiro. The old
-- API-Football-based scraper wrote ~200 rows using API-Football's own
-- fixture IDs. Since the new Bzzoiro-only scraper only ever
-- upserts by Bzzoiro's own (different) event IDs, those old rows are
-- never touched or refreshed anymore — they just sit there cluttering
-- the admin match list.
--
-- This finds the most recent successful scrape batch (by updated_at)
-- among real provider-sourced rows and removes anything older than
-- that batch window — i.e., anything NOT part of the last scrape run.
--
-- SAFE: only targets fixture_id > 0 (real provider rows). Manually-added
-- matches always have a NEGATIVE fixture_id and are never touched by
-- this cleanup, regardless of how old they are.
delete from match_stats
where fixture_id > 0
  and updated_at < (
    select max(updated_at) from match_stats where fixture_id > 0
  ) - interval '2 hours';
