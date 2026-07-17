// daily-scraper.js
import 'dotenv/config';
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.VITE_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
const BZZOIRO_TOKEN = process.env.VITE_BZZOIRO_API_KEY;

console.log("🔑 Bzzoiro Token Status:", BZZOIRO_TOKEN ? `✅ Loaded (${BZZOIRO_TOKEN.substring(0, 6)}...)` : "❌ MISSING!");

// 🛡️ FIX 1: Add a real browser User-Agent to prevent silent connection drops
const bzzoiroHeaders = {
  'Authorization': `Token ${BZZOIRO_TOKEN}`,
  'Accept': 'application/json',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
};

// Helper: some v2 list endpoints return a bare array, others may return {count, next, previous, results}
function extractList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

// 🛡️ FIX 2: Automatic retry logic for timeouts (504, 429, ECONNABORTED)
async function fetchWithRetry(url, retries = 3, delay = 2000) {
  for (let i = 0; i < retries; i++) {
    try {
      // Increased timeout to 30 seconds to give the server time to respond
      const response = await axios.get(url, { headers: bzzoiroHeaders, timeout: 30000 });
      return response.data;
    } catch (error) {
      const status = error.response?.status;
      const errorMsg = error.response?.data || error.message;

      // If it's a timeout or rate limit, wait and retry (exponential backoff)
      if ((status === 504 || status === 429 || status === 502 || error.code === 'ECONNABORTED') && i < retries - 1) {
        console.log(`  ⚠️ Timeout/Rate Limit (${status || 'Timeout'}). Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= 2;
      } else {
        return null; // Return null if all retries fail or it's a different error
      }
    }
  }
  return null;
}

async function runScraper() {
  console.log("🚀 Starting Ultimate Bzzoiro Scraper (Resilient Mode)...");
  const today = new Date().toISOString().split('T')[0];

  console.log(`🌍 Fetching fixtures for ${today}...`);

  try {
    // Paginate: /events/ doesn't expose a count/next wrapper, so we keep requesting pages
    const PAGE_SIZE = 200;
    let fixtures = [];
    let offset = 0;

    while (true) {
      const url = `https://sports.bzzoiro.com/api/v2/events/?date_from=${today}&date_to=${today}&limit=${PAGE_SIZE}&offset=${offset}`;
      const fixturesData = await fetchWithRetry(url);

      if (!fixturesData) {
        console.error("❌ Failed to fetch fixtures page. Stopping pagination.");
        break;
      }

      const page = extractList(fixturesData);
      fixtures = fixtures.concat(page);

      if (page.length < PAGE_SIZE) break;
      offset += PAGE_SIZE;
    }

    console.log(`📅 Found ${fixtures.length} matches today.`);

    let successCount = 0;

    for (const match of fixtures) {
      // FIX: status enum values are lowercase
      if (match.status === 'cancelled' || match.status === 'postponed') continue;

      const fixtureId = match.id;
      const homeName = match.home_team;
      const awayName = match.away_team;
      const homeId = match.home_team_id;
      const awayId = match.away_team_id;

      console.log(`\n🔍 Scraping: ${homeName} vs ${awayName}...`);

      try {
        // 1. H2H
        const h2hData = await fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${fixtureId}/h2h/`);
        const cleanH2h = h2hData?.recent_matches || h2hData || [];

        // 2. Form: 90-day lookback window to guarantee historical finished matches
        const fetchForm = async (teamId) => {
          const lookback = new Date();
          lookback.setDate(lookback.getDate() - 90);
          const dateFrom = lookback.toISOString().split('T')[0];

          const res = await fetchWithRetry(
            `https://sports.bzzoiro.com/api/v2/teams/${teamId}/fixtures/?date_from=${dateFrom}&date_to=${today}&status=finished&limit=50`
          );
          const allMatches = extractList(res || []);
          return allMatches
            .sort((a, b) => new Date(b.event_date) - new Date(a.event_date)) // most recent first
            .slice(0, 5)
            .map(f => ({
              home_team: f.home_team,
              away_team: f.away_team,
              home_score: f.home_score,
              away_score: f.away_score,
              home_team_id: f.home_team_id,
              away_team_id: f.away_team_id
            }));
        };

        const cleanHomeForm = await fetchForm(homeId);
        const cleanAwayForm = await fetchForm(awayId);

        // 3. Prediction: CatBoost ML prediction
        const predictionData = await fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${fixtureId}/prediction/`);

        // 4. Odds: consensus decimal odds
        const oddsData = await fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${fixtureId}/odds/`);

        // 🆕 5. Lineups & Match Details (For the Ultimate Match Center tabs)
        const lineupsData = await fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${fixtureId}/lineups/`);
        const matchDetails = await fetchWithRetry(`https://sports.bzzoiro.com/api/v2/events/${fixtureId}/`);

        // 6. Save to Supabase
        await supabase.from('match_stats').upsert({
          fixture_id: fixtureId,
          home_team_id: homeId,
          away_team_id: awayId,
          h2h_data: cleanH2h,
          home_form: cleanHomeForm,
          away_form: cleanAwayForm,
          prediction_data: predictionData,
          odds_data: oddsData,
          lineups_data: lineupsData,
          match_details: matchDetails,
          updated_at: new Date()
        });

        console.log(`  ✅ Saved! (H2H: ${cleanH2h.length}, Home Form: ${cleanHomeForm.length}, Away Form: ${cleanAwayForm.length}, Pred: ${predictionData ? 'yes' : 'no'}, Odds: ${oddsData ? 'yes' : 'no'})`);
        successCount++;

        // 🛡️ Polite delay: Random between 1.5s and 2.5s to avoid Cloudflare rate limiting
        const delay = Math.floor(Math.random() * 1000) + 1500;
        await new Promise(resolve => setTimeout(resolve, delay));

      } catch (error) {
        console.error(`  ❌ Failed to process match:`, error.message);
      }
    }

    console.log(`\n🎉 SUCCESS! Saved clean data for ${successCount} matches.`);

  } catch (error) {
    console.error("❌ Fatal API Error:", error.response?.data || error.message);
  }
}

runScraper();