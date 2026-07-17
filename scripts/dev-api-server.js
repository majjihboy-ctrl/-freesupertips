// Local development only. On Vercel, each file in /api/mpesa is deployed
// directly as its own serverless function — this file is never used in
// production. It exists so `npm run dev` gives you a working /api/mpesa/*
// locally without needing the Vercel CLI, using the exact same handler
// code that ships to production (no logic duplicated/out of sync).
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import stkpushHandler from '../api/mpesa/stkpush.js';
import callbackHandler from '../api/mpesa/callback.js';

const app = express();
app.use(cors());
app.use(express.json());

const adapt = handler => (req, res) => handler(req, res);

app.post('/api/mpesa/stkpush', adapt(stkpushHandler));
app.post('/api/mpesa/callback', adapt(callbackHandler));

const PORT = process.env.API_PORT || 3001;
app.listen(PORT, () => console.log(`📱 M-Pesa local dev API running on http://localhost:${PORT}`));
