export default function HomePage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <section className="mx-auto max-w-6xl px-6 py-16">
        <p className="text-sm uppercase tracking-[0.2em] text-zinc-500">Lead Agent</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight md:text-6xl">
          AI-powered lead discovery for software agencies.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-zinc-400">
          Find companies, analyze opportunities, score leads, and prepare personalized outreach with Kimi K3.
        </p>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {[
            ["Leads found", "0"],
            ["High opportunity", "0"],
            ["Contacted", "0"],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6">
              <p className="text-sm text-zinc-500">{label}</p>
              <p className="mt-2 text-3xl font-semibold">{value}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
