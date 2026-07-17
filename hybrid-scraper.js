// hybrid-scraper.js
import 'dotenv/config';
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.VITE_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

const API_KEY = process.env.VITE_API_FOOTBALL_KEY;
const BZZOIRO_TOKEN = process.env.VITE_BZZOIRO_API_KEY;

const apiHeaders = { 'x-apisports-key': API_KEY };
const bzzoiroHeaders = {
  'Authorization': `Token ${BZZOIRO_TOKEN}`,
  'Accept': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
};

// 🎯 Only deeply scrape these leagues to stay under the 100 API-Football limit
const TOP_LEAGUES = [39, 140, 78, 135, 61, 2]; // Premier, La Liga, Bundesliga, Serie A, Ligue 1, UCL

async function fetchWithRetry(url, headers, retries = 2) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await axios.get(url, { headers, timeout: 15000 });
      return res.data;
    } catch (error) {
      if (i < retries - 1) await new Promise(r => setTimeout(r, 1500));
    }
  }
  return null;
}

async function runHybridScraper() {
  console.log(" Starting Smart Hybrid Scraper (API-Football + Bzzoiro)...");
  const today = new Date().toISOString().split('T')[0];
  let apiRequestsUsed = 0;

  try {
    // 1. Get ALL matches from API-Football (USES 1 REQUEST)
    console.log("🌍 Fetching global fixtures from API-Football...");
    const fixturesData = await fetchWithRetry(`https://v3.football.api-sports.io/fixtures?date=${today}`, apiHeaders);
    apiRequestsUsed++;

    const fixtures = fixturesData?.response || [];
    console.log(`📅 Found ${fixtures.length} total matches today.`);

    let enrichedCount = 0;
    let basicCount = 0;

    for (const match of fixtures) {
      const fixtureId = match.fixture.id;
      const leagueId = match.league.id;
      const leagueName = match.league.name;
      const homeName = match.teams.home.name;
      const awayName = match.teams.away.name;
      const homeId = match.teams.home.id;
      const awayId = match.teams.away.id;

      // Format the time nicely (e.g., "19:00")
      const kickoffTime = new Date(match.fixture.date).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

      const isTopLeague = TOP_LEAGUES.includes(leagueId);

      console.log(`\n🔍 Processing: ${homeName} vs ${awayName} (${isTopLeague ? 'TOP LEAGUE' : 'Basic'})`);

      let h2hData = [], homeForm = [], awayForm = [], predData = null, oddsData = null;

      if (isTopLeague && apiRequestsUsed < 90) {
        // 2. Fetch H2H & Form from API-Football (USES 3 REQUESTS)
        const h2h = await fetchWithRetry(`https://v3.football.api-sports.io/fixtures/headtohead?h2h=${homeId}-${awayId}&last=5`, apiHeaders);
        apiRequestsUsed++;
        h2hData = h2h?.response?.map(m => ({
          date: m.fixture.date, home: m.teams.home.name, away: m.teams.away.name, score: `${m.goals.home}-${m.goals.away}`
        })) || [];

        const homeF = await fetchWithRetry(`https://v3.football.api-sports.io/fixtures?team=${homeId}&last=5`, apiHeaders);
        apiRequestsUsed++;
        homeForm = homeF?.response || [];

        const awayF = await fetchWithRetry(`https://v3.football.api-sports.io/fixtures?team=${awayId}&last=5`, apiHeaders);
        apiRequestsUsed++;
        awayForm = awayF?.response || [];

        // 3. Try to enrich with Bzzoiro ML Predictions (UNLIMITED REQUESTS)
        const bzzEvents = await fetchWithRetry(
          `https://sports.bzzoiro.com/api/v2/events/?team_name=${encodeURIComponent(homeName)}&date_from=${today}&date_to=${today}`,
          bzzoiroHeaders
        );

        const bzzMatch = bzzEvents?.results?.find(e => e.away_team.toLowerCase().includes(awayName.toLowerCase()));

        if (bzzMatch) {
          predData = await fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzMatch.id}/prediction/`, bzzoiroHeaders);
          oddsData = await fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${bzzMatch.id}/odds/`, bzzoiroHeaders);
          console.log(`  ✨ Enriched with Bzzoiro ML Data!`);
        }
        enrichedCount++;
      } else {
        basicCount++;
      }

      // 4. Save to Supabase (Includes new columns for the frontend)
      await supabase.from('match_stats').upsert({
        fixture_id: fixtureId,
        home_team_id: homeId,
        away_team_id: awayId,
        league_name: leagueName,
        kickoff_time: kickoffTime,
        home_team_name: homeName,
        away_team_name: awayName,
        h2h_data: h2hData,
        home_form: homeForm,
        away_form: awayForm,
        prediction_data: predData,
        odds_data: oddsData,
        updated_at: new Date()
      });

      console.log(`  ✅ Saved to Supabase! (API Requests Used: ${apiRequestsUsed}/100)`);

      // Polite delay
      await new Promise(resolve => setTimeout(resolve, 800));
    }

    console.log(`\n🎉 HYBRID SCRAPER COMPLETE!`);
    console.log(`📊 Total Matches Saved: ${fixtures.length}`);
    console.log(`🏆 Richly Enriched (Top Leagues): ${enrichedCount}`);
    console.log(`📝 Basic Info Only (Lower Leagues): ${basicCount}`);
    console.log(`🔑 API-Football Requests Used: ${apiRequestsUsed}/100`);

  } catch (error) {
    console.error("❌ Fatal Error:", error.response?.data || error.message);
  }
}

runHybridScraper();