-- Ejecutar una vez en el SQL Editor del proyecto de Supabase.

create table if not exists public.inscripciones (
  id bigint generated always as identity primary key,
  nombre text not null check (char_length(nombre) between 2 and 120),
  email text not null unique check (char_length(email) <= 254),
  estudios text check (char_length(estudios) <= 160),
  area text not null check (area in ('contenido', 'audio', 'desarrollo', 'difusion', 'oyente')),
  motivacion text check (char_length(motivacion) <= 1000),
  created_at timestamptz not null default now()
);

alter table public.inscripciones enable row level security;

-- La web solo puede añadir inscripciones; nadie puede leerlas con la clave pública.
grant insert on table public.inscripciones to anon;

create policy "La web puede registrar inscripciones"
  on public.inscripciones
  for insert
  to anon
  with check (true);
