'use client';
import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import { Mail, ArrowRight, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/dashboard`,
      },
    });

    if (!error) setDone(true);
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#F9F9F7] flex items-center justify-center p-6">
      <div className="max-w-sm w-full">
        <div className="text-center mb-10">
          <h1 className="text-2xl font-serif font-bold mb-2">Sunday Access</h1>
          <p className="text-stone-400 text-sm italic">Введите почту для получения ключа</p>
        </div>

        {done ? (
          <div className="bg-white p-8 rounded-[32px] border border-stone-100 text-center animate-in fade-in zoom-in duration-500">
            <div className="bg-green-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-green-500">
              <Mail size={20} />
            </div>
            <p className="text-sm font-medium">Письмо отправлено!</p>
            <p className="text-xs text-stone-400 mt-2">Проверьте входящие и кликните по ссылке.</p>
          </div>
        ) : (
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="relative">
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@sunday.ai"
                className="w-full bg-white px-6 py-4 rounded-2xl border border-stone-100 focus:outline-none focus:ring-2 focus:ring-orange-100 transition-all text-sm"
              />
            </div>
            <button 
              disabled={loading}
              className="w-full bg-[#2D2D2D] text-white py-4 rounded-2xl font-medium flex items-center justify-center gap-2 hover:bg-black transition-all disabled:opacity-50"
            >
              {loading ? <Loader2 className="animate-spin" size={18} /> : (
                <>Войти <ArrowRight size={18} /></>
              )}
            </button>
          </form>
        )}
        
        <div className="mt-8 text-center">
          <a href="/" className="text-[10px] uppercase tracking-widest text-stone-300 hover:text-stone-500 transition-colors">
            Вернуться на главную
          </a>
        </div>
      </div>
    </div>
  );
}