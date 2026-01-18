import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';

// Инициализация клиента Supabase
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabase = createClient(supabaseUrl, supabaseAnonKey);

export async function POST(request: Request) {
  try {
    const { email } = await request.json();

    if (!email) {
      return NextResponse.json({ error: 'Email обязателен' }, { status: 400 });
    }

    // Вставка данных в таблицу
    // ЗАМЕНИ 'subscribers' на название своей таблицы, если оно другое
    const { error } = await supabase
      .from('waitlist') 
      .insert([{ email, created_at: new Date() }]);

    if (error) {
      console.error('Supabase error:', error);
      return NextResponse.json({ error: 'Ошибка сохранения в базу' }, { status: 500 });
    }

    return NextResponse.json({ 
      success: true, 
      message: 'Email успешно сохранен! Скоро вы получите свой Sunday-адрес.' 
    });

  } catch (err) {
    return NextResponse.json({ error: 'Ошибка сервера' }, { status: 500 });
  }
}