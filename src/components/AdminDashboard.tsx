import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

interface MatchRow {
  fixture_id: number;
  home_team_name: string;
  away_team_name: string;
  league_name: string;
  kickoff_time: string;
  fixture_date: string;
  status: string;
  admin_prediction: string | null;
  admin_odds: string | null;
  admin_confidence: string | null;
  is_premium_override: boolean | null;
}

interface AdminDashboardProps {
  user: User | null;
}

export default function AdminDashboard({ user }: AdminDashboardProps) {
  const navigate = useNavigate();

  const adminEmails = (import.meta.env.VITE_ADMIN_EMAILS || '')
    .split(',')
    .map((e: string) => e.trim().toLowerCase())
    .filter(Boolean);
  const isAdmin = !!user?.email && adminEmails.includes(user.email.toLowerCase());

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

  const fetchMatches = async () => {
    setLoading(true);
    // Today + tomorrow's scraped matches — the ones an admin would actually be curating tips for.
    const { data, error } = await supabase
      .from('match_stats')
      .select('fixture_id, home_team_name, away_team_name, league_name, kickoff_time, fixture_date, status, admin_prediction, admin_odds, admin_confidence, is_premium_override')
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
    if (!window.confirm('Clear the manual override for this match? It will fall back to the auto-generated tip.')) return;
    const { error } = await supabase
      .from('match_stats')
      .update({ admin_prediction: null, admin_odds: null, admin_confidence: null, is_premium_override: null })
      .eq('fixture_id', fixtureId);

    if (error) console.error('Failed to clear override', error);
    else fetchMatches();
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
            Editing a row here overrides the auto-generated prediction for that match on the live site. Leave fields blank to keep the scraper's own tip. Rows come from <code className="text-brand-green">match_stats</code> — the same table <code className="text-brand-green">hybrid-scraper.js</code> writes to.
          </p>
          <input
            type="text"
            placeholder="Search by team name or match ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
          />
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
                        <span className="text-xs text-slate-500 ml-2">#{m.fixture_id} • {m.league_name} • {m.status}</span>
                      </div>
                      {(m.admin_prediction || m.admin_odds || m.admin_confidence) && (
                        <button onClick={() => clearRow(m.fixture_id)} className="text-xs text-slate-500 hover:text-brand-danger">
                          Clear override
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <input
                        type="text"
                        placeholder="Prediction (e.g. Home Win)"
                        value={val('admin_prediction') || ''}
                        onChange={(e) => updateField(m.fixture_id, 'admin_prediction', e.target.value)}
                        className="bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                      />
                      <input
                        type="text"
                        placeholder="Odds (e.g. 1.85)"
                        value={val('admin_odds') || ''}
                        onChange={(e) => updateField(m.fixture_id, 'admin_odds', e.target.value)}
                        className="bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                      />
                      <input
                        type="text"
                        placeholder="Confidence (e.g. 80%)"
                        value={val('admin_confidence') || ''}
                        onChange={(e) => updateField(m.fixture_id, 'admin_confidence', e.target.value)}
                        className="bg-bg-base border border-bg-surface-hover rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-brand-green"
                      />
                      <div className="flex items-center gap-2">
                        <label className="flex items-center gap-2 text-xs text-slate-300">
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
                          className="ml-auto bg-brand-green hover:bg-brand-green-hover disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold px-3 py-2 rounded-lg transition-colors"
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
