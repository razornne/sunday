'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { Loader2 } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { DigestViewer } from './components/DigestViewer';

export default function Dashboard() {
  const router = useRouter();
  const [activeDigest, setActiveDigest] = useState<any>(null);
  const [allDigests, setAllDigests] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { router.push('/login'); return; }

      const { data: profileData } = await supabase.from('profiles').select('*').eq('id', user.id).single();
      setProfile(profileData || { role: 'Subscriber', focus_areas: ['Tech', 'Design'] }); 

      const { data: digests } = await supabase.from('digests').select('*').eq('user_id', user.id).order('created_at', { ascending: false });
      
      // MOCK DATA (if DB is empty, to show design)
      if (!digests || digests.length === 0) {
         const mock = [{
            id: 1, 
            created_at: new Date().toISOString(), 
            subject: 'Weekly Intelligence', 
            structured_content: { big_picture: 'Market shifts indicate a pivot towards privacy-first design patterns.', trends: [{title: 'AI Saturation', insight: 'Users are seeking more human-curated content.'}] } 
         }];
         setAllDigests(mock);
         setActiveDigest(parseDigest(mock[0]));
      } else {
         setAllDigests(digests);
         setActiveDigest(parseDigest(digests[0]));
      }
      setLoading(false);
    }
    loadDashboardData();
  }, [router]);

  const parseDigest = (item: any) => {
    let content = item.structured_content;
    if (typeof content === 'string') {
      try { content = JSON.parse(content); } catch (e) { content = {}; }
    }
    return { ...item, content };
  };

  if (loading) return (
    <div className="flex h-screen items-center justify-center bg-white">
      <Loader2 className="animate-spin text-stone-300" size={24} />
    </div>
  );

  return (
    <>
      <Sidebar 
         allDigests={allDigests} 
         activeDigest={activeDigest} 
         profile={profile} 
         onSelectDigest={(d) => setActiveDigest(parseDigest(d))} 
      />
      <main className="flex-1 overflow-y-auto relative bg-white scroll-smooth focus:outline-none">
        <DigestViewer activeDigest={activeDigest} />
      </main>
    </>
  );
}