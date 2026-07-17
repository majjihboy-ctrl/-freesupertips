import { useState, useEffect } from 'react';
import { Menu, X, User as UserIcon, LogOut, Crown } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { User } from '@supabase/supabase-js';

interface NavbarProps {
  user: User | null;
  hasPremium: boolean;
  onLogout: () => void;
  onOpenAuth: (mode: 'login' | 'signup') => void;
}

export default function Navbar({ user, hasPremium, onLogout, onOpenAuth }: NavbarProps) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { to: '/', label: 'Today' },
    { to: '/pricing', label: 'VIP Predictions' },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 border-b ${
        isScrolled ? 'bg-bg-base/95 backdrop-blur-sm border-bg-surface-hover' : 'bg-bg-base border-transparent'
      }`}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center gap-1.5">
            <span className="text-2xl font-extrabold text-white">Free</span>
            <span className="text-2xl font-extrabold text-brand-green">SuperTips</span>
          </Link>

          <div className="hidden md:flex items-center space-x-8">
            {navLinks.map(link => (
              <Link key={link.to} to={link.to} className="text-slate-300 hover:text-white font-medium transition-colors">
                {link.label}
              </Link>
            ))}

            {user ? (
              <div className="flex items-center gap-3">
                {hasPremium && (
                  <span className="flex items-center gap-1 text-xs font-bold text-brand-premium bg-brand-premium/10 px-3 py-1.5 rounded-full">
                    <Crown className="w-3.5 h-3.5" /> VIP
                  </span>
                )}
                <span className="flex items-center gap-1.5 text-sm text-slate-300">
                  <UserIcon className="w-4 h-4" /> {user.email?.split('@')[0]}
                </span>
                <button
                  onClick={onLogout}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-full border border-bg-surface-hover text-slate-300 hover:text-white hover:border-slate-500 transition-all text-sm font-semibold"
                >
                  <LogOut className="w-3.5 h-3.5" /> Log out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onOpenAuth('login')}
                  className="px-5 py-2 rounded-full border border-bg-surface-hover text-slate-200 font-semibold hover:border-slate-500 transition-all text-sm"
                >
                  Log In
                </button>
                <button
                  onClick={() => onOpenAuth('signup')}
                  className="px-5 py-2 rounded-full bg-brand-green hover:bg-brand-green-hover text-white font-semibold transition-all text-sm"
                >
                  Sign Up
                </button>
              </div>
            )}
          </div>

          <button className="md:hidden p-2 text-slate-200" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-bg-surface-hover">
            <div className="flex flex-col space-y-4 px-2">
              {navLinks.map(link => (
                <Link
                  key={link.to}
                  to={link.to}
                  className="text-slate-300 hover:text-white font-medium"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}

              {user ? (
                <>
                  <span className="text-sm text-slate-400">{user.email}</span>
                  <button
                    onClick={() => {
                      onLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="w-full px-6 py-2 rounded-full border border-bg-surface-hover text-slate-200 font-semibold"
                  >
                    Log out
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => {
                      onOpenAuth('login');
                      setMobileMenuOpen(false);
                    }}
                    className="w-full px-6 py-2 rounded-full border border-bg-surface-hover text-slate-200 font-semibold"
                  >
                    Log In
                  </button>
                  <button
                    onClick={() => {
                      onOpenAuth('signup');
                      setMobileMenuOpen(false);
                    }}
                    className="w-full px-6 py-2 rounded-full bg-brand-green text-white font-semibold"
                  >
                    Sign Up
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
