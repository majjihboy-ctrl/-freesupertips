import LegalPage from './LegalPage';

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service">
      <p>
        By accessing or using FreeSuperTips ("the Site"), you agree to be bound by these Terms of
        Service. If you do not agree, please do not use the Site.
      </p>

      <h2>1. Nature of the Service</h2>
      <p>
        FreeSuperTips provides football predictions and betting tips for informational and
        entertainment purposes only. Predictions are generated from statistical models and publicly
        available data. They are opinions, not guarantees, and no prediction — free or VIP — carries
        any assurance of accuracy or profit.
      </p>

      <h2>2. Age Requirement</h2>
      <p>
        You must be at least 18 years old (or the legal gambling age in your jurisdiction, if
        higher) to use this Site or purchase a VIP subscription.
      </p>

      <h2>3. VIP Subscriptions</h2>
      <p>
        VIP subscriptions are paid via M-Pesa and grant access to premium predictions for the
        duration of the plan purchased (daily, weekly, or monthly). Subscriptions do not
        auto-renew; you must manually purchase a new plan once yours expires. See our{' '}
        <a href="/refund" className="text-brand-green hover:underline">Refund Policy</a> for details
        on cancellations.
      </p>

      <h2>4. No Financial Advice</h2>
      <p>
        Nothing on this Site constitutes financial, investment, or betting advice. You are solely
        responsible for any betting decisions and their outcomes. Please gamble responsibly.
      </p>

      <h2>5. Account Responsibility</h2>
      <p>
        You are responsible for maintaining the confidentiality of your account credentials and for
        all activity that occurs under your account.
      </p>

      <h2>6. Changes to These Terms</h2>
      <p>
        We may update these Terms from time to time. Continued use of the Site after changes are
        posted constitutes acceptance of the revised Terms.
      </p>

      <h2>7. Contact</h2>
      <p>
        Questions about these Terms can be sent via our{' '}
        <a href="/contact" className="text-brand-green hover:underline">Contact page</a>.
      </p>
    </LegalPage>
  );
}
