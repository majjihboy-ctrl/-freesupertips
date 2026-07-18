import { useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export default function ContactPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');

  const whatsappUrl = import.meta.env.VITE_WHATSAPP_URL as string | undefined;
  const telegramUrl = import.meta.env.VITE_TELEGRAM_URL as string | undefined;
  const contactEmail = import.meta.env.VITE_CONTACT_EMAIL as string | undefined;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('sending');
    const { error } = await supabase.from('contact_messages').insert({ name, email, message });
    if (error) {
      console.error('Contact form submission failed:', error);
      setStatus('error');
      return;
    }
    setStatus('sent');
    setName('');
    setEmail('');
    setMessage('');
  };

  return (
    <div className="pt-24 pb-16 min-h-screen">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <Link to="/" className="text-brand-green hover:underline mb-6 inline-block">← Back to Home</Link>
        <h1 className="text-3xl sm:text-4xl font-bold text-white mb-4">Contact Us</h1>
        <p className="text-slate-400 mb-8">
          Have a question about a subscription, a payment, or a prediction? Send us a message below,
          or reach out directly.
        </p>

        {(whatsappUrl || telegramUrl || contactEmail) && (
          <div className="flex flex-wrap gap-3 mb-10">
            {whatsappUrl && (
              <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="px-5 py-2.5 rounded-full bg-[#25D366] text-white font-semibold text-sm">
                WhatsApp
              </a>
            )}
            {telegramUrl && (
              <a href={telegramUrl} target="_blank" rel="noopener noreferrer" className="px-5 py-2.5 rounded-full bg-[#0088cc] text-white font-semibold text-sm">
                Telegram
              </a>
            )}
            {contactEmail && (
              <a href={`mailto:${contactEmail}`} className="px-5 py-2.5 rounded-full bg-bg-surface border border-bg-surface-hover text-slate-200 font-semibold text-sm">
                {contactEmail}
              </a>
            )}
          </div>
        )}

        {status === 'sent' ? (
          <div className="p-6 rounded-2xl bg-brand-green/10 border border-brand-green/30 text-brand-green text-center">
            ✅ Thanks — your message has been sent. We'll get back to you soon.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 bg-bg-surface p-6 rounded-2xl border border-bg-surface-hover">
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-1.5">Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-bg-base border border-bg-surface-hover text-white focus:outline-none focus:border-brand-green"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-1.5">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-bg-base border border-bg-surface-hover text-white focus:outline-none focus:border-brand-green"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-1.5">Message</label>
              <textarea
                required
                rows={5}
                value={message}
                onChange={e => setMessage(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-bg-base border border-bg-surface-hover text-white focus:outline-none focus:border-brand-green"
              />
            </div>
            {status === 'error' && (
              <p className="text-brand-danger text-sm">Something went wrong — please try again.</p>
            )}
            <button
              type="submit"
              disabled={status === 'sending'}
              className="w-full py-3 rounded-full bg-brand-green hover:bg-brand-green-hover text-white font-bold transition-all disabled:opacity-60"
            >
              {status === 'sending' ? 'Sending…' : 'Send Message'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
