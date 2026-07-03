import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#F9F9F7] flex flex-col items-center justify-center p-6 text-center">
      <h1 className="text-6xl font-serif mb-6 text-[#2D2D2D]">
        Sunday<span className="text-orange-400">.</span>
      </h1>

      <p className="text-stone-500 max-w-md mb-10 leading-relaxed italic font-serif">
        Your newsletters. Once a week. In the perfect format.
      </p>

      <Link
        href="/login"
        className="bg-[#FFB26B] text-white px-10 py-4 rounded-3xl font-bold hover:shadow-lg hover:bg-[#ffaa5e] active:scale-95 transition-all"
      >
        Войти
      </Link>

      <div className="mt-12 text-xs text-stone-300 uppercase tracking-widest">
        Make your email quiet again
      </div>
    </div>
  );
}