// hybrid-scraper.js
//
// Bzzoiro-only scraper. Previously this pulled the global fixture list
// from API-Football (limited to 100 requests/day on the free tier, and
// prone to "missing application key" plan restrictions) and used
// Bzzoiro only as a supplementary enrichment source for a handful of
// top leagues. Now Bzzoiro is the sole source: it already provides
// fixtures, predictions, odds, confidence, form, and head-to-head data
// directly, with no artificial per-day request ceiling.
//
// Bzzoiro's own match coverage is narrower than a full global sweep —
// that's expected and fine, since admins can manually add any match
// Bzzoiro doesn't have via the "Add Match" form in /admin. This script
// only ever populates matches Bzzoiro actually knows about; it never
// touches manually-added rows (those have negative fixture_id values,
// which Bzzoiro's real event IDs will never collide with).
import 'dotenv/config';
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.VITE_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

const BZZOIRO_TOKEN = process.env.VITE_BZZOIRO_API_KEY;
const bzzoiroHeaders = {
  'Authorization': `Token ${BZZOIRO_TOKEN}`,
  'Accept': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
      if (i < retries - 1) await new Promise(r => setTimeout(r, 1500));
    }
  }
  return null;
}

function isoDateOffset(offsetDays) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().split('T')[0];
}

// Best-effort field extraction: Bzzoiro's exact response shape per
// endpoint isn't formally documented here, so this checks a few
// plausible field name variants rather than assuming one. Logged
// clearly if nothing matches, so a wrong guess is visible in the run
// output instead of silently producing empty data.
function pick(obj, ...keys) {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return null;
}

async function runBzzoiroScraper() {
  console.log('🎯 Starting Bzzoiro-only scraper...');

  if (!BZZOIRO_TOKEN) {
    console.error('❌ VITE_BZZOIRO_API_KEY is not set. Cannot continue.');
    process.exitCode = 1;
    return;
  }

  const datesToScrape = [isoDateOffset(-1), isoDateOffset(0), isoDateOffset(1)];

  let totalFound = 0;
  let savedCount = 0;
  let failedCount = 0;
  let enrichedCount = 0;

  for (const dateStr of datesToScrape) {
    console.log(`\n📅 Fetching Bzzoiro events for ${dateStr}...`);

    const eventsData = await fetchWithRetry(
      `https://sports.bzzoiro.com/api/v2/events/?date_from=${dateStr}&date_to=${dateStr}`,
      bzzoiroHeaders
    );

    const events = eventsData?.results || eventsData?.response || [];
    console.log(`  Found ${events.length} events on ${dateStr}.`);
    totalFound += events.length;

    for (const event of events) {
      const bzzId = pick(event, 'id', 'event_id');
      const homeName = pick(event, 'home_team', 'home_team_name');
      const awayName = pick(event, 'away_team', 'away_team_name');
      const leagueName = pick(event, 'league_name', 'competition_name', 'league') || 'Unknown League';
      const kickoffIso = pick(event, 'kickoff', 'start_time', 'date', 'datetime');
      const statusRaw = pick(event, 'status', 'status_short') || 'NS';
      const homeScore = pick(event, 'home_score', 'score_home');
      const awayScore = pick(event, 'away_score', 'score_away');

      if (!bzzId || !homeName || !awayName) {
        console.error(`  ⚠️  Skipping event with missing core fields:`, JSON.stringify(event).slice(0, 200));
        failedCount++;
        continue;
      }

      console.log(`\n🔍 ${homeName} vs ${awayName} (${leagueName})`);

      const [predData, oddsData, h2hRes, homeFormRes, awayFormRes] = await Promise.all([
        fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/prediction/`, bzzoiroHeaders),
        fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/odds/`, bzzoiroHeaders),
        fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/h2h/`, bzzoiroHeaders),
        fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/form/?side=home`, bzzoiroHeaders),
        fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzId}/form/?side=away`, bzzoiroHeaders),
      ]);

      if (predData || oddsData) enrichedCount++;

      const h2hData = h2hRes?.results || h2hRes?.response || [];
      const homeForm = homeFormRes?.results || homeFormRes?.response || [];
      const awayForm = awayFormRes?.results || awayFormRes?.response || [];

      const kickoffTime = kickoffIso
        ? new Date(kickoffIso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
        : 'TBA';

      const { error: upsertError } = await supabase.from('match_stats').upsert({
        fixture_id: bzzId,
        league_name: leagueName,
        kickoff_time: kickoffTime,
        fixture_date: kickoffIso,
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
      }, { onConflict: 'fixture_id' });

      if (upsertError) {
        console.error(`  ❌ Supabase upsert FAILED for event ${bzzId}:`, upsertError.message || upsertError);
        failedCount++;
      } else {
        console.log(`  ✅ Saved${predData || oddsData ? ' with prediction/odds data' : ''}.`);
        savedCount++;
      }

      // Polite delay between events
      await new Promise((r) => setTimeout(r, 500));
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
