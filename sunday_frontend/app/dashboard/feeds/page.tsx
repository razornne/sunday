'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { Loader2, Plus, Trash2, AlertCircle, Rss } from 'lucide-react';
import { Sidebar } from '../components/Sidebar';

export default function FeedsPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<any>(null);
  const [feeds, setFeeds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newUrl, setNewUrl] = useState('');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { router.push('/login'); return; }
      setUserId(user.id);

      const { data: profileData } = await supabase.from('profiles').select('*').eq('id', user.id).single();
      setProfile(profileData);

      const { data: feedsData } = await supabase
        .from('rss_feeds')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });
      setFeeds(feedsData || []);
      setLoading(false);
    }
    load();
  }, [router]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId || !newUrl.trim()) return;
    setAdding(true);
    setError('');

    const { data, error: insertError } = await supabase
      .from('rss_feeds')
      .insert({ user_id: userId, feed_url: newUrl.trim() })
      .select()
      .single();

    if (insertError) {
      setError(insertError.message.includes('duplicate') ? 'Этот фид уже добавлен.' : 'Не удалось добавить фид.');
    } else if (data) {
      setFeeds([data, ...feeds]);
      setNewUrl('');
    }
    setAdding(false);
  };

  const handleRemove = async (id: string) => {
    setFeeds(feeds.filter((f) => f.id !== id));
    await supabase.from('rss_feeds').delete().eq('id', id);
  };

  const handleToggle = async (feed: any) => {
    const nextActive = !feed.is_active;
    setFeeds(feeds.map((f) => (f.id === feed.id ? { ...f, is_active: nextActive } : f)));
    await supabase.from('rss_feeds').update({ is_active: nextActive }).eq('id', feed.id);
  };

  if (loading) return (
    <div className="flex h-screen items-center justify-center bg-white">
      <Loader2 className="animate-spin text-stone-300" size={24} />
    </div>
  );

  return (
    <>
      <Sidebar profile={profile} />
      <main className="flex-1 overflow-y-auto bg-white">
        <div className="max-w-2xl mx-auto pt-32 pb-24 px-12">
          <header className="mb-16 text-center">
            <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-[#FFF4E6] text-[#FFB26B] text-[9px] font-bold uppercase tracking-[0.25em] mb-10">
              RSS Feeds
            </div>
            <h1 className="text-5xl font-serif text-[#1A1A1A] mb-4 leading-[1.1] tracking-tight">
              Your reading sources
            </h1>
            <p className="text-stone-400 font-serif italic">
              Add feeds and Sunday will summarize new articles into your briefings.
            </p>
          </header>

          <form onSubmit={handleAdd} className="flex gap-3 mb-4">
            <input
              type="url"
              required
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://example.com/feed.xml"
              className="flex-1 bg-[#FAFAF9] px-6 py-4 rounded-2xl border border-stone-100 outline-none focus:ring-4 focus:ring-[#FFB26B]/10 transition-all text-sm placeholder:text-stone-300"
            />
            <button
              disabled={adding}
              className="bg-[#FFB26B] text-white px-6 py-4 rounded-2xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-all disabled:opacity-50"
            >
              {adding ? <Loader2 className="animate-spin" size={18} /> : <Plus size={18} />}
            </button>
          </form>
          {error && <p className="text-rose-500 text-xs mb-8">{error}</p>}

          <div className="space-y-3 mt-10">
            {feeds.length === 0 && (
              <div className="text-center py-20 text-stone-300 font-serif italic">
                No feeds yet — add your first one above.
              </div>
            )}
            {feeds.map((feed) => (
              <div
                key={feed.id}
                className="flex items-center justify-between gap-4 px-6 py-4 rounded-2xl border border-stone-100 bg-[#FAFAF9]"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <Rss size={16} className="text-[#FFB26B] shrink-0" strokeWidth={1.5} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-stone-800 truncate">
                      {feed.title || feed.feed_url}
                    </p>
                    <p className="text-xs text-stone-400 truncate">{feed.feed_url}</p>
                    {feed.last_error && (
                      <p className="text-xs text-rose-500 flex items-center gap-1 mt-1">
                        <AlertCircle size={12} /> {feed.last_error}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleToggle(feed)}
                    className={`text-[10px] uppercase tracking-widest font-semibold px-3 py-1.5 rounded-full transition-colors ${
                      feed.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-stone-100 text-stone-400'
                    }`}
                  >
                    {feed.is_active ? 'Active' : 'Paused'}
                  </button>
                  <button
                    onClick={() => handleRemove(feed.id)}
                    className="p-2 rounded-lg text-stone-300 hover:text-rose-500 hover:bg-rose-50 transition-colors"
                  >
                    <Trash2 size={16} strokeWidth={1.5} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
