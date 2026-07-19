// hybrid-scraper.js
//
// Bzzoiro-only scraper, built against the official Bzzoiro Sports Data
// API v2 OpenAPI spec. Bzzoiro provides fixtures, CatBoost predictions,
// consensus odds, and head-to-head data directly — no API-Football
// dependency needed for fixture discovery.
//
// Bzzoiro's own match coverage is narrower than a full global sweep —
// that's expected. Admins can manually add any match Bzzoiro doesn't
// have via the "Add Match" form in /admin. This script only ever
// populates matches Bzzoiro actually knows about; it never touches
// manually-added rows (those have negative fixture_id values, which
// Bzzoiro's real event IDs — always positive — will never collide with).
import 'dotenv/config';
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.VITE_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

const BZZOIRO_TOKEN = process.env.VITE_BZZOIRO_API_KEY;
const bzzoiroHeaders = {
  'Authorization': `Token ${BZZOIRO_TOKEN}`,
  'Accept': 'application/json',
};

async function fetchWithRetry(url, headers, retries = 2) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await axios.get(url, { headers, timeout: 15000 });
      return res.data;
    } catch (error) {
      const status = error.response?.status;
      const body = error.response?.data;
      console.error(`  ⚠️  Request failed (attempt ${i + 1}/${retries}) [${status || 'network error'}] ${url}:`, body ? JSON.stringify(body).slice(0, 300) : error.message);
      if (i < retries - 1) await new Promise((r) => setTimeout(r, 1500));
    }
  }
  return null;
}

function isoDateOffset(offsetDays) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().split('T')[0];
}

// Matches that are genuinely over. Everything else (notstarted,
// 1st_half, 2nd_half, halftime, extratime, aet, penalties, delayed,
// postponed) is treated as "not yet finished" and stays visible as an
// upcoming pick on the site.
const FINISHED_STATUSES = new Set(['finished']);

async function fetchAllLeagues() {
  console.log('📚 Fetching league list for name lookups...');
  const data = await fetchWithRetry('https://sports.bzzoiro.com/api/v2/leagues/?limit=200', bzzoiroHeaders);
  const leagues = data?.results || data || [];
  const map = new Map();
  for (const l of leagues) map.set(l.id, l.name);
  console.log(`  Loaded ${map.size} leagues.`);
  return map;
}

// Derives last-5 form (most recent finished matches before this event)
// from /teams/{id}/fixtures/ — Bzzoiro has no dedicated form endpoint.
async function fetchRecentForm(teamId, beforeDateIso) {
  if (!teamId || !beforeDateIso) return [];
  const dateTo = beforeDateIso.split('T')[0];
  const dateFrom = isoDateOffset(-90); // look back 90 days for finished matches
  const data = await fetchWithRetry(
    `https://sports.bzzoiro.com/api/v2/teams/${teamId}/fixtures/?status=finished&date_from=${dateFrom}&date_to=${dateTo}&limit=20`,
    bzzoiroHeaders
  );
  const fixtures = data?.results || data || [];
  return fixtures
    .slice()
    .sort((a, b) => new Date(b.event_date) - new Date(a.event_date))
    .slice(0, 5)
    .map((f) => ({
      event_id: f.id,
      event_date: f.event_date,
      home_team: f.home_team,
      away_team: f.away_team,
      home_score: f.home_score,
      away_score: f.away_score,
    }));
}

async function runBzzoiroScraper() {
  console.log('🎯 Starting Bzzoiro-only scraper...');

  if (!BZZOIRO_TOKEN) {
    console.error('❌ VITE_BZZOIRO_API_KEY is not set. Cannot continue.');
    process.exitCode = 1;
    return;
  }

  const leagueNames = await fetchAllLeagues();
  const datesToScrape = [isoDateOffset(-1), isoDateOffset(0), isoDateOffset(1)];

  let totalFound = 0;
  let savedCount = 0;
  let failedCount = 0;
  let enrichedCount = 0;

  for (const dateStr of datesToScrape) {
    console.log(`\n📅 Fetching Bzzoiro events for ${dateStr}...`);

    const eventsData = await fetchWithRetry(
      `https://sports.bzzoiro.com/api/v2/events/?date_from=${dateStr}&date_to=${dateStr}&limit=200`,
      bzzoiroHeaders
    );

    const events = eventsData?.results || eventsData || [];
    console.log(`  Found ${events.length} events on ${dateStr}.`);
    totalFound += events.length;

    for (const event of events) {
      const {
        id: bzzId,
        home_team: homeName,
        away_team: awayName,
        home_team_id: homeTeamId,
        away_team_id: awayTeamId,
        event_date: eventDate,
        status: statusRaw,
        home_score: homeScore,
        away_score: awayScore,
        league_id: leagueId,
      } = event;

      if (!bzzId || !homeName || !awayName) {
        console.error(`  ⚠️  Skipping event with missing core fields:`, JSON.stringify(event).slice(0, 200));
        failedCount++;
        continue;
      }

      const leagueName = leagueNames.get(leagueId) || 'Unknown League';
      console.log(`\n🔍 ${homeName} vs ${awayName} (${leagueName}) — status: ${statusRaw}`);

      const isFinished = FINISHED_STATUSES.has(statusRaw);

      // Only bother fetching prediction/odds/h2h/form for matches that
      // haven't been played yet — no point enriching historical results.
      let predData = null, oddsData = null, h2hData = null, homeForm = [], awayForm = [];
      if (!isFinished) {
        [predData, oddsData, h2hData, homeForm, awayForm] = await Promise.all([
          fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/prediction/`, bzzoiroHeaders),
          fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/odds/`, bzzoiroHeaders),
          fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/h2h/`, bzzoiroHeaders),
          fetchRecentForm(homeTeamId, eventDate),
          fetchRecentForm(awayTeamId, eventDate),
        ]);
        if (predData || oddsData) enrichedCount++;
      }

      const kickoffTime = eventDate
        ? new Date(eventDate).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
        : 'TBA';

      const { error: upsertError } = await supabase.from('match_stats').upsert(
        {
          fixture_id: bzzId,
          home_team_id: homeTeamId,
          away_team_id: awayTeamId,
          league_name: leagueName,
          kickoff_time: kickoffTime,
          fixture_date: eventDate,
          status: statusRaw,
          home_score: homeScore,
          away_score: awayScore,
          home_team_name: homeName,
          away_team_name: awayName,
          h2h_data: h2hData,
          home_form: homeForm,
          away_form: awayForm,
          prediction_data: predData,
          odds_data: oddsData,
          updated_at: new Date(),
        },
        { onConflict: 'fixture_id' }
      );

      if (upsertError) {
        console.error(`  ❌ Supabase upsert FAILED for event ${bzzId}:`, upsertError.message || upsertError);
        failedCount++;
      } else {
        console.log(`  ✅ Saved${predData || oddsData ? ' with prediction/odds data' : ''}.`);
        savedCount++;
      }

      await new Promise((r) => setTimeout(r, 400)); // polite delay
    }
  }

  console.log(`\n🎉 BZZOIRO SCRAPER COMPLETE!`);
  console.log(`📊 Events Found: ${totalFound}`);
  console.log(`✅ Saved to Supabase: ${savedCount}`);
  console.log(`✨ With Prediction/Odds Data: ${enrichedCount}`);
  console.log(`❌ Failed: ${failedCount}`);

  if (totalFound > 0 && savedCount === 0) {
    console.error('\n⚠️  Every single Supabase write failed. Failing the job so this shows up as an error, not a false success.');
    process.exitCode = 1;
  }
}

runBzzoiroScraper();
