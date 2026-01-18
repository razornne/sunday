'use client';
import { useState } from 'react';

export default function LandingPage() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success'>('idle');

  const joinWaitlist = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading');

    try {
      // Отправляем данные на наш Python Backend
      const response = await fetch('http://127.0.0.1:8000/api/waitlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email }),
      });

      if (response.ok) {
        setStatus('success');
        setEmail(''); // Очистить поле после успеха
      } else {
        console.error('Ошибка сервера при добавлении в waitlist');
        setStatus('idle');
      }
    } catch (error) {
      console.error('Ошибка сети:', error);
      setStatus('idle');
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9F7] flex flex-col items-center justify-center p-6 text-center">
      <h1 className="text-6xl font-serif mb-6 text-[#2D2D2D]">
        Sunday<span className="text-orange-400">.</span>
      </h1>
      
      <p className="text-stone-500 max-w-md mb-10 leading-relaxed italic font-serif">
        Your newsletters. Once a week. In the perfect format.
      </p>

      {status === 'success' ? (
        <div className="flex flex-col items-center gap-2">
            <p className="text-orange-500 font-serif italic text-xl animate-bounce">
                Welcome to the quiet side of the internet.
            </p>
            <p className="text-stone-400 text-sm">We'll be in touch soon.</p>
        </div>
      ) : (
        <form onSubmit={joinWaitlist} className="flex flex-col sm:flex-row gap-3 w-full max-w-lg">
          <input 
            type="email" 
            placeholder="Your email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 px-8 py-4 rounded-3xl border border-stone-200 bg-white text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-orange-100 transition-all shadow-sm"
            required
            disabled={status === 'loading'}
          />
          <button 
            type="submit"
            disabled={status === 'loading'}
            className="bg-[#FFB26B] text-white px-10 py-4 rounded-3xl font-bold hover:shadow-lg hover:bg-[#ffaa5e] active:scale-95 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {status === 'loading' ? 'Joining...' : 'Waiting for access'}
          </button>
        </form>
      )}
      
      <div className="mt-12 text-xs text-stone-300 uppercase tracking-widest">
        Make your email quiet again
      </div>
    </div>
  );
}