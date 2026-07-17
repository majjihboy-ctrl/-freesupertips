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
  onSubmit: (e: React.FormEvent) => void;
  onResend?: () => void;
}

export default function AuthModal({ isOpen, onClose, authMode, setAuthMode, email, setEmail, password, setPassword, authError, onSubmit, onResend }: AuthModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-bg-surface p-8 rounded-2xl border border-bg-surface-hover shadow-2xl w-full max-w-md relative" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 text-slate-400 hover:text-white">✕</button>
        <h2 className="text-2xl font-bold text-white mb-2 text-center">{authMode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
        <p className="text-slate-400 text-sm text-center mb-6">{authMode === 'login' ? 'Log in to save your bet slips.' : 'Join FreeSuperTips today.'}</p>

        <form onSubmit={onSubmit} className="space-y-4">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email address" required className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-green" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required className="w-full bg-bg-base border border-bg-surface-hover rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-green" />
          <button type="submit" className="w-full bg-brand-green hover:bg-brand-green-hover text-white font-bold py-3 rounded-lg transition-colors">
            {authMode === 'login' ? 'Log In' : 'Sign Up'}
          </button>
        </form>

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
      </div>
    </div>
  );
}