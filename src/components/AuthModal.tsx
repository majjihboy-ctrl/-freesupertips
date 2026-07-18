import { useState } from 'react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  authMode: 'login' | 'signup';
  setAuthMode: (mode: 'login' | 'signup') => void;
  email: string;
  setEmail: (email: string) => void;
  password: string;
  setPassword: (password: string) => void;
  authError: string;
  setAuthError?: (msg: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onResend?: () => void;
  onForgotPassword?: (email: string) => Promise<boolean>;
}

export default function AuthModal({
  isOpen, onClose, authMode, setAuthMode, email, setEmail, password, setPassword,
  authError, setAuthError, onSubmit, onResend, onForgotPassword,
}: AuthModalProps) {
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSubmitting, setForgotSubmitting] = useState(false);

  if (!isOpen) return null;

  const closeAndReset = () => {
    setShowForgot(false);
    onClose();
  };

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onForgotPassword) return;
    setForgotSubmitting(true);
    await onForgotPassword(forgotEmail);
    setForgotSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={closeAndReset}>
      <div className="bg-bg-surface p-8 rounded-2xl border border-bg-surface-hover shadow-2xl w-full max-w-md relative" onClick={(e) => e.stopPropagation()}>
        <button onClick={closeAndReset} className="absolute top-4 right-4 text-slate-400 hover:text-white">✕</button>

        {showForgot ? (
          <>
            <h2 className="text-2xl font-bold text-white mb-2 text-center">Reset Password</h2>
            <p className="text-slate-400 text-sm text-center mb-6">
              Enter your email and we'll send you a link to reset your password.
            </p>
            <form onSubmit={handleForgotSubmit} className="space-y-4">
              <input
                type="email"
                value={forgotEmail}
                onChange={(e) => setForgotEmail(e.target.value)}
                placeholder="Email address"
                required
                className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-green"
              />
              <button
                type="submit"
                disabled={forgotSubmitting}
                className="w-full bg-brand-green hover:bg-brand-green-hover text-white font-bold py-3 rounded-lg transition-colors disabled:opacity-60"
              >
                {forgotSubmitting ? 'Sending…' : 'Send Reset Link'}
              </button>
            </form>
            {authError && <p className="text-center text-sm mt-4 text-brand-danger">{authError}</p>}
            <p className="text-center text-sm text-slate-400 mt-6">
              <button
                onClick={() => { setShowForgot(false); setAuthError?.(''); }}
                className="text-brand-green hover:underline font-bold"
              >
                ← Back to Log In
              </button>
            </p>
          </>
        ) : (
          <>
            <h2 className="text-2xl font-bold text-white mb-2 text-center">{authMode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
            <p className="text-slate-400 text-sm text-center mb-6">{authMode === 'login' ? 'Log in to save your bet slips.' : 'Join FreeSuperTips today.'}</p>

            <form onSubmit={onSubmit} className="space-y-4">
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email address" required className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-green" />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-green" />
              <button type="submit" className="w-full bg-brand-green hover:bg-brand-green-hover text-white font-bold py-3 rounded-lg transition-colors">
                {authMode === 'login' ? 'Log In' : 'Sign Up'}
              </button>
            </form>

            {authMode === 'login' && onForgotPassword && (
              <p className="text-center mt-3">
                <button
                  onClick={() => { setForgotEmail(email); setShowForgot(true); setAuthError?.(''); }}
                  className="text-sm text-slate-400 hover:text-brand-green hover:underline"
                >
                  Forgot password?
                </button>
              </p>
            )}

            {authError && (
              <div className="text-center text-sm mt-4">
                <p className="text-brand-danger">{authError}</p>
                {authMode === 'signup' && authError.includes('Check your email') && onResend && (
                  <button onClick={onResend} className="text-brand-green hover:underline font-bold mt-2">
                    Didn't get it? Resend email
                  </button>
                )}
              </div>
            )}

            <p className="text-center text-sm text-slate-400 mt-6">
              {authMode === 'login' ? "Don't have an account? " : "Already have an account? "}
              <button onClick={() => { setAuthMode(authMode === 'login' ? 'signup' : 'login'); }} className="text-brand-green hover:underline font-bold">
                {authMode === 'login' ? 'Sign Up' : 'Log In'}
              </button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
