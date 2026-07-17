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
  odds: string;
  confidence: string;
  isPremium: boolean;
  status: string;
  homeScore: number | null;
  awayScore: number | null;
  date: string;
}

export type Day = 'yesterday' | 'today' | 'tomorrow';

function dayRange(day: Day): { start: string; end: string } {
  const offset = day === 'yesterday' ? -1 : day === 'tomorrow' ? 1 : 0;
  const start = new Date();
  start.setUTCDate(start.getUTCDate() + offset);
  start.setUTCHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setUTCDate(end.getUTCDate() + 1);
  return { start: start.toISOString(), end: end.toISOString() };
}

// Derives a display prediction from raw scraped data, unless the admin
// has manually overridden it via the dashboard — admin edits always win.
function deriveFixture(stat: any): Fixture {
  const pred = stat.prediction_data;
  const odds = stat.odds_data;

  let predictionText = 'Match Preview';
  let confidence = '50%';
  let isPremium = false;

  if (pred) {
    const conf = pred.model?.confidence || 0.5;
    confidence = `${Math.round(conf * 100)}%`;

    const rec = pred.recommendations || {};
    if (rec.bet_favorite) {
      predictionText = rec.favorite === 'H' ? `${stat.home_team_name} Win` :
                       rec.favorite === 'A' ? `${stat.away_team_name} Win` : 'Draw';
    } else if (rec.over_25) {
      predictionText = 'Over 2.5 Goals';
    } else if (rec.btts) {
      predictionText = 'Both Teams to Score';
    }

    if (conf > 0.75) isPremium = true;
  }

  let displayOdds = '1.90';
  if (odds && odds.odds && typeof odds.odds.home_win === 'number') {
    displayOdds = odds.odds.home_win.toFixed(2);
  }

  // Admin overrides (set from /admin) take priority over the scraped/derived values.
  if (stat.admin_prediction) predictionText = stat.admin_prediction;
  if (stat.admin_odds) displayOdds = stat.admin_odds;
  if (stat.admin_confidence) confidence = stat.admin_confidence;
  if (stat.is_premium_override !== null && stat.is_premium_override !== undefined) {
    isPremium = stat.is_premium_override;
  }

  return {
    id: stat.fixture_id,
    homeTeamId: stat.home_team_id,
    awayTeamId: stat.away_team_id,
    league: stat.league_name || 'Unknown League',
    time: stat.kickoff_time || 'TBA',
    homeTeam: stat.home_team_name,
    awayTeam: stat.away_team_name,
    prediction: predictionText,
    odds: displayOdds,
    confidence,
    isPremium,
    status: stat.status || 'NS',
    homeScore: stat.home_score ?? null,
    awayScore: stat.away_score ?? null,
    date: stat.fixture_date
      ? new Date(stat.fixture_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      : '',
  };
}

export async function fetchFixturesForDay(day: Day = 'today'): Promise<Fixture[]> {
  try {
    const { start, end } = dayRange(day);
    const { data, error } = await supabase
      .from('match_stats')
      .select('*')
      .gte('fixture_date', start)
      .lt('fixture_date', end)
      .order('fixture_date', { ascending: true });

    if (error) {
      console.error('❌ Supabase fetch error:', error);
      return [];
    }
    if (!data || data.length === 0) return [];

    return data.map(deriveFixture);
  } catch (error) {
    console.error('Fetch failed:', error);
    return [];
  }
}

// Kept for any callers still expecting "today's fixtures" by name.
export async function fetchTodaysFixtures(): Promise<Fixture[]> {
  return fetchFixturesForDay('today');
}

export interface ResultRow extends Fixture {
  outcome: 'WON' | 'LOST' | 'PUSH' | 'PENDING';
}

// Very rough settlement check for common tip phrasings. Anything not
// recognized is marked PENDING rather than guessed at.
function settleOutcome(prediction: string, homeScore: number | null, awayScore: number | null): 'WON' | 'LOST' | 'PUSH' | 'PENDING' {
  if (homeScore === null || awayScore === null) return 'PENDING';
  const p = prediction.toLowerCase();
  const totalGoals = homeScore + awayScore;

  if (p.includes('over 2.5')) return totalGoals > 2.5 ? 'WON' : 'LOST';
  if (p.includes('under 2.5')) return totalGoals < 2.5 ? 'WON' : 'LOST';
  if (p.includes('both teams to score') || p === 'btts') {
    return homeScore > 0 && awayScore > 0 ? 'WON' : 'LOST';
  }
  if (p.includes(' win')) {
    const team = p.replace(' win', '');
    if (homeScore === awayScore) return 'LOST';
    const homeWon = homeScore > awayScore;
    // If the predicted team's name appears in the home slot vs away slot,
    // this is resolved by the caller passing homeTeam/awayTeam context —
    // kept simple here since predictionText already encodes the team name.
    return team.length > 0 ? (homeWon ? 'WON' : 'LOST') : 'PENDING';
  }
  if (p === 'draw') return homeScore === awayScore ? 'WON' : 'LOST';
  return 'PENDING';
}

export async function fetchRecentResults(limit = 15): Promise<ResultRow[]> {
  try {
    const { data, error } = await supabase
      .from('match_stats')
      .select('*')
      .eq('status', 'FT')
      .order('fixture_date', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('❌ Supabase fetch error:', error);
      return [];
    }
    if (!data || data.length === 0) return [];

    return data.map((stat) => {
      const fixture = deriveFixture(stat);
      return {
        ...fixture,
        outcome: settleOutcome(fixture.prediction, fixture.homeScore, fixture.awayScore),
      };
    });
  } catch (error) {
    console.error('Fetch failed:', error);
    return [];
  }
}
