export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-sky-100 to-white p-6 text-slate-900">
      <section className="w-full max-w-xl rounded-2xl bg-white p-10 text-center shadow-lg">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
          Frontend Welcome
        </p>
        <h1 className="text-4xl font-bold">Welcome to your Next.js app</h1>
        <p className="mt-4 text-lg text-slate-600">
          This is a simple frontend project page for your CI/CD demo.
        </p>
      </section>
    </main>
  );
}
