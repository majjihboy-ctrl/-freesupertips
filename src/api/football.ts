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

// Predictions are entered manually by the admin after the scraper
// populates fixtures — there is no auto-derived odds/probability model
// on the live site. A fixture only appears once an admin has actually
// set a tip for it.
function deriveFixture(stat: any): Fixture {
  return {
    id: stat.fixture_id,
    homeTeamId: stat.home_team_id,
    awayTeamId: stat.away_team_id,
    league: stat.league_name || 'Unknown League',
    time: stat.kickoff_time || 'TBA',
    homeTeam: stat.home_team_name,
    awayTeam: stat.away_team_name,
    prediction: stat.admin_prediction,
    isPremium: stat.is_premium_override ?? false,
    status: stat.status || 'NS',
    homeScore: stat.home_score ?? null,
    awayScore: stat.away_score ?? null,
    date: stat.fixture_date
      ? new Date(stat.fixture_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      : '',
  };
}

// All upcoming fixtures an admin has manually entered a tip for, soonest
// kickoff first. No day-window filtering — this always reflects whatever
// is currently on the board.
export async function fetchUpcomingFixtures(): Promise<Fixture[]> {
  try {
    const { data, error } = await supabase
      .from('match_stats')
      .select('*')
      .not('admin_prediction', 'is', null)
      .neq('status', 'FT')
      .order('fixture_date', { ascending: true })
      .limit(100);

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
    const homeWon = homeScore > awayScore;
    if (homeScore === awayScore) return 'LOST';
    return homeWon ? 'WON' : 'LOST'; // predictionText already encodes which team
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
      .not('admin_prediction', 'is', null)
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
