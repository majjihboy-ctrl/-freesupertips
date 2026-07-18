import LegalPage from './LegalPage';

export default function DisclaimerPage() {
  return (
    <LegalPage title="Disclaimer">
      <h2>Betting Involves Risk</h2>
      <p>
        Sports betting involves substantial financial risk and is not suitable for everyone. Past
        results, statistical models, and prediction accuracy do not guarantee future outcomes. You
        could lose some or all of the money you stake.
      </p>

      <h2>Predictions Are Opinions, Not Guarantees</h2>
      <p>
        All predictions on FreeSuperTips — free and VIP — are generated using statistical models
        based on historical data, team form, and odds analysis. No prediction is certain. We do not
        guarantee any specific win rate, return, or outcome, regardless of the confidence percentage
        displayed.
      </p>

      <h2>18+ Only</h2>
      <p>
        This Site is intended for individuals aged 18 and above (or the legal gambling age in your
        jurisdiction). If you or someone you know has a gambling problem, help is available at{' '}
        <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" className="text-brand-green hover:underline">
          BeGambleAware.org
        </a>.
      </p>

      <h2>We Are Not a Bookmaker</h2>
      <p>
        FreeSuperTips does not accept bets, hold customer betting funds, or operate as a licensed
        bookmaker. We provide predictions only; all actual betting takes place on third-party
        platforms of your choosing, subject to their own terms and local regulations.
      </p>

      <h2>No Liability</h2>
      <p>
        We are not liable for any financial losses incurred as a result of betting decisions made
        using information from this Site.
      </p>
    </LegalPage>
  );
}
