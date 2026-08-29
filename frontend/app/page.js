"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const industries = [
  "agencias de viajes",
  "hoteles",
  "inmobiliarias",
  "restaurantes",
  "constructoras",
  "gimnasios",
  "clinicas",
  "dentistas",
  "veterinarias",
  "cafeterias",
];

export default function HomePage() {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState({ total: 0, high_priority: 0, contacted: 0, replied: 0, average_score: 0 });
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedLead, setSelectedLead] = useState(null);
  const [filters, setFilters] = useState({ minScore: "", industry: "", city: "" });
  const [search, setSearch] = useState({
    industry: "agencias de viajes",
    city: "Buenos Aires",
    country: "Argentina",
    limit: 3,
    minimum_score: 50,
    notify_each: true,
  });

  async function request(path, options) {
    const response = await fetch(`${API_URL}${path}`, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Error de conexión con el backend");
    return data;
  }

  async function loadDashboard() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (filters.minScore) params.set("min_score", filters.minScore);
      if (filters.industry) params.set("industry", filters.industry);
      if (filters.city) params.set("city", filters.city);

      const [leadData, statsData] = await Promise.all([
        request(`/api/leads?${params.toString()}`),
        request("/api/leads/stats"),
      ]);
      setLeads(leadData.leads || []);
      setStats(statsData);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  async function runSearch(event) {
    event.preventDefault();
    setRunning(true);
    setMessage("Buscando y analizando nuevos leads...");
    try {
      const data = await request("/api/discovery/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...search,
          limit: Number(search.limit),
          minimum_score: Number(search.minimum_score),
        }),
      });
      setMessage(`Listo: ${data.analyzed} analizados, ${data.qualified} calificados y ${data.skipped_duplicates} duplicados omitidos.`);
      await loadDashboard();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setRunning(false);
    }
  }

  const topLead = useMemo(() => leads.reduce((best, lead) => (!best || (lead.score || 0) > (best.score || 0) ? lead : best), null), [leads]);

  const scoreClass = (score) => {
    if (score >= 75) return "bg-emerald-500/15 text-emerald-300 border-emerald-500/20";
    if (score >= 50) return "bg-amber-500/15 text-amber-300 border-amber-500/20";
    return "bg-zinc-800 text-zinc-400 border-zinc-700";
  };

  return (
    <main className="min-h-screen bg-[#09090b] text-zinc-100">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-8">
        <header className="mb-8 flex flex-col gap-4 border-b border-zinc-800 pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-400">Lead Agent</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Pipeline comercial con IA</h1>
            <p className="mt-2 text-sm text-zinc-500">Descubrí empresas, analizá oportunidades y priorizá prospectos desde un solo lugar.</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 px-4 py-3 text-sm text-zinc-400">
            API: <span className="text-zinc-200">{API_URL}</span>
          </div>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["Leads", stats.total],
            ["Alta prioridad", stats.high_priority],
            ["Score promedio", stats.average_score],
            ["Contactados", stats.contacted],
            ["Respondieron", stats.replied],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-5 shadow-sm">
              <p className="text-sm text-zinc-500">{label}</p>
              <p className="mt-2 text-3xl font-semibold">{value}</p>
            </div>
          ))}
        </section>

        <div className="mt-6 grid gap-6 xl:grid-cols-[380px_1fr]">
          <aside className="space-y-6">
            <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-5">
              <div className="mb-5">
                <h2 className="font-semibold">Buscar nuevos leads</h2>
                <p className="mt-1 text-sm text-zinc-500">El agente descarta duplicados antes de gastar llamadas de IA.</p>
              </div>

              <form onSubmit={runSearch} className="space-y-4">
                <Field label="Rubro">
                  <select className="input" value={search.industry} onChange={(e) => setSearch({ ...search, industry: e.target.value })}>
                    {industries.map((item) => <option key={item}>{item}</option>)}
                  </select>
                </Field>
                <Field label="Ciudad">
                  <input className="input" value={search.city} onChange={(e) => setSearch({ ...search, city: e.target.value })} />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Cantidad">
                    <input className="input" type="number" min="1" max="50" value={search.limit} onChange={(e) => setSearch({ ...search, limit: e.target.value })} />
                  </Field>
                  <Field label="Score mínimo">
                    <input className="input" type="number" min="0" max="100" value={search.minimum_score} onChange={(e) => setSearch({ ...search, minimum_score: e.target.value })} />
                  </Field>
                </div>
                <label className="flex items-center gap-3 text-sm text-zinc-400">
                  <input type="checkbox" checked={search.notify_each} onChange={(e) => setSearch({ ...search, notify_each: e.target.checked })} />
                  Enviarme email por cada lead
                </label>
                <button disabled={running} className="w-full rounded-xl bg-emerald-400 px-4 py-3 font-semibold text-zinc-950 transition hover:bg-emerald-300 disabled:cursor-wait disabled:opacity-60">
                  {running ? "Analizando..." : "Ejecutar búsqueda"}
                </button>
              </form>

              {message && <p className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-400">{message}</p>}
            </section>

            {topLead && (
              <section className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Mejor oportunidad visible</p>
                <h3 className="mt-3 text-lg font-semibold">{topLead.company_name}</h3>
                <p className="mt-1 text-sm text-zinc-400">{topLead.opportunity}</p>
                <div className="mt-4 text-3xl font-semibold">{topLead.score}<span className="text-sm text-zinc-500">/100</span></div>
              </section>
            )}
          </aside>

          <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70">
            <div className="border-b border-zinc-800 p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="font-semibold">Leads guardados</h2>
                  <p className="mt-1 text-sm text-zinc-500">{loading ? "Cargando..." : `${leads.length} resultados visibles`}</p>
                </div>
                <div className="grid gap-2 sm:grid-cols-3">
                  <input className="input" placeholder="Ciudad" value={filters.city} onChange={(e) => setFilters({ ...filters, city: e.target.value })} />
                  <input className="input" placeholder="Rubro" value={filters.industry} onChange={(e) => setFilters({ ...filters, industry: e.target.value })} />
                  <div className="flex gap-2">
                    <input className="input min-w-0" type="number" placeholder="Score" value={filters.minScore} onChange={(e) => setFilters({ ...filters, minScore: e.target.value })} />
                    <button onClick={loadDashboard} className="rounded-xl border border-zinc-700 px-3 text-sm hover:bg-zinc-800">Filtrar</button>
                  </div>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="border-b border-zinc-800 text-xs uppercase tracking-wider text-zinc-500">
                  <tr>
                    <th className="px-5 py-4">Empresa</th>
                    <th className="px-5 py-4">Score</th>
                    <th className="px-5 py-4">Rubro</th>
                    <th className="px-5 py-4">Ciudad</th>
                    <th className="px-5 py-4">Servicio sugerido</th>
                    <th className="px-5 py-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/80">
                  {leads.map((lead) => (
                    <tr key={lead.id} className="hover:bg-zinc-800/30">
                      <td className="px-5 py-4">
                        <p className="font-medium">{lead.company_name}</p>
                        <p className="mt-1 max-w-[220px] truncate text-xs text-zinc-500">{lead.website || lead.contact_email || "Sin web/contacto"}</p>
                      </td>
                      <td className="px-5 py-4"><span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${scoreClass(lead.score || 0)}`}>{lead.score ?? "-"}</span></td>
                      <td className="px-5 py-4 text-zinc-400">{lead.industry || "-"}</td>
                      <td className="px-5 py-4 text-zinc-400">{lead.city || "-"}</td>
                      <td className="max-w-[260px] truncate px-5 py-4 text-zinc-300">{lead.opportunity || "-"}</td>
                      <td className="px-5 py-4 text-right"><button onClick={() => setSelectedLead(lead)} className="rounded-lg border border-zinc-700 px-3 py-2 text-xs hover:bg-zinc-800">Ver análisis</button></td>
                    </tr>
                  ))}
                  {!loading && leads.length === 0 && (
                    <tr><td colSpan="6" className="px-5 py-16 text-center text-zinc-500">Todavía no hay leads para mostrar.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>

      {selectedLead && <LeadModal lead={selectedLead} onClose={() => setSelectedLead(null)} />}
    </main>
  );
}

function Field({ label, children }) {
  return <label className="block"><span className="mb-2 block text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</span>{children}</label>;
}

function LeadModal({ lead, onClose }) {
  const analysis = lead.analysis || {};
  const metadata = analysis.discovery_metadata || {};
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" onClick={onClose}>
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-zinc-700 bg-zinc-950 p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-zinc-500">Lead #{lead.id}</p>
            <h2 className="mt-1 text-2xl font-semibold">{lead.company_name}</h2>
            <p className="mt-2 text-zinc-400">{lead.industry} · {lead.city}</p>
          </div>
          <button onClick={onClose} className="rounded-lg border border-zinc-700 px-3 py-2 text-sm">Cerrar</button>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Info label="Score" value={`${lead.score ?? "-"}/100`} />
          <Info label="Email" value={lead.contact_email || "No encontrado"} />
          <Info label="Teléfono" value={metadata.phone || "No encontrado"} />
        </div>

        {lead.website && <a href={lead.website} target="_blank" rel="noreferrer" className="mt-5 inline-block text-sm text-emerald-400 hover:underline">Abrir sitio web ↗</a>}

        <Detail title="Resumen" text={analysis.summary} />
        <ListDetail title="Problemas detectados" items={analysis.problems} />
        <ListDetail title="Oportunidades" items={analysis.opportunities} />
        <Detail title="Servicio recomendado" text={analysis.recommended_service || lead.opportunity} />
        <Detail title="Mensaje de contacto sugerido" text={lead.outreach_draft || analysis.outreach_message} boxed />
      </div>
    </div>
  );
}

function Info({ label, value }) {
  return <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4"><p className="text-xs uppercase tracking-wider text-zinc-500">{label}</p><p className="mt-2 break-words text-sm">{value}</p></div>;
}

function Detail({ title, text, boxed = false }) {
  if (!text) return null;
  return <section className="mt-6"><h3 className="mb-2 text-sm font-semibold">{title}</h3><p className={`text-sm leading-6 text-zinc-400 ${boxed ? "rounded-xl border border-zinc-800 bg-zinc-900 p-4" : ""}`}>{text}</p></section>;
}

function ListDetail({ title, items }) {
  if (!items?.length) return null;
  return <section className="mt-6"><h3 className="mb-2 text-sm font-semibold">{title}</h3><ul className="space-y-2 text-sm text-zinc-400">{items.map((item, index) => <li key={index} className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-3">{item}</li>)}</ul></section>;
}
