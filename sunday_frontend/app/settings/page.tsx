'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { ChevronRight, ChevronLeft, Check } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  
  const [role, setRole] = useState('');
  const [focusAreas, setFocusAreas] = useState('');
  const [digestDay, setDigestDay] = useState('Sunday');
  const [digestTime, setDigestTime] = useState('09:00');

  const handleSave = async () => {
    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    
    if (user) {
      const focusArray = focusAreas.split(',').map(item => item.trim()).filter(i => i !== '');
      const { error } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          role: role,
          focus_areas: focusArray,
          digest_day: digestDay,
          digest_time: digestTime,
          timezone: 'UTC'
        });

      if (!error) router.push('/dashboard');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#F9F9F7] text-[#2D2D2D] flex flex-col items-center justify-center p-6 antialiased">
      
      {/* 1. Логотип и Вопрос — Крупно и по центру */}
      <div className="text-center mb-16 w-full max-w-4xl">
        <div className="text-6xl font-serif font-bold mb-10 tracking-tight">
          Sunday<span className="text-[#FFB26B]">.</span>
        </div>
        
        <div className="space-y-4">
          <h1 className="text-4xl font-serif text-stone-800 leading-tight">
            {step === 1 && <>What is your <span className="italic text-stone-400">professional role?</span></>}
            {step === 2 && <>Define your <span className="italic text-stone-400">focus areas.</span></>}
            {step === 3 && <>Delivery <span className="italic text-stone-400">ritual.</span></>}
          </h1>
          <p className="text-stone-400 text-lg italic">
            {step === 1 && "SundayAI tailors content based on your perspective."}
            {step === 2 && "Enter topics separated by commas."}
            {step === 3 && "When should your intelligence arrive?"}
          </p>
        </div>
      </div>

      {/* 2. Основной блок управления — Ширина 'чуть больше половины' (max-w-3xl) */}
      <div className="w-full max-w-3xl space-y-8 flex flex-col items-center">
        
        {/* STEP 1: ROLE */}
        {step === 1 && (
          <div className="w-full space-y-6 animate-in fade-in duration-500">
            <input 
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. Founder"
              className="w-full bg-white px-10 py-5 rounded-full border border-stone-100 outline-none focus:ring-4 focus:ring-[#FFB26B]/10 transition-all text-center text-2xl placeholder:text-stone-200 shadow-sm"
            />
            <button 
              onClick={() => setStep(2)}
              disabled={!role}
              className="w-full bg-[#FFB26B] text-white py-5 rounded-full font-bold flex items-center justify-center gap-3 hover:opacity-90 transition-all disabled:opacity-30 shadow-sm text-xl"
            >
              Continue <ChevronRight size={24} />
            </button>
          </div>
        )}

        {/* STEP 2: FOCUS AREAS */}
        {step === 2 && (
          <div className="w-full space-y-6 animate-in fade-in duration-500">
            <textarea 
              rows={3}
              value={focusAreas}
              onChange={(e) => setFocusAreas(e.target.value)}
              placeholder="AI, SaaS, Fintech..."
              className="w-full bg-white px-10 py-8 rounded-[3rem] border border-stone-100 outline-none focus:ring-4 focus:ring-[#FFB26B]/10 transition-all text-center text-2xl resize-none placeholder:text-stone-200 shadow-sm"
            />
            <div className="flex gap-4 w-full">
              <button onClick={() => setStep(1)} className="p-5 text-stone-300 hover:text-stone-900 transition-colors">
                <ChevronLeft size={32} />
              </button>
              <button 
                onClick={() => setStep(3)}
                disabled={!focusAreas}
                className="flex-1 bg-[#FFB26B] text-white py-5 rounded-full font-bold flex items-center justify-center gap-3 hover:opacity-90 transition-all disabled:opacity-30 shadow-sm text-xl"
              >
                Continue <ChevronRight size={24} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: SCHEDULE */}
        {step === 3 && (
          <div className="w-full space-y-6 animate-in fade-in duration-500">
            <div className="w-full space-y-4">
              <div className="bg-white px-10 py-2 rounded-full border border-stone-100 shadow-sm">
                <select 
                  value={digestDay} 
                  onChange={(e) => setDigestDay(e.target.value)} 
                  className="w-full bg-transparent p-5 outline-none appearance-none text-center font-serif text-2xl cursor-pointer"
                >
                  {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="bg-white px-10 py-2 rounded-full border border-stone-100 shadow-sm">
                <input 
                  type="time" 
                  value={digestTime} 
                  onChange={(e) => setDigestTime(e.target.value)} 
                  className="w-full bg-transparent p-5 outline-none text-center text-2xl cursor-pointer" 
                />
              </div>
            </div>
            <div className="flex gap-4 w-full">
              <button onClick={() => setStep(2)} className="p-5 text-stone-300 hover:text-stone-900 transition-colors">
                <ChevronLeft size={32} />
              </button>
              <button 
                onClick={handleSave}
                disabled={loading}
                className="flex-1 bg-[#FFB26B] text-white py-5 rounded-full font-bold flex items-center justify-center gap-3 hover:opacity-90 transition-all disabled:opacity-50 shadow-sm text-xl"
              >
                {loading ? '...' : <>Complete Setup <Check size={24} /></>}
              </button>
            </div>
          </div>
        )}

        {/* 3. Индикатор прогресса снизу */}
        <div className="pt-20 flex justify-center gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className={`h-1 rounded-full transition-all duration-500 ${step === i ? 'w-20 bg-[#FFB26B]' : 'w-4 bg-stone-200'}`} />
          ))}
        </div>
      </div>
    </div>
  );
}