import { MessageCircle, Send } from 'lucide-react';

export default function Hero() {
  const whatsappUrl = import.meta.env.VITE_WHATSAPP_URL as string | undefined;
  const telegramUrl = import.meta.env.VITE_TELEGRAM_URL as string | undefined;

  return (
    <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-bg-base overflow-hidden">
      <div className="max-w-5xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-tight mb-6">
          Sure Football Prediction Site <br />
          <span className="text-brand-green">Free Accurate Betting Tips</span>
        </h1>
        <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Get free daily football predictions with high accuracy. Our expert analysis covers all major leagues worldwide with proven winning strategies.
        </p>

        {(whatsappUrl || telegramUrl) && (
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
            {whatsappUrl && (
              <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center px-8 py-4 bg-[#25D366] text-white rounded-full font-bold text-lg hover:bg-[#128C7E] transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5">
                <MessageCircle className="w-6 h-6 mr-2" />
                Join WhatsApp
              </a>
            )}
            {telegramUrl && (
              <a href={telegramUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center px-8 py-4 bg-[#0088cc] text-white rounded-full font-bold text-lg hover:bg-[#006699] transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5">
                <Send className="w-6 h-6 mr-2" />
                Join Telegram
              </a>
            )}
          </div>
        )}

        <div className="flex flex-wrap justify-center gap-8 text-sm text-slate-500 font-medium">
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