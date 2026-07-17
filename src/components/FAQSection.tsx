import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const faqs = [
  { q: "What is this website?", a: "We are a free football prediction platform providing daily betting tips with high accuracy. Our expert analysts cover all major leagues worldwide." },
  { q: "Are the tips really free?", a: "Yes! We provide free daily tips for all our visitors. We also offer VIP tips with even higher accuracy for those who want premium service." },
  { q: "Where does your data come from?", a: "We use advanced statistical models, historical data, team form analysis, injury reports, and expert knowledge to generate our predictions." },
  { q: "What is your accuracy rate?", a: "Our free tips maintain an 85%+ accuracy rate, while our VIP tips achieve even higher success rates of 90%+." },
  { q: "When are tips posted?", a: "Daily tips are posted by 10:00 AM GMT every day. VIP tips are sent to our Telegram and WhatsApp channels immediately." },
  { q: "How do I join your Telegram channel?", a: "Click the Telegram button in the hero section or visit our contact page for the direct invite link." }
];

export default function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center text-gray-900 mb-12">Frequently Asked Questions</h2>

        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div key={index} className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full px-8 py-6 text-left flex justify-between items-center hover:bg-gray-50 transition-colors"
              >
                <span className="font-bold text-gray-900 text-lg pr-4">{index + 1}. {faq.q}</span>
                {openIndex === index ? <ChevronUp className="w-6 h-6 text-primary shrink-0" /> : <ChevronDown className="w-6 h-6 text-gray-400 shrink-0" />}
              </button>
              {openIndex === index && (
                <div className="px-8 pb-6 text-gray-600 text-lg leading-relaxed">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}