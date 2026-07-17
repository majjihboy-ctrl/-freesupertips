import { applyCompletedPayment } from '../_lib/mpesa.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const stkCallback = req.body?.Body?.stkCallback;

  if (!stkCallback) {
    console.error('Malformed M-Pesa callback payload:', req.body);
    return res.status(200).json({ ResultCode: 0, ResultDesc: 'Received' }); // ack anyway to stop retries
  }

  const { CheckoutRequestID, ResultCode, ResultDesc, CallbackMetadata } = stkCallback;

  if (ResultCode === 0) {
    const items = CallbackMetadata?.Item ?? [];
    const receiptItem = items.find(i => i.Name === 'MpesaReceiptNumber');
    const mpesaReceiptNumber = receiptItem ? receiptItem.Value : null;

    const result = await applyCompletedPayment(CheckoutRequestID, mpesaReceiptNumber);

    if (result.ok) {
      console.log(`✅ Premium granted to user ${result.userId ?? '(already processed)'} until ${result.premiumUntil ?? 'n/a'}`);
    } else {
      console.error(`❌ Could not apply payment for ${CheckoutRequestID}: ${result.reason}`);
    }
  } else {
    console.log(`❌ M-Pesa payment failed for ${CheckoutRequestID}: ${ResultDesc}`);
  }

  // Always acknowledge — Safaricom retries on non-200/malformed responses.
  return res.status(200).json({ ResultCode: 0, ResultDesc: 'Success' });
}
