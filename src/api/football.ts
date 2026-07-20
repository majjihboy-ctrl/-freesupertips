// src/api/football.ts
import { supabase } from '../lib/supabase';

export interface Fixture {
  id: number;
  homeTeamId: number;
  awayTeamId: number;
  league: string;
  time: string;
  homeTeam: string;
  awayTeam: string;
  prediction: string;
  isPremium: boolean;
  status: string;
  homeScore: number | null;
  awayScore: number | null;
  date: string;
}

// PostgREST returns jsonb columns as native JS objects/arrays via
// supabase-js — but if this column was ever created/altered as plain
// `text` instead of `jsonb`, the same value comes back as a raw JSON
// string instead. Handle both so a column-type mismatch can't silently
// make every prediction look empty.
function safeJsonField(value: any): any {
  if (value === null || value === undefined) return null;
  if (typeof value === 'object') return value; // already parsed (jsonb)
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  }
  return null;
}

// Turns Bzzoiro's CatBoost prediction payload into a human-readable tip.
// Mirrors the shape confirmed in Bzzoiro's own API docs:
// recommendations: { bet_favorite, favorite: "H"|"A"|"D", favorite_prob,
//                     over_15, over_25, over_35, btts, winner }
export function derivePredictionFromBzzoiro(predictionDataRaw: any, homeTeam: string, awayTeam: string): string | null {
  const predictionData = safeJsonField(predictionDataRaw);
  const rec = predictionData?.recommendations;
  if (!rec) return null;

  if (rec.bet_favorite && rec.favorite) {
    if (rec.favorite === 'H') return `${homeTeam} to Win`;
    if (rec.favorite === 'A') return `${awayTeam} to Win`;
    if (rec.favorite === 'D') return 'Draw';
  }
  if (rec.over_25) return 'Over 2.5 Goals';
  if (rec.btts) return 'Both Teams to Score';
  if (rec.over_15) return 'Over 1.5 Goals';

  return null;
}

// An admin-entered tip always wins if one exists (lets you correct or
// customize any pick). Otherwise, Bzzoiro's own prediction is used
// automatically — no admin action needed for matches Bzzoiro covers.
function deriveFixture(stat: any): Fixture {
  const prediction = stat.admin_prediction || derivePredictionFromBzzoiro(stat.prediction_data, stat.home_team_name, stat.away_team_name);

  return {
    id: stat.fixture_id,
    homeTeamId: stat.home_team_id,
    awayTeamId: stat.away_team_id,
    league: stat.league_name || 'Unknown League',
    time: stat.kickoff_time || 'TBA',
    homeTeam: stat.home_team_name,
    awayTeam: stat.away_team_name,
    prediction: prediction || '',
    isPremium: stat.is_premium_override ?? false,
    status: stat.status || 'notstarted',
    homeScore: stat.home_score ?? null,
    awayScore: stat.away_score ?? null,
    date: stat.fixture_date
      ? new Date(stat.fixture_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      : '',
  };
}

// All upcoming fixtures with a tip — either Bzzoiro's own auto-generated
// prediction, or an admin override/manually-added match. No day-window
// filtering — this always reflects whatever is currently on the board.
//
// NOTE: whether a row has a usable prediction is decided CLIENT-SIDE
// (after deriveFixture), not via a database filter. Chaining multiple
// .or() calls to check both admin_prediction and prediction_data at the
// DB level adds a layer of PostgREST filter-combination behavior that's
// easy to get subtly wrong; filtering the already-small result set in
// JS after fetching is simpler and impossible to get wrong the same way.
export async function fetchUpcomingFixtures(): Promise<Fixture[]> {
  try {
    const { data, error } = await supabase
      .from('match_stats')
      // Bzzoiro's status enum is 'finished' / 'notstarted' / 'cancelled' /
      // '1st_half' / etc — NOT API-Football's 'FT'/'NS'. A plain
      // .neq('status', 'finished') would ALSO silently drop any row
      // where status is NULL (NULL <> 'finished' evaluates to NULL, not
      // true, in SQL). Explicitly include NULL alongside anything that
      // isn't finished or cancelled.
      .select('*')
      .or('status.is.null,status.not.in.(finished,cancelled,canceled)')
      .order('fixture_date', { ascending: true })
      .limit(300);

    if (error) {
      console.error('❌ Supabase fetch error:', error);
      return [];
    }
    if (!data || data.length === 0) return [];

    return data.map(deriveFixture).filter((f) => f.prediction); // drop anything that still ended up with no usable tip
  } catch (error) {
    console.error('Fetch failed:', error);
    return [];
  }
}

export interface ResultRow extends Fixture {
  outcome: 'WON' | 'LOST' | 'PUSH' | 'PENDING';
}

// Very rough settlement check for common tip phrasings. Anything not
// recognized is marked PENDING rather than guessed at.
function settleOutcome(
  prediction: string,
  homeTeam: string,
  awayTeam: string,
  homeScore: number | null,
  awayScore: number | null
): 'WON' | 'LOST' | 'PUSH' | 'PENDING' {
  if (homeScore === null || awayScore === null) return 'PENDING';
  const p = prediction.toLowerCase();
  const totalGoals = homeScore + awayScore;

  if (p.includes('over 2.5')) return totalGoals > 2.5 ? 'WON' : 'LOST';
  if (p.includes('under 2.5')) return totalGoals < 2.5 ? 'WON' : 'LOST';
  if (p.includes('over 1.5')) return totalGoals > 1.5 ? 'WON' : 'LOST';
  if (p.includes('both teams to score') || p === 'btts') {
    return homeScore > 0 && awayScore > 0 ? 'WON' : 'LOST';
  }
  if (p.includes(' win')) {
    if (homeScore === awayScore) return 'LOST'; // a "win" tip never pushes on a draw
    const homeWon = homeScore > awayScore;
    // Which side did the tip actually pick? Check which team's name
    // appears in the prediction text — don't just assume "home" won.
    const pickedHome = p.includes(homeTeam.toLowerCase());
    const pickedAway = p.includes(awayTeam.toLowerCase());
    if (pickedHome && !pickedAway) return homeWon ? 'WON' : 'LOST';
    if (pickedAway && !pickedHome) return homeWon ? 'LOST' : 'WON';
    return 'PENDING'; // couldn't tell which team the tip was for
  }
  if (p === 'draw') return homeScore === awayScore ? 'WON' : 'LOST';
  return 'PENDING';
}

export async function fetchRecentResults(limit = 15): Promise<ResultRow[]> {
  try {
    const { data, error } = await supabase
      .from('match_stats')
      .select('*')
      .eq('status', 'finished')
      .order('fixture_date', { ascending: false })
      .limit(limit * 5); // over-fetch since most finished rows won't have a usable tip after deriving

    if (error) {
      console.error('❌ Supabase fetch error:', error);
      return [];
    }
    if (!data || data.length === 0) return [];

    return data
      .map(deriveFixture)
      .filter((f) => f.prediction)
      .slice(0, limit)
      .map((fixture) => ({
        ...fixture,
        outcome: settleOutcome(fixture.prediction, fixture.homeTeam, fixture.awayTeam, fixture.homeScore, fixture.awayScore),
      }));
  } catch (error) {
    console.error('Fetch failed:', error);
    return [];
  }
}
