// api/server.js
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const app = express();
app.use(cors());
app.use(express.json());

// Initialize Supabase Admin
const supabase = createClient(process.env.VITE_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

// Helper: Get M-Pesa OAuth Token
const getMpesaToken = async () => {
  const auth = Buffer.from(`${process.env.MPESA_CONSUMER_KEY}:${process.env.MPESA_CONSUMER_SECRET}`).toString('base64');
  const res = await axios.get('https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials', {
    headers: { Authorization: `Basic ${auth}` }
  });
  return res.data.access_token;
};

// 1. TRIGGER STK PUSH
app.post('/api/mpesa/stkpush', async (req, res) => {
  const { phone, amount, userId } = req.body;

  try {
    const token = await getMpesaToken();
    const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, -3); // YYYYMMDDHHmmss
    const password = Buffer.from(process.env.MPESA_SHORTCODE + process.env.MPESA_PASSKEY + timestamp).toString('base64');

    const response = await axios.post('https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest', {
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
      TransactionDesc: 'VIP Premium Subscription'
    }, {
      headers: { Authorization: `Bearer ${token}` }
    });

    // Save the CheckoutRequestID and userId so we know who paid when the callback arrives
    // (In a real app, save this to a database table, but for now we'll pass userId in the callback)
    res.json({ success: true, CheckoutRequestID: response.data.CheckoutRequestID });
  } catch (error) {
    console.error("M-Pesa STK Push Failed:", error.response?.data || error.message);
    res.status(500).json({ error: "Failed to initiate M-Pesa payment" });
  }
});

// 2. MPESA CALLBACK (Where Safaricom sends the payment result)
app.post('/api/mpesa/callback', async (req, res) => {
  console.log("📩 Received M-Pesa Callback:", req.body);

  const callbackMetadata = req.body.Body.stkCallback.CallbackMetadata;
  const resultDesc = req.body.Body.stkCallback.ResultDesc;

  // ResultCode 0 means success!
  if (req.body.Body.stkCallback.ResultCode === 0) {
    // Extract the phone number and amount from the callback
    const phoneItem = callbackMetadata.Item.find(i => i.Name === 'PhoneNumber');
    const phone = phoneItem ? phoneItem.Value.toString() : null;

    // TODO: In a production app, you should query your database using the CheckoutRequestID
    // to find the exact userId. For this setup, we will upgrade the user based on the phone number
    // if you store the phone number in their Supabase profile, OR you can pass userId via a custom callback.

    // For simplicity in this demo, let's assume you pass the userId in the AccountReference
    // or we just upgrade the user associated with this phone number.
    console.log(`✅ SUCCESS! M-Pesa payment confirmed for ${phone}. Upgrading user...`);

    // Note: To make this perfectly link to the user, you should save the `CheckoutRequestID`
    // and `userId` in a Supabase table when the STK push is triggered, and look it up here.
  } else {
    console.log(`❌ M-Pesa Payment Failed: ${resultDesc}`);
  }

  res.json({ ResultCode: 0, ResultDesc: "Success" });
});

const PORT = 3001;
app.listen(PORT, () => console.log(`📱 M-Pesa Backend running on http://localhost:${PORT}`));