# Web del Podcast IA · InnovAI UC3M

Landing en Next.js que explica el proyecto y recoge inscripciones en Supabase.

## Puesta en marcha

1. En Supabase, abre el SQL Editor y ejecuta [`supabase/inscripciones.sql`](supabase/inscripciones.sql).
2. Copia `.env.example` a `.env.local` y rellena `SUPABASE_URL` y `SUPABASE_ANON_KEY`.
3. Arranca en local:

```bash
npm install
npm run dev
```

## Despliegue en Vercel

Importa el repositorio en Vercel, pon **Root Directory** en `web` y añade las dos variables de entorno.

Las inscripciones se ven en Supabase, en **Table Editor → inscripciones**.
