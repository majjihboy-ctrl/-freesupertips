import { MessageCircle, Send } from 'lucide-react';

export default function Hero() {
  return (
    <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-gray-50 via-white to-pink-50 overflow-hidden">
      <div className="max-w-5xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 tracking-tight leading-tight mb-6">
          Sure Football Prediction Site <br />
          <span className="text-primary">Free Accurate Betting Tips</span>
        </h1>
        <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed">
          Get free daily football predictions with high accuracy. Our expert analysis covers all major leagues worldwide with proven winning strategies.
        </p>

        <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
          <a href="#" className="inline-flex items-center justify-center px-8 py-4 bg-[#25D366] text-white rounded-full font-bold text-lg hover:bg-[#128C7E] transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5">
            <MessageCircle className="w-6 h-6 mr-2" />
            Join WhatsApp
          </a>
          <a href="#" className="inline-flex items-center justify-center px-8 py-4 bg-[#0088cc] text-white rounded-full font-bold text-lg hover:bg-[#006699] transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5">
            <Send className="w-6 h-6 mr-2" />
            Join Telegram
          </a>
        </div>

        <div className="flex flex-wrap justify-center gap-8 text-sm text-gray-500 font-medium">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            85%+ Accuracy Rate
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            100% Free Tips
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            Daily Updates
          </div>
        </div>
      </div>
    </section>
  );
}