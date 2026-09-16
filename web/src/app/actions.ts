"use server";

import { createClient } from "@supabase/supabase-js";
import { AREAS } from "./areas";

type Fields = {
  nombre: string;
  email: string;
  estudios: string;
  area: string;
  motivacion: string;
  consentimiento: boolean;
};

export type SignupState = {
  status: "idle" | "success" | "error";
  message: string;
  errors: Partial<Record<keyof Fields, string>>;
  fields: Fields;
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function text(formData: FormData, name: string) {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

export async function signup(_prev: SignupState, formData: FormData): Promise<SignupState> {
  const fields: Fields = {
    nombre: text(formData, "nombre"),
    email: text(formData, "email").toLowerCase(),
    estudios: text(formData, "estudios"),
    area: text(formData, "area"),
    motivacion: text(formData, "motivacion"),
    consentimiento: formData.get("consentimiento") === "on",
  };

  // Honeypot: invisible for people, bots tend to fill it in.
  if (text(formData, "web")) {
    return { status: "success", message: "", errors: {}, fields };
  }

  const errors: SignupState["errors"] = {};
  if (fields.nombre.length < 2 || fields.nombre.length > 120) errors.nombre = "Escribe tu nombre.";
  if (!EMAIL_PATTERN.test(fields.email) || fields.email.length > 254) errors.email = "Revisa el email.";
  if (fields.estudios.length > 160) errors.estudios = "Máximo 160 caracteres.";
  if (!Object.hasOwn(AREAS, fields.area)) errors.area = "Elige un área.";
  if (fields.motivacion.length > 1000) errors.motivacion = "Máximo 1000 caracteres.";
  if (!fields.consentimiento) errors.consentimiento = "Necesitamos tu permiso para contactarte.";

  if (Object.keys(errors).length > 0) {
    return { status: "error", message: "Revisa los campos marcados.", errors, fields };
  }

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_ANON_KEY;
  if (!url || !key) {
    console.error("Faltan SUPABASE_URL o SUPABASE_ANON_KEY");
    return { status: "error", message: "Las inscripciones no están disponibles ahora mismo.", errors: {}, fields };
  }

  const supabase = createClient(url, key, { auth: { persistSession: false } });
  const { error } = await supabase.from("inscripciones").insert({
    nombre: fields.nombre,
    email: fields.email,
    estudios: fields.estudios || null,
    area: fields.area,
    motivacion: fields.motivacion || null,
  });

  if (error?.code === "23505") {
    return { status: "success", message: "Ya estabas inscrito/a. Te escribiremos pronto.", errors: {}, fields };
  }
  if (error) {
    console.error("Error guardando inscripción", error);
    return { status: "error", message: "No hemos podido guardar tu inscripción. Inténtalo de nuevo.", errors: {}, fields };
  }

  return { status: "success", message: "¡Listo! Te escribiremos pronto.", errors: {}, fields };
}
