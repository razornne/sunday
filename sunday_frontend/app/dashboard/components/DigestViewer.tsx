'use client';

interface DigestViewerProps {
  activeDigest: any;
}

export function DigestViewer({ activeDigest }: DigestViewerProps) {
  const ACCENT_COLOR = "text-[#FFB26B]";

  if (!activeDigest) {
    return (
      <div className="h-full flex flex-col items-center justify-center pt-20">
        <p className="font-serif italic text-stone-300 text-xl">Select a briefing from the archive</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto pt-32 pb-24 px-12 animate-in fade-in duration-700 slide-in-from-bottom-4">
      
      {/* Header Area */}
      <header className="mb-24 text-center">
         <div className={`inline-flex items-center gap-3 px-4 py-2 rounded-full bg-[#FFF4E6] ${ACCENT_COLOR} text-[9px] font-bold uppercase tracking-[0.25em] mb-10`}>
           Personal Digest
         </div>
         
         <h1 className="text-5xl md:text-6xl font-serif text-[#1A1A1A] mb-10 leading-[1.1] tracking-tight">
          {activeDigest.subject || "Sunday Briefing"}
         </h1>
         
         <div className="flex items-center justify-center gap-3 text-stone-400">
            <span className="text-sm font-serif italic">Prepared for you on</span>
            <span className="text-xs font-bold uppercase tracking-widest text-stone-300 font-sans">
              {new Date(activeDigest.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })}
            </span>
         </div>
      </header>

      {/* Content Body */}
      <div className="space-y-24">
        
        {/* Executive Summary */}
        {activeDigest.content?.big_picture && (
          <section className="relative pl-6 md:pl-12 border-l-2 border-[#FFB26B]">
             <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-300 mb-6 font-sans">Executive Summary</h2>
             <p className="text-2xl md:text-[28px] font-serif text-stone-800 leading-[1.6] antialiased">
               {activeDigest.content.big_picture}
             </p>
          </section>
        )}

        {/* Trends / Signals */}
        {activeDigest.content?.trends && (
            <section>
              <div className="flex items-end gap-6 mb-12 pb-4 border-b border-stone-100">
                  <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-300 font-sans">Key Signals</h2>
              </div>
              
              <div className="grid gap-16">
                {activeDigest.content.trends.map((trend: any, i: number) => (
                  <div key={i} className="group">
                    <div className="flex items-center gap-4 mb-4">
                       <span className="font-serif text-[#FFB26B]/40 text-2xl italic">#{i+1}</span>
                       <h3 className="text-xl font-bold text-stone-900 group-hover:text-[#FFB26B] transition-colors">
                         {trend.title}
                       </h3>
                    </div>
                    <p className="text-stone-500 leading-relaxed pl-10 text-lg font-serif">
                      {trend.insight}
                    </p>
                  </div>
                ))}
              </div>
            </section>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-40 pt-12 border-t border-stone-100 text-center pb-20">
         <div className="text-3xl font-serif font-bold text-stone-200 mb-6 select-none">
            Sunday<span className="text-[#FFB26B]">.</span>
         </div>
         <p className="text-stone-300 text-[9px] uppercase tracking-[0.3em] font-sans">
            Your Weekly Intelligence System
         </p>
      </footer>
    </div>
  );
}
