import { MessageCircle, Send, Mail } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Footer() {
  const whatsappUrl = import.meta.env.VITE_WHATSAPP_URL as string | undefined;
  const telegramUrl = import.meta.env.VITE_TELEGRAM_URL as string | undefined;
  const contactEmail = (import.meta.env.VITE_CONTACT_EMAIL as string | undefined) || null;

  return (
    <footer className="bg-bg-surface text-white pt-20 pb-10 border-t border-bg-surface-hover">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 18+ Disclaimer */}
        <div className="bg-brand-danger/10 border border-brand-danger/30 p-6 rounded-2xl mb-16 text-center">
          <p className="font-bold text-2xl mb-3 text-brand-danger">18+ | Gamble Responsibly</p>
          <p className="text-slate-300 max-w-2xl mx-auto">
            Betting involves risk. Please gamble responsibly. If you have a gambling problem,
            visit <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" className="text-brand-green hover:underline font-semibold">BeGambleAware.org</a>
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-12 mb-16">
          {/* Useful Links */}
          <div>
            <h4 className="font-bold text-xl mb-6 text-white">Useful Links</h4>
            <ul className="space-y-4">
              <li><Link to="/" className="text-slate-400 hover:text-brand-green transition-colors text-lg">Home</Link></li>
              <li><Link to="/results" className="text-slate-400 hover:text-brand-green transition-colors text-lg">Results</Link></li>
              <li><Link to="/pricing" className="text-slate-400 hover:text-brand-green transition-colors text-lg">VIP Tips</Link></li>
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h4 className="font-bold text-xl mb-6 text-white">Legal</h4>
            <ul className="space-y-4">
              <li><Link to="/disclaimer" className="text-slate-400 hover:text-brand-green transition-colors text-lg">Disclaimer</Link></li>
              <li><Link to="/terms" className="text-slate-400 hover:text-brand-green transition-colors text-lg">Terms of Service</Link></li>
              <li><Link to="/refund" className="text-slate-400 hover:text-brand-green transition-colors text-lg">Refund Policy</Link></li>
              <li><Link to="/contact" className="text-slate-400 hover:text-brand-green transition-colors text-lg">Contact Us</Link></li>
            </ul>
          </div>

          {/* Contact & Social */}
          <div>
            <h4 className="font-bold text-xl mb-6 text-white">Contact Us</h4>
            <ul className="space-y-4 mb-8">
              {whatsappUrl && (
                <li>
                  <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-slate-400 hover:text-white text-lg transition-colors">
                    <MessageCircle className="w-5 h-5 text-[#25D366]" />
                    <span>WhatsApp Support</span>
                  </a>
                </li>
              )}
              {telegramUrl && (
                <li>
                  <a href={telegramUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-slate-400 hover:text-white text-lg transition-colors">
                    <Send className="w-5 h-5 text-[#0088cc]" />
                    <span>Telegram Channel</span>
                  </a>
                </li>
              )}
              {contactEmail && (
                <li>
                  <a href={`mailto:${contactEmail}`} className="flex items-center gap-3 text-slate-400 hover:text-white text-lg transition-colors">
                    <Mail className="w-5 h-5 text-brand-green" />
                    <span>{contactEmail}</span>
                  </a>
                </li>
              )}
              {!whatsappUrl && !telegramUrl && !contactEmail && (
                <li className="text-slate-500 text-sm">Contact details coming soon.</li>
              )}
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="border-t border-bg-surface-hover pt-10 text-center text-slate-500 text-lg">
          <p>&copy; {new Date().getFullYear()} FreeSuperTips. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
