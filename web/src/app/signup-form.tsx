"use client";

import { useActionState } from "react";
import { signup, type SignupState } from "./actions";
import { AREAS } from "./areas";

const initialState: SignupState = {
  status: "idle",
  message: "",
  errors: {},
  fields: { nombre: "", email: "", estudios: "", area: "", motivacion: "", consentimiento: false },
};

const inputClass =
  "w-full rounded-lg border-2 border-ink bg-white px-4 py-3 text-ink placeholder:text-ink/40 outline-none transition focus:border-ink focus:ring-4 focus:ring-brand aria-invalid:border-red-600";

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="mt-1.5 text-sm font-medium text-red-700">
      {message}
    </p>
  );
}

export function SignupForm() {
  const [state, formAction, pending] = useActionState(signup, initialState);
  const { errors, fields } = state;

  if (state.status === "success") {
    return (
      <div className="rounded-2xl border-2 border-ink bg-brand p-8 text-ink shadow-[6px_6px_0_0_#0a0a0a]" role="status">
        <p className="font-display text-3xl font-bold">¡Gracias por apuntarte!</p>
        <p className="mt-3 text-lg">{state.message}</p>
      </div>
    );
  }

  return (
    <form
      action={formAction}
      noValidate
      className="rounded-2xl border-2 border-ink bg-white p-6 text-ink shadow-[6px_6px_0_0_#0a0a0a] sm:p-8"
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="nombre" className="mb-1.5 block font-semibold">
            Nombre
          </label>
          <input
            id="nombre"
            name="nombre"
            autoComplete="name"
            required
            maxLength={120}
            defaultValue={fields.nombre}
            aria-invalid={!!errors.nombre}
            aria-describedby="nombre-error"
            className={inputClass}
          />
          <FieldError id="nombre-error" message={errors.nombre} />
        </div>

        <div>
          <label htmlFor="email" className="mb-1.5 block font-semibold">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
            placeholder="tu@correo.com"
            defaultValue={fields.email}
            aria-invalid={!!errors.email}
            aria-describedby="email-error"
            className={inputClass}
          />
          <FieldError id="email-error" message={errors.email} />
        </div>

        <div>
          <label htmlFor="estudios" className="mb-1.5 block font-semibold">
            Estudios <span className="font-normal text-ink/60">(opcional)</span>
          </label>
          <input
            id="estudios"
            name="estudios"
            maxLength={160}
            placeholder="Ej. 3º de Informática"
            defaultValue={fields.estudios}
            aria-invalid={!!errors.estudios}
            aria-describedby="estudios-error"
            className={inputClass}
          />
          <FieldError id="estudios-error" message={errors.estudios} />
        </div>

        <div>
          <label htmlFor="area" className="mb-1.5 block font-semibold">
            ¿En qué te gustaría participar?
          </label>
          {/* React's form reset ignores an updated defaultValue on <select>; remounting applies it. */}
          <select
            key={fields.area}
            id="area"
            name="area"
            required
            defaultValue={fields.area}
            aria-invalid={!!errors.area}
            aria-describedby="area-error"
            className={inputClass}
          >
            <option value="" disabled>
              Elige una opción
            </option>
            {Object.entries(AREAS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <FieldError id="area-error" message={errors.area} />
        </div>

        <div className="sm:col-span-2">
          <label htmlFor="motivacion" className="mb-1.5 block font-semibold">
            ¿Por qué te interesa? <span className="font-normal text-ink/60">(opcional)</span>
          </label>
          <textarea
            id="motivacion"
            name="motivacion"
            rows={3}
            maxLength={1000}
            defaultValue={fields.motivacion}
            aria-invalid={!!errors.motivacion}
            aria-describedby="motivacion-error"
            className={inputClass}
          />
          <FieldError id="motivacion-error" message={errors.motivacion} />
        </div>
      </div>

      <div className="absolute -left-[9999px]" aria-hidden="true">
        <label htmlFor="web">No rellenar</label>
        <input id="web" name="web" tabIndex={-1} autoComplete="off" />
      </div>

      <div className="mt-5">
        <label className="flex items-start gap-3 text-sm">
          <input
            type="checkbox"
            name="consentimiento"
            defaultChecked={fields.consentimiento}
            aria-invalid={!!errors.consentimiento}
            aria-describedby="consentimiento-error"
            className="mt-0.5 size-5 shrink-0 accent-ink"
          />
          <span>
            Acepto que InnovAI UC3M guarde estos datos para contactarme sobre el proyecto. No se usarán para nada más.
          </span>
        </label>
        <FieldError id="consentimiento-error" message={errors.consentimiento} />
      </div>

      <div className="mt-6 flex flex-col-reverse items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p aria-live="polite" className="text-sm font-medium text-red-700">
          {state.status === "error" ? state.message : ""}
        </p>
        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-full border-2 border-ink bg-brand px-8 py-3 font-bold text-ink transition hover:-translate-y-0.5 hover:shadow-[4px_4px_0_0_#0a0a0a] disabled:translate-y-0 disabled:opacity-60 disabled:shadow-none sm:w-auto"
        >
          {pending ? "Enviando…" : "Quiero unirme"}
        </button>
      </div>
    </form>
  );
}
