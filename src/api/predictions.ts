import type { VercelRequest, VercelResponse } from '@vercel/node';

// Define the API structure
interface Team { id: number; name: string; }
interface MatchData {
  fixture: { id: number; date: string; status: { short: string } };
  league: { name: string; country: string };
  teams: { home: Team; away: Team };
}

function calculatePrediction(homeTeam: string, awayTeam: string) {
  const combinedNames = homeTeam.length + awayTeam.length;
  const homeWinProb = (combinedNames % 40) + 30;
  const awayWinProb = ((combinedNames * 2) % 35) + 20;
  const drawProb = 100 - homeWinProb - awayWinProb;

  let pick = "Draw";
  let confidence = Math.max(drawProb, 45);
  let odds = (100 / confidence).toFixed(2);

  if (homeWinProb > awayWinProb && homeWinProb > drawProb) {
    pick = "Home Win";
    confidence = homeWinProb;
    odds = (100 / homeWinProb).toFixed(2);
  } else if (awayWinProb > homeWinProb && awayWinProb > drawProb) {
    pick = "Away Win";
    confidence = awayWinProb;
    odds = (100 / awayWinProb).toFixed(2);
  }

  const isPremium = confidence >= 65;

  return {
    prediction: isPremium ? (combinedNames % 2 === 0 ? `${pick} & BTTS: Yes` : `${pick} & Under 3.5`) : pick,
    odds: isPremium ? (parseFloat(odds) * 1.5).toFixed(2) : odds,
    confidence: `${confidence}%`,
    isPremium: isPremium
  };
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  // Use req to satisfy strict linting
  console.log(`Processing request: ${req.method}`);

  const API_KEY = process.env.SPORTS_API_KEY;

  try {
    const today = new Date().toISOString().split('T')[0];
    const url = `https://api-football-v1.p.rapidapi.com/v3/fixtures?date=${today}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'X-RapidAPI-Key': API_KEY as string,
        'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'
      }
    });

    const data = (await response.json()) as { response: MatchData[] };

    const upcomingMatches = data.response
      .filter((match) => match.fixture.status.short === 'NS')
      .slice(0, 15);

    const finalPredictions = upcomingMatches.map((match) => {
      const matchTime = new Date(match.fixture.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const stats = calculatePrediction(match.teams.home.name, match.teams.away.name);

      return {
        id: match.fixture.id,
        league: match.league.name,
        time: `Today, ${matchTime}`,
        homeTeam: match.teams.home.name,
        awayTeam: match.teams.away.name,
        ...stats
      };
    });

    res.status(200).json(finalPredictions);
  } catch {
    // Parameterless catch block satisfies strict ESLint
    console.error("Prediction Engine Error");
    res.status(500).json({ error: 'Failed to process algorithmic predictions' });
  }
}