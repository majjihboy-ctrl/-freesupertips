import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

export const supabaseAdmin = createClient(
  process.env.VITE_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// How long each plan grants premium access for, in days.
export const PLAN_DURATIONS_DAYS = {
  daily: 1,
  weekly: 7,
  monthly: 30,
};

export async function getMpesaToken() {
  const auth = Buffer.from(`${process.env.MPESA_CONSUMER_KEY}:${process.env.MPESA_CONSUMER_SECRET}`).toString(
    'base64'
  );
  const res = await axios.get('https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', {
    headers: { Authorization: `Basic ${auth}` },
  });
  return res.data.access_token;
}

export function mpesaTimestamp() {
  return new Date().toISOString().replace(/[^0-9]/g, '').slice(0, -3); // YYYYMMDDHHmmss
}

export function mpesaPassword(timestamp) {
  return Buffer.from(process.env.MPESA_SHORTCODE + process.env.MPESA_PASSKEY + timestamp).toString('base64');
}

// Applies a completed payment to the user's premium status. Idempotent:
// if this pending_payments row was already marked completed, it's a no-op
// (Safaricom can retry callbacks, so this must be safe to call twice).
export async function applyCompletedPayment(checkoutRequestId, mpesaReceiptNumber) {
  const { data: payment, error: fetchError } = await supabaseAdmin
    .from('pending_payments')
    .select('*')
    .eq('checkout_request_id', checkoutRequestId)
    .maybeSingle();

  if (fetchError || !payment) {
    console.error('No matching pending_payments row for', checkoutRequestId, fetchError);
    return { ok: false, reason: 'no_matching_payment' };
  }

  if (payment.status === 'completed') {
    return { ok: true, reason: 'already_completed' };
  }

  const durationDays = PLAN_DURATIONS_DAYS[payment.plan] ?? 7;
  const now = new Date();

  // Extend from the later of "now" or their current premium_until, so a
  // renewal before expiry stacks instead of resetting the clock.
  const { data: profile } = await supabaseAdmin
    .from('profiles')
    .select('premium_until')
    .eq('id', payment.user_id)
    .maybeSingle();

  const currentUntil = profile?.premium_until ? new Date(profile.premium_until) : now;
  const base = currentUntil > now ? currentUntil : now;
  const premiumUntil = new Date(base.getTime() + durationDays * 24 * 60 * 60 * 1000);

  const { error: updateError } = await supabaseAdmin
    .from('profiles')
    .update({ is_premium: true, premium_until: premiumUntil.toISOString() })
    .eq('id', payment.user_id);

  if (updateError) {
    console.error('Failed to upgrade user to premium:', updateError);
    return { ok: false, reason: 'profile_update_failed' };
  }

  await supabaseAdmin
    .from('pending_payments')
    .update({ status: 'completed', completed_at: now.toISOString(), mpesa_receipt: mpesaReceiptNumber ?? null })
    .eq('checkout_request_id', checkoutRequestId);

  return { ok: true, userId: payment.user_id, premiumUntil: premiumUntil.toISOString() };
}
