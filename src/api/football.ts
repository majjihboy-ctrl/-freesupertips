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
}

export async function fetchTodaysFixtures(): Promise<Fixture[]> {
  try {
    //  Fetch the 109 matches directly from Supabase
    const { data, error } = await supabase
      .from('match_stats')
      .select('*')
      .order('kickoff_time', { ascending: true });

    if (error) {
      console.error("❌ Supabase fetch error:", error);
      return [];
    }

    if (!data || data.length === 0) return [];

    // Map the database rows to the Fixture interface
    return data.map((stat: any) => {
      const pred = stat.prediction_data;
      const odds = stat.odds_data;

      let predictionText = "Match Preview";
      let confidence = "50%";
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

      let displayOdds = "1.90";
      if (odds && odds.odds && typeof odds.odds.home_win === 'number') {
        displayOdds = odds.odds.home_win.toFixed(2);
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
        confidence: confidence,
        isPremium: isPremium
      };
    });

  } catch (error) {
    console.error(" Fetch Failed:", error);
    return [];
  }
}