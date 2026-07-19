-- Run this in the Supabase SQL editor (Project → SQL Editor → New query).
--
-- Switching from API-Football to Bzzoiro changes the status column's
-- vocabulary: API-Football used 'FT' (full time) / 'NS' (not started);
-- Bzzoiro uses 'finished' / 'notstarted' (plus several in-progress
-- states this app doesn't otherwise distinguish between).
--
-- Any row already in match_stats from before this switch — either
-- scraped by the old API-Football-based scraper, or manually added via
-- the admin "Add Match" form before it was updated — still has the old
-- values. Without this, those rows would be filtered incorrectly by the
-- new Bzzoiro-based queries (a finished match tagged 'FT' would
-- wrongly still show as upcoming, since the new filter only recognizes
-- 'finished'). Normalizing preserves any admin_prediction already
-- entered on those rows rather than losing them.

update match_stats set status = 'finished' where status = 'FT';
update match_stats set status = 'notstarted' where status = 'NS';
