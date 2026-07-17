import { getMpesaToken, mpesaTimestamp, mpesaPassword, supabaseAdmin, PLAN_DURATIONS_DAYS, PLAN_PRICES_KES, MPESA_BASE_URL } from '../_lib/mpesa.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { phone, userId, plan } = req.body || {};

  if (!phone || !userId) {
    return res.status(400).json({ error: 'phone and userId are required' });
  }

  const normalizedPlan = plan && PLAN_DURATIONS_DAYS[plan] ? plan : 'weekly';
  // The price is looked up server-side from the plan name — never trust a
  // client-supplied amount, or someone could pay 1 KES for a monthly plan.
  const amount = PLAN_PRICES_KES[normalizedPlan];

  try {
    const token = await getMpesaToken();
    const timestamp = mpesaTimestamp();
    const password = mpesaPassword(timestamp);

    const axios = (await import('axios')).default;
    const response = await axios.post(
      `${MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest`,
      {
        BusinessShortCode: process.env.MPESA_SHORTCODE,
        Password: password,
        Timestamp: timestamp,
        TransactionType: 'CustomerPayBillOnline',
        Amount: amount,
        PartyA: phone,
        PartyB: process.env.MPESA_SHORTCODE,
        PhoneNumber: phone,
        CallBackURL: process.env.MPESA_CALLBACK_URL,
        AccountReference: 'FreeSuperTips',
        TransactionDesc: `${normalizedPlan} VIP subscription`,
      },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    const checkoutRequestId = response.data.CheckoutRequestID;

    // Persist WHO is paying against THIS specific checkout request, so the
    // callback (which only gets phone/amount/CheckoutRequestID back from
    // Safaricom) can look up the right user and actually grant premium.
    const { error: insertError } = await supabaseAdmin.from('pending_payments').insert({
      checkout_request_id: checkoutRequestId,
      user_id: userId,
      amount,
      plan: normalizedPlan,
      status: 'pending',
    });

    if (insertError) {
      console.error('Failed to record pending payment:', insertError);
      // The STK push already went out to the user's phone at this point —
      // we still return success so they aren't left confused mid-payment,
      // but log loudly since the callback won't be able to link this one.
    }

    return res.status(200).json({ success: true, CheckoutRequestID: checkoutRequestId });
  } catch (error) {
    console.error('M-Pesa STK Push failed:', error.response?.data || error.message);
    return res.status(500).json({ error: 'Failed to initiate M-Pesa payment' });
  }
}
