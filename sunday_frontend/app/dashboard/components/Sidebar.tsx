'use client';

import { Inbox, Settings, LogOut, User } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

interface SidebarProps {
  allDigests: any[];
  activeDigest: any;
  profile: any;
  onSelectDigest: (digest: any) => void;
}

export function Sidebar({ allDigests, activeDigest, profile, onSelectDigest }: SidebarProps) {
  const router = useRouter();

  return (
    <aside className="w-72 flex flex-col py-12 px-8 shrink-0 h-full bg-[#FAFAF9] border-r border-stone-100">
      
      {/* Logo - Editorial Style */}
      <div className="mb-16 px-2">
        <h1 className="text-3xl font-serif tracking-tight text-stone-900 select-none">
          Sunday<span className="text-[#FFB26B]">.</span>
        </h1>
      </div>
      
      <nav className="flex-1 flex flex-col min-h-0 space-y-8">
        
        {/* Main Menu */}
        <div className="space-y-1">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-white text-stone-900 shadow-sm border border-stone-100 transition-all duration-200 group">
            <Inbox size={18} strokeWidth={1.5} className="text-[#FFB26B]" /> 
            <span className="text-[13px] font-medium">Briefings</span>
          </button>
          <button 
            onClick={() => router.push('/settings')}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-stone-500 hover:text-stone-900 hover:bg-white hover:shadow-sm hover:border-stone-100 border border-transparent transition-all duration-200 group"
          >
            <Settings size={18} strokeWidth={1.5} className="text-stone-400 group-hover:text-stone-600" /> 
            <span className="text-[13px] font-medium">Settings</span>
          </button>
        </div>

        {/* Archive List */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 mb-4 px-2">Archive</h2>
          <div className="overflow-y-auto flex-1 space-y-1 pr-2 -mr-2">
            {allDigests.map((d) => {
              const isActive = activeDigest?.id === d.id;
              return (
                <button 
                  key={d.id}
                  onClick={() => onSelectDigest(d)}
                  className={`w-full text-left px-4 py-4 rounded-xl transition-all duration-200 group ${
                    isActive 
                      ? 'bg-white shadow-sm border border-stone-100' 
                      : 'hover:bg-white/60 border border-transparent'
                  }`}
                >
                  <span className={`text-[11px] font-semibold uppercase tracking-wider block mb-1.5 ${
                    isActive ? 'text-[#FFB26B]' : 'text-stone-400'
                  }`}>
                    {new Date(d.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                  <p className={`text-[13px] leading-snug line-clamp-2 ${
                    isActive ? 'text-stone-900 font-medium' : 'text-stone-500 group-hover:text-stone-700'
                  }`}>
                    {d.subject || "Weekly Update"}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* User Profile - Minimal */}
      <div className="pt-6 mt-auto border-t border-stone-200/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-stone-200/60 flex items-center justify-center text-stone-500">
              <User size={16} strokeWidth={1.5} />
            </div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-stone-600">
              {profile?.role || 'User'}
            </span>
          </div>
          <button 
            onClick={() => supabase.auth.signOut().then(() => router.push('/'))} 
            className="p-2 rounded-lg text-stone-400 hover:text-stone-600 hover:bg-stone-200/40 transition-colors"
            title="Sign out"
          >
            <LogOut size={16} strokeWidth={1.5} />
          </button>
        </div>
      </div>
    </aside>
  );
}
