import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    // Supabase's client parses the recovery token out of the URL
    // automatically and fires PASSWORD_RECOVERY once that session is
    // established. Until then, we don't know if this link is valid.
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') setReady(true);
    });

    // If the session was already established before this component
    // mounted (e.g. fast redirect), check directly too.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) setReady(true);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    const { error: updateError } = await supabase.auth.updateUser({ password });
    setSubmitting(false);

    if (updateError) {
      setError(updateError.message);
      return;
    }
    setDone(true);
    setTimeout(() => navigate('/'), 2500);
  };

  return (
    <div className="pt-24 pb-16 min-h-screen flex items-start justify-center">
      <div className="w-full max-w-md px-4 sm:px-6">
        <div className="bg-bg-surface p-8 rounded-2xl border border-bg-surface-hover shadow-2xl">
          <h1 className="text-2xl font-bold text-white mb-2 text-center">Set a New Password</h1>

          {done ? (
            <p className="text-center text-brand-green mt-6">
              ✅ Password updated. Redirecting you to the homepage…
            </p>
          ) : !ready ? (
            <p className="text-center text-slate-400 mt-6">
              Verifying your reset link… If nothing happens within a few seconds, the link may have
              expired — request a new one from the Log In menu.
            </p>
          ) : (
            <>
              <p className="text-slate-400 text-sm text-center mb-6">
                Enter your new password below.
              </p>
              <form onSubmit={handleSubmit} className="space-y-4">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="New password"
                  required
                  className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-green"
                />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  required
                  className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-green"
                />
                {error && <p className="text-brand-danger text-sm text-center">{error}</p>}
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-brand-green hover:bg-brand-green-hover text-white font-bold py-3 rounded-lg transition-colors disabled:opacity-60"
                >
                  {submitting ? 'Updating…' : 'Update Password'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
