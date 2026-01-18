'use client'; // <-- ОБЯЗАТЕЛЬНО для Next.js App Router

import React, { useState } from 'react';
import { createClient } from '@supabase/supabase-js';

// Проверь этот ключ в панели Supabase! Он должен начинаться с eyJhb...
const supabase = createClient(
  "https://tkltifrcefjoxjvrisix.supabase.co", 
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRrbHRpZnJjZWZqb3hqdnJpc2l4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0NzgyMzYsImV4cCI6MjA4MTA1NDIzNn0.akWubBsGE5-PXl2xT3_2E5ikrIIKzxfWUTroBJXX3AE");

export default function LandingPage() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState(null); // 'loading', 'success', 'error'

  const handleJoin = async (e) => {
    e.preventDefault();
    setStatus('loading');

    const { error } = await supabase.from('waitlist').insert([{ email }]);
    
    if (error) {
      console.error("Ошибка Supabase:", error);
      setStatus('error');
    } else {
      setStatus('success');
      setEmail(''); // Очищаем поле после записи
    }
  };

  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-blue-100 font-sans">
      {/* --- Navigation --- */}
      <nav className="max-w-7xl mx-auto px-6 py-8 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold shadow-lg shadow-blue-200">S</div>
          <span className="text-xl font-bold tracking-tight">Sunday AI</span>
        </div>
        <div className="hidden md:flex gap-8 text-sm font-medium text-slate-500">
          <a href="#how" className="hover:text-blue-600 transition">Как это работает</a>
          <a href="#security" className="hover:text-blue-600 transition">Безопасность</a>
        </div>
        <button className="text-sm font-semibold bg-slate-900 text-white px-6 py-2.5 rounded-full hover:bg-slate-800 transition shadow-lg shadow-slate-200">
          Войти
        </button>
      </nav>

      {/* --- Hero Section --- */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-32 grid lg:grid-cols-2 gap-16 items-center">
        <div className="animate-in fade-in slide-in-from-left duration-1000">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-xs font-bold uppercase tracking-wider mb-6">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            Beta доступ открыт
          </div>
          <h1 className="text-6xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-8">
            Верни себе свои <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-500">воскресенья.</span>
          </h1>
          <p className="text-xl text-slate-500 mb-10 leading-relaxed max-w-lg">
            Sunday AI анализирует вашу рабочую почту и присылает один идеальный отчет. 
            Больше никакого "email fatigue".
          </p>

          <form onSubmit={handleJoin} className="flex flex-col sm:flex-row gap-3 max-w-md">
            <input 
              required
              type="email" 
              value={email}
              placeholder="Введите ваш email..."
              className="flex-1 px-6 py-4 rounded-2xl bg-slate-50 border-none ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none transition"
              onChange={(e) => setEmail(e.target.value)}
            />
            <button 
              type="submit"
              disabled={status === 'loading'}
              className="px-8 py-4 bg-blue-600 text-white rounded-2xl font-bold hover:bg-blue-700 transition shadow-xl shadow-blue-200 disabled:opacity-50"
            >
              {status === 'loading' ? 'Секунду...' : 'Go'}
            </button>
          </form>
          {status === 'success' && <p className="mt-4 text-green-600 font-medium">✨ Вы в списке! Мы свяжемся с вами скоро.</p>}
          {status === 'error' && <p className="mt-4 text-red-600 font-medium">❌ Упс! Ошибка. Проверьте соединение.</p>}
        </div>

        {/* --- Live Preview Card --- */}
        <div className="relative group animate-in fade-in zoom-in duration-1000">
          <div className="absolute -inset-4 bg-gradient-to-tr from-blue-100 to-indigo-100 rounded-[40px] blur-2xl opacity-50 group-hover:opacity-80 transition duration-1000"></div>
          <div className="relative bg-white border border-slate-100 rounded-[32px] shadow-2xl p-8 transform group-hover:-translate-y-2 transition duration-500">
            {/* Твой контент карточки (оставлен без изменений, так как он отличный) */}
            <div className="flex justify-between items-center mb-8 border-b border-slate-50 pb-6">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-400 mb-1">Weekly Intelligence</p>
                <h3 className="text-xl font-bold">The Sunday Brief</h3>
              </div>
              <div className="w-10 h-10 bg-slate-50 rounded-full flex items-center justify-center text-lg">☀️</div>
            </div>

            <div className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-blue-600">
                  <span className="text-sm font-bold uppercase tracking-tighter">Big Picture</span>
                </div>
                <p className="text-slate-600 leading-relaxed text-sm">
                  Неделя сфокусирована на <strong>запуске продукта</strong>. Основной риск — задержка API, но команда маркетинга уже подготовила план Б.
                </p>
              </div>

              <div className="p-4 bg-amber-50 rounded-2xl border border-amber-100">
                <h4 className="text-[10px] font-bold text-amber-700 uppercase mb-3 tracking-widest">⚠️ Action Items</h4>
                <ul className="text-xs text-amber-900 space-y-2 font-medium">
                  <li>• Утвердить бюджет с Николаем (до ВТ)</li>
                  <li>• Созвон по юридическим вопросам (14:00)</li>
                </ul>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-xl text-center">
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Noise Filter</p>
                  <p className="text-xs font-bold text-slate-700">34 скрыто</p>
                </div>
                <div className="p-4 bg-slate-50 rounded-xl text-center">
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Focus Mode</p>
                  <p className="text-xs font-bold text-slate-700">Marketing</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --- Features & Footer (остаются без изменений) --- */}
    </div>
  );
}