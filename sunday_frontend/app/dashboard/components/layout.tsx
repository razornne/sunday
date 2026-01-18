import { Playfair_Display, Inter } from 'next/font/google';

// ... Font configuration ...

export default function DashboardLayout({ children }) {
  return (
    // These variables (--font-playfair) now power the Tailwind 'font-serif' utility
    <div className={`${playfair.variable} ${inter.variable} flex min-h-screen bg-white font-sans text-stone-900 overflow-hidden`}>
      {children}
    </div>
  );
}