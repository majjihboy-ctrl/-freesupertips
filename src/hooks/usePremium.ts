import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

export function usePremium(userId: string | null) {
  const [hasPremium, setHasPremium] = useState(false);

  const fetchPremiumStatus = async (id: string) => {
    const { data, error } = await supabase
      .from('profiles')
      .select('is_premium')
      .eq('id', id)
      .maybeSingle(); // <-- This is the magic fix!

    if (!error && data) {
      setHasPremium(data.is_premium);
    } else {
      setHasPremium(false);
    }
  };

  useEffect(() => {
    if (userId) fetchPremiumStatus(userId);
    else setHasPremium(false);
  }, [userId]);

    const handleUpgradeToPremium = async (onShowAuth: () => void) => {
    if (!userId) {
      onShowAuth();
      return;
    }

    // Defaulting to the Weekly Plan (500 KES) from the Navbar
    const amount = 500;

    const phone = prompt(`Enter your M-Pesa Phone Number for Weekly VIP (${amount} KES):`);
    if (!phone) return;
    if (!phone.startsWith('254') || phone.length !== 12) {
      alert("Please enter a valid phone number in the format 2547XXXXXXXX");
      return;
    }
    try {
      const res = await fetch('/api/mpesa/stkpush', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, amount, userId }), // <-- Now passing the dynamic amount!
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ Check your phone! Enter M-Pesa PIN to pay ${amount} KES.`);
        setTimeout(() => window.location.reload(), 30000);
      } else {
        alert("❌ Failed to initiate M-Pesa. Please try again.");
      }
    } catch (error) {
      console.error("M-Pesa Error:", error);
    }
  };

  return { hasPremium, handleUpgradeToPremium };
}