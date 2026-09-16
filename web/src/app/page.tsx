import { SignupForm } from "./signup-form";

const STEPS = [
  {
    title: "Investigación",
    tool: "Perplexity",
    text: "Busca las noticias de IA más recientes y descarta los temas que ya se han tratado en episodios anteriores.",
  },
  {
    title: "Guion",
    tool: "Perplexity",
    text: "Convierte la investigación en una conversación entre dos personajes, línea a línea.",
  },
  {
    title: "Dramatización",
    tool: "Gemini",
    text: "Reescribe el diálogo con pausas, muletillas y reacciones («ajá», «claro») para que suene hablado y no leído.",
  },
  {
    title: "Voces",
    tool: "Gemini TTS",
    text: "Genera las dos voces a la vez, en una sola petición, para que el ritmo y la entonación sean coherentes.",
  },
  {
    title: "Mezcla",
    tool: "FFmpeg",
    text: "Une intro, conversación y outro sobre una música de fondo y exporta el episodio final en MP3.",
  },
];

const FORMATS = [
  {
    name: "Deep Dive",
    tag: "1 noticia",
    text: "Una noticia reciente y de alto impacto, analizada a fondo.",
  },
  {
    name: "Newsletter",
    tag: "5 noticias",
    text: "Un boletín ágil con las cinco historias de IA más relevantes de la semana.",
  },
  {
    name: "Basics",
    tag: "Divulgación",
    text: "Un episodio educativo sobre un tema concreto, para entender los conceptos clave.",
  },
];

const FACTS = [
  { value: "5–7", label: "minutos por episodio" },
  { value: "2", label: "voces generadas por IA" },
  { value: "3", label: "formatos distintos" },
  { value: "0", label: "personas editando" },
];

const WAVE = [40, 70, 55, 90, 65, 100, 45, 80, 60, 95, 50, 75, 35, 85, 55, 70, 45, 90, 60, 40];

function Logo() {
  return (
    <a href="#" className="flex items-center gap-2 font-display text-xl font-bold tracking-tight">
      <span>
        Innov<span className="rounded bg-brand px-1 text-ink">AI</span>
      </span>
      <span className="text-sm font-medium opacity-60">UC3M</span>
    </a>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-4 inline-block rounded-full border-2 border-current px-3 py-1 text-xs font-bold uppercase tracking-widest">
      {children}
    </p>
  );
}

export default function Home() {
  return (
    <>
      <header className="sticky top-0 z-20 border-b-2 border-ink bg-paper/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Logo />
          <nav className="flex items-center gap-6 text-sm font-semibold">
            <a href="#proyecto" className="hidden hover:underline md:inline">
              El proyecto
            </a>
            <a href="#como-funciona" className="hidden hover:underline md:inline">
              Cómo funciona
            </a>
            <a href="#formatos" className="hidden hover:underline md:inline">
              Formatos
            </a>
            <a
              href="#unete"
              className="rounded-full border-2 border-ink bg-brand px-4 py-2 transition hover:shadow-[3px_3px_0_0_#0a0a0a]"
            >
              Únete
            </a>
          </nav>
        </div>
      </header>

      <main>
        <section className="bg-ink text-paper">
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 sm:px-6 md:grid-cols-[1.2fr_1fr] md:py-28">
            <div>
              <p className="mb-6 inline-flex items-center gap-2 rounded-full bg-paper/10 px-3 py-1 text-sm font-medium">
                <span className="size-2 rounded-full bg-brand" />
                Un proyecto de InnovAI UC3M
              </p>
              <h1 className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
                Un podcast sobre IA, <span className="bg-brand px-2 text-ink">hecho por IA</span>.
              </h1>
              <p className="mt-6 max-w-xl text-lg text-paper/75">
                Episodios en español producidos de principio a fin sin intervención humana: la IA busca las noticias,
                escribe el guion, pone las voces y mezcla el audio.
              </p>
              <div className="mt-10 flex flex-wrap gap-4">
                <a
                  href="#unete"
                  className="rounded-full border-2 border-brand bg-brand px-7 py-3 font-bold text-ink transition hover:-translate-y-0.5"
                >
                  Quiero participar
                </a>
                <a
                  href="#como-funciona"
                  className="rounded-full border-2 border-paper/40 px-7 py-3 font-bold transition hover:border-paper"
                >
                  Cómo funciona
                </a>
              </div>
            </div>

            <div className="rounded-2xl border-2 border-paper bg-brand p-6 text-ink shadow-[8px_8px_0_0_#ffffff]">
              <div className="flex items-center justify-between text-sm font-semibold">
                <span>Episodio · Deep Dive</span>
                <span>06:12</span>
              </div>
              <div className="my-8 flex h-24 items-center gap-1.5" aria-hidden="true">
                {WAVE.map((height, i) => (
                  <span
                    key={i}
                    className="wave-bar w-full rounded-full bg-ink"
                    style={{ height: `${height}%`, animationDelay: `${(i % 7) * 0.12}s` }}
                  />
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border-2 border-ink bg-paper p-4">
                  <p className="font-display text-lg font-bold">Tony</p>
                  <p className="text-sm text-ink/70">El presentador curioso</p>
                </div>
                <div className="rounded-xl border-2 border-ink bg-paper p-4">
                  <p className="font-display text-lg font-bold">Gabriela</p>
                  <p className="text-sm text-ink/70">La experta tranquila</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="proyecto" className="scroll-mt-16">
          <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 md:grid-cols-2 md:py-28">
            <div>
              <SectionLabel>El proyecto</SectionLabel>
              <h2 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
                ¿Hasta dónde puede llegar la IA generativa sola?
              </h2>
              <p className="mt-6 text-lg text-ink/75">
                Nace dentro de InnovAI, la asociación de inteligencia artificial de la Universidad Carlos III de Madrid,
                para responder a esa pregunta con algo que se pueda escuchar.
              </p>
              <p className="mt-4 text-lg text-ink/75">
                Cada episodio es una conversación entre dos personajes con voz sintética: Tony, que pregunta lo que
                cualquiera se preguntaría, y Gabriela, que lo explica con calma. Todo el proceso está automatizado.
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-4 self-center">
              {FACTS.map((fact) => (
                <div key={fact.label} className="rounded-2xl border-2 border-ink p-6">
                  <dt className="sr-only">{fact.label}</dt>
                  <dd>
                    <span className="block font-display text-5xl font-bold">{fact.value}</span>
                    <span className="mt-2 block text-ink/70">{fact.label}</span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section id="como-funciona" className="scroll-mt-16 border-y-2 border-ink bg-brand">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
            <SectionLabel>Cómo funciona</SectionLabel>
            <h2 className="max-w-2xl font-display text-4xl font-bold tracking-tight sm:text-5xl">
              De la noticia al MP3 en cinco pasos
            </h2>
            <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {STEPS.map((step, i) => (
                <li key={step.title} className="flex flex-col rounded-2xl border-2 border-ink bg-paper p-5">
                  <div className="flex items-center justify-between">
                    <span className="flex size-10 items-center justify-center rounded-full bg-ink font-display font-bold text-brand">
                      {i + 1}
                    </span>
                    <span className="text-xs font-semibold uppercase tracking-wide text-ink/60">{step.tool}</span>
                  </div>
                  <h3 className="mt-4 font-display text-xl font-bold">{step.title}</h3>
                  <p className="mt-2 text-sm text-ink/75">{step.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="formatos" className="scroll-mt-16">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
            <SectionLabel>Formatos</SectionLabel>
            <h2 className="max-w-2xl font-display text-4xl font-bold tracking-tight sm:text-5xl">
              Tres maneras de contar la IA
            </h2>
            <div className="mt-12 grid gap-6 md:grid-cols-3">
              {FORMATS.map((format) => (
                <article
                  key={format.name}
                  className="rounded-2xl border-2 border-ink p-6 transition hover:-translate-y-1 hover:shadow-[6px_6px_0_0_#ffd400]"
                >
                  <span className="rounded-full bg-ink px-3 py-1 text-xs font-bold text-brand">{format.tag}</span>
                  <h3 className="mt-5 font-display text-2xl font-bold">{format.name}</h3>
                  <p className="mt-2 text-ink/75">{format.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="unete" className="scroll-mt-16 bg-ink text-paper">
          <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 md:py-28 lg:grid-cols-[1fr_1.4fr]">
            <div>
              <SectionLabel>Únete</SectionLabel>
              <h2 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
                Forma parte del <span className="text-brand">proyecto</span>
              </h2>
              <p className="mt-6 text-lg text-paper/75">
                Buscamos gente con ganas de experimentar con IA, da igual lo que estudies. Puedes ayudar a mejorar los
                guiones, las voces, el código o a que el podcast llegue a más gente.
              </p>
              <ul className="mt-8 space-y-3">
                {["Rellena el formulario", "Te escribimos para conocerte", "Empiezas a colaborar en el área que elijas"].map(
                  (item, i) => (
                    <li key={item} className="flex items-center gap-3">
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand text-sm font-bold text-ink">
                        {i + 1}
                      </span>
                      {item}
                    </li>
                  ),
                )}
              </ul>
            </div>
            <SignupForm />
          </div>
        </section>
      </main>

      <footer className="border-t-2 border-paper/10 bg-ink text-paper">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-paper/60 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <Logo />
          <p>Asociación de inteligencia artificial · Universidad Carlos III de Madrid</p>
        </div>
      </footer>
    </>
  );
}
