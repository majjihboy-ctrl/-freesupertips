import LegalPage from './LegalPage';

export default function RefundPage() {
  return (
    <LegalPage title="Refund Policy">
      <h2>General Policy</h2>
      <p>
        VIP subscription payments made via M-Pesa are generally non-refundable once access to
        premium predictions has been granted, since the digital content is delivered immediately
        upon successful payment.
      </p>

      <h2>Exceptions</h2>
      <p>You may be eligible for a refund if:</p>
      <p>
        • You were charged but never received VIP access due to a technical error on our end, and
        the issue could not be resolved within 24 hours of contacting support.
        <br />
        • You were double-charged for the same subscription period due to a payment processing
        error.
      </p>

      <h2>How to Request a Refund</h2>
      <p>
        Contact us via the{' '}
        <a href="/contact" className="text-brand-green hover:underline">Contact page</a> within 48
        hours of the payment, including your M-Pesa transaction code (found in the confirmation SMS
        from Safaricom) and the phone number used. We aim to review all requests within 3 business
        days.
      </p>

      <h2>What's Not Covered</h2>
      <p>
        Refunds are not provided for dissatisfaction with prediction outcomes, changed betting
        decisions, or partial use of a subscription period.
      </p>
    </LegalPage>
  );
}
