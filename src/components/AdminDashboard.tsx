import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { isAdminEmail } from '../lib/adminEmails';

interface MatchRow {
  fixture_id: number;
  home_team_name: string;
  away_team_name: string;
  league_name: string;
  kickoff_time: string;
  fixture_date: string;
  status: string;
  admin_prediction: string | null;
  is_premium_override: boolean | null;
}

interface AdminDashboardProps {
  user: User | null;
}

// Always an admin regardless of whether VITE_ADMIN_EMAILS is configured
// correctly in the current environment — this account should never get
// accidentally locked out by a missing/misconfigured env var.
export default function AdminDashboard({ user }: AdminDashboardProps) {
  const navigate = useNavigate();
  const isAdmin = isAdminEmail(user?.email);

  useEffect(() => {
    if (user === null) return; // still loading initial session
    if (!isAdmin) navigate('/');
  }, [user, isAdmin, navigate]);

  if (!isAdmin) {
    return (
      <div className="pt-32 pb-16 text-center text-slate-400">
        <p>Checking access…</p>
      </div>
    );
  }

  return <AdminDashboardContent user={user} navigate={navigate} />;
}

function AdminDashboardContent({ user, navigate }: { user: User | null; navigate: (path: string) => void }) {
  const [matches, setMatches] = useState<MatchRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<Record<number, Partial<MatchRow>>>({});
  const [message, setMessage] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newMatch, setNewMatch] = useState({ home: '', away: '', league: '', kickoff: '' });
  const [adding, setAdding] = useState(false);

  const fetchMatches = async () => {
    setLoading(true);
    // Today + tomorrow's scraped matches — the ones an admin would actually be curating tips for.
    const { data, error } = await supabase
      .from('match_stats')
      .select('fixture_id, home_team_name, away_team_name, league_name, kickoff_time, fixture_date, status, admin_prediction, is_premium_override')
      .order('fixture_date', { ascending: true })
      .limit(200);

    if (error) {
      console.error('Error fetching match_stats:', error);
      setMessage('❌ Failed to load matches: ' + error.message);
    } else {
      setMatches(data || []);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchMatches();
  }, []);

  const updateField = (fixtureId: number, field: keyof MatchRow, value: string | boolean) => {
    setEditing((prev) => ({ ...prev, [fixtureId]: { ...prev[fixtureId], [field]: value } }));
  };

  const saveRow = async (fixtureId: number) => {
    const changes = editing[fixtureId];
    if (!changes) return;

    const { error } = await supabase.from('match_stats').update(changes).eq('fixture_id', fixtureId);

    if (error) {
      setMessage('❌ Failed to save: ' + error.message);
    } else {
      setMessage(`✅ Saved tip for match ${fixtureId}`);
      setEditing((prev) => {
        const next = { ...prev };
        delete next[fixtureId];
        return next;
      });
      fetchMatches();
    }
  };

  const clearRow = async (fixtureId: number) => {
    if (!window.confirm('Remove the tip for this match? It will disappear from the live site until you enter a new one.')) return;
    const { error } = await supabase
      .from('match_stats')
      .update({ admin_prediction: null, is_premium_override: null })
      .eq('fixture_id', fixtureId);

    if (error) console.error('Failed to clear tip', error);
    else fetchMatches();
  };

  // Manually-added matches (Bzzoiro doesn't cover everything) get a
  // negative fixture_id, guaranteed never to collide with a real
  // Bzzoiro event ID (always positive). Finds the current lowest
  // negative ID in use and goes one further, rather than deriving from
  // a timestamp — safe regardless of whether the column is a 4-byte or
  // 8-byte integer.
  const handleAddMatch = async () => {
    if (!newMatch.home.trim() || !newMatch.away.trim() || !newMatch.kickoff) {
      setMessage('❌ Home team, away team, and kickoff time are all required.');
      return;
    }
    setAdding(true);

    const { data: minRow } = await supabase
      .from('match_stats')
      .select('fixture_id')
      .lt('fixture_id', 0)
      .order('fixture_id', { ascending: true })
      .limit(1);

    const newId = (minRow?.[0]?.fixture_id ?? 0) - 1;
    const kickoffDate = new Date(newMatch.kickoff);

    const { error } = await supabase.from('match_stats').insert({
      fixture_id: newId,
      home_team_name: newMatch.home.trim(),
      away_team_name: newMatch.away.trim(),
      league_name: newMatch.league.trim() || 'Other',
      kickoff_time: kickoffDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
      fixture_date: kickoffDate.toISOString(),
      status: 'notstarted',
    });

    setAdding(false);

    if (error) {
      setMessage('❌ Failed to add match: ' + error.message);
    } else {
      setMessage(`✅ Added ${newMatch.home} vs ${newMatch.away} — now enter a tip for it below.`);
      setNewMatch({ home: '', away: '', league: '', kickoff: '' });
      setShowAddForm(false);
      fetchMatches();
    }
  };

  const filtered = matches.filter((m) => {
    const q = search.toLowerCase();
    return !q || m.home_team_name?.toLowerCase().includes(q) || m.away_team_name?.toLowerCase().includes(q) || String(m.fixture_id).includes(q);
  });

  return (
    <div className="min-h-screen bg-bg-base p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">⚙️ Admin Dashboard</h1>
            <p className="text-slate-400 text-sm mt-1">
              Logged in as: <span className="text-brand-green font-bold">{user?.email}</span>
            </p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="bg-bg-surface hover:bg-bg-surface-hover text-white px-4 py-2 rounded-lg border border-bg-surface-hover transition-colors"
          >
            ← Back to Site
          </button>
        </div>

        <div className="bg-bg-surface p-4 rounded-2xl border border-bg-surface-hover mb-6">
          <p className="text-xs text-slate-400 mb-3">
            Enter a tip here to publish it on the live site. Matches only appear on the homepage once you've entered a prediction for them — nothing is shown automatically. Rows come from <code className="text-brand-green">match_stats</code>, populated by <code className="text-brand-green">hybrid-scraper.js</code> (Bzzoiro fixtures, kickoff times, and final scores only — not tips).
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Search by team name or match ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
            />
            <button
              onClick={() => setShowAddForm((v) => !v)}
              className="bg-brand-green/10 hover:bg-brand-green/20 text-brand-green font-bold text-sm px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
            >
              {showAddForm ? '✕ Cancel' : '+ Add Match'}
            </button>
          </div>

          {showAddForm && (
            <div className="mt-4 pt-4 border-t border-bg-surface-hover">
              <p className="text-xs text-slate-400 mb-3">
                For any match Bzzoiro doesn't cover — its match coverage is narrower than a full global sweep, so use this for anything missing.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <input
                  type="text"
                  placeholder="Home team"
                  value={newMatch.home}
                  onChange={(e) => setNewMatch((p) => ({ ...p, home: e.target.value }))}
                  className="bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                />
                <input
                  type="text"
                  placeholder="Away team"
                  value={newMatch.away}
                  onChange={(e) => setNewMatch((p) => ({ ...p, away: e.target.value }))}
                  className="bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                />
                <input
                  type="text"
                  placeholder="League (optional)"
                  value={newMatch.league}
                  onChange={(e) => setNewMatch((p) => ({ ...p, league: e.target.value }))}
                  className="bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                />
                <input
                  type="datetime-local"
                  value={newMatch.kickoff}
                  onChange={(e) => setNewMatch((p) => ({ ...p, kickoff: e.target.value }))}
                  className="bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                />
              </div>
              <button
                onClick={handleAddMatch}
                disabled={adding}
                className="bg-brand-green hover:bg-brand-green-hover disabled:opacity-40 text-white font-bold text-sm px-4 py-2 rounded-lg transition-colors"
              >
                {adding ? 'Adding…' : 'Add Match'}
              </button>
            </div>
          )}
        </div>

        {message && <p className="text-sm mb-4 text-brand-green">{message}</p>}

        <div className="bg-bg-surface rounded-2xl border border-bg-surface-hover overflow-hidden">
          <div className="p-4 border-b border-bg-surface-hover bg-bg-base/50">
            <h2 className="text-lg font-bold text-white">📋 Matches ({filtered.length})</h2>
          </div>

          <div className="divide-y divide-bg-surface-hover max-h-[70vh] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center text-slate-500">Loading…</div>
            ) : filtered.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                No matches found. Run <code>node hybrid-scraper.js</code> to populate match_stats.
              </div>
            ) : (
              filtered.map((m) => {
                const draft = editing[m.fixture_id] || {};
                const val = (field: keyof MatchRow) => (draft[field] !== undefined ? draft[field] : m[field]) as string | null;
                const hasChanges = !!editing[m.fixture_id];

                return (
                  <div key={m.fixture_id} className="p-4 hover:bg-bg-base/50 transition-colors">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <span className="font-bold text-white">{m.home_team_name} vs {m.away_team_name}</span>
                        <span className="text-xs text-slate-500 ml-2">
                          #{m.fixture_id} • {m.league_name} • {m.status || '⚠️ no status (re-scrape needed)'}
                          {m.fixture_id < 0 && <span className="text-brand-premium ml-1">• Manually Added</span>}
                        </span>
                      </div>
                      {m.admin_prediction && (
                        <button onClick={() => clearRow(m.fixture_id)} className="text-xs text-slate-500 hover:text-brand-danger">
                          Remove tip
                        </button>
                      )}
                    </div>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <input
                        type="text"
                        placeholder="Tip (e.g. Arsenal to Win, Over 2.5 Goals, BTTS)"
                        value={val('admin_prediction') || ''}
                        onChange={(e) => updateField(m.fixture_id, 'admin_prediction', e.target.value)}
                        className="flex-1 bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                      />
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 text-xs text-slate-300 whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={!!(draft.is_premium_override ?? m.is_premium_override)}
                            onChange={(e) => updateField(m.fixture_id, 'is_premium_override', e.target.checked)}
                            className="rounded bg-bg-base border-slate-600 text-brand-green focus:ring-brand-green"
                          />
                          VIP only
                        </label>
                        <button
                          onClick={() => saveRow(m.fixture_id)}
                          disabled={!hasChanges}
                          className="bg-brand-green hover:bg-brand-green-hover disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
