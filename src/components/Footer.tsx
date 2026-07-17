import { MessageCircle, Send, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-white pt-20 pb-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 18+ Disclaimer */}
        <div className="bg-red-900/30 border border-red-500/30 p-6 rounded-2xl mb-16 text-center">
          <p className="font-bold text-2xl mb-3 text-red-400">18+ | Gamble Responsibly</p>
          <p className="text-gray-300 max-w-2xl mx-auto">
            Betting involves risk. Please gamble responsibly. If you have a gambling problem,
            visit <a href="https://www.begambleaware.org" className="text-primary hover:underline font-semibold">BeGambleAware.org</a>
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-12 mb-16">
          {/* Useful Links */}
          <div>
            <h4 className="font-bold text-xl mb-6 text-white">Useful Links</h4>
            <ul className="space-y-4">
              <li><Link to="/" className="text-gray-400 hover:text-primary transition-colors text-lg">Home</Link></li>
              <li><Link to="/blog" className="text-gray-400 hover:text-primary transition-colors text-lg">Blog</Link></li>
              <li><Link to="/results" className="text-gray-400 hover:text-primary transition-colors text-lg">Results</Link></li>
              <li><a href="/vip" className="text-gray-400 hover:text-primary transition-colors text-lg">VIP Tips</a></li>
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h4 className="font-bold text-xl mb-6 text-white">Legal</h4>
            <ul className="space-y-4">
              <li><Link to="/disclaimer" className="text-gray-400 hover:text-primary transition-colors text-lg">Disclaimer</Link></li>
              <li><Link to="/terms" className="text-gray-400 hover:text-primary transition-colors text-lg">Terms of Service</Link></li>
              <li><Link to="/refund" className="text-gray-400 hover:text-primary transition-colors text-lg">Refund Policy</Link></li>
              <li><Link to="/contact" className="text-gray-400 hover:text-primary transition-colors text-lg">Contact Us</Link></li>
            </ul>
          </div>

          {/* Predictions by Day */}
          <div>
            <h4 className="font-bold text-xl mb-6 text-white">Predictions by Day</h4>
            <ul className="space-y-4">
              {days.map((day) => (
                <li key={day}>
                  <Link to={`/day/${day.toLowerCase()}`} className="text-gray-400 hover:text-primary transition-colors text-lg">
                    {day} Predictions
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact & Social */}
          <div>
            <h4 className="font-bold text-xl mb-6 text-white">Contact Us</h4>
            <ul className="space-y-4 mb-8">
              <li className="flex items-center gap-3 text-gray-400 text-lg">
                <MessageCircle className="w-5 h-5 text-[#25D366]" />
                <span>WhatsApp Support</span>
              </li>
              <li className="flex items-center gap-3 text-gray-400 text-lg">
                <Send className="w-5 h-5 text-[#0088cc]" />
                <span>Telegram Channel</span>
              </li>
              <li className="flex items-center gap-3 text-gray-400 text-lg">
                <Globe className="w-5 h-5 text-primary" />
                <span>info@betmaster.com</span>
              </li>
            </ul>

            <div className="flex gap-4">
              <a href="#" className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center hover:bg-primary transition-colors">
                <Globe className="w-5 h-5" />
              </a>
              <a href="#" className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center hover:bg-[#0088cc] transition-colors">
                <Send className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>

        {/* Copyright */}
        <div className="border-t border-gray-800 pt-10 text-center text-gray-500 text-lg">
          <p>&copy; {new Date().getFullYear()} BetMaster Predictions. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}