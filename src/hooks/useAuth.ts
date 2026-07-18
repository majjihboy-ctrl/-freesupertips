import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import type { User } from '@supabase/supabase-js';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    if (authMode === 'login') {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) setAuthError(error.message);
      else setShowAuthModal(false);
    } else {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: window.location.origin },
      });
      if (error) setAuthError(error.message);
      else setAuthError('✅ Check your email for the confirmation link! (Check spam too — see note below if nothing arrives.)');
    }
  };

  const resendConfirmation = async () => {
    setAuthError('');
    const { error } = await supabase.auth.resend({
      type: 'signup',
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) setAuthError(error.message);
    else setAuthError('✅ Confirmation email resent.');
  };

  const requestPasswordReset = async (resetEmail: string) => {
    setAuthError('');
    const { error } = await supabase.auth.resetPasswordForEmail(resetEmail, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) {
      setAuthError(error.message);
      return false;
    }
    setAuthError('✅ Check your email for a password reset link. (Check spam too if it takes a few minutes.)');
    return true;
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return {
    user, showAuthModal, setShowAuthModal, authMode, setAuthMode,
    email, setEmail, password, setPassword, authError, setAuthError, handleLogin, handleLogout, resendConfirmation, requestPasswordReset
  };
}