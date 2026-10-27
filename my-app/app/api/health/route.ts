export const dynamic = "force-dynamic";

export async function GET() {
  const missing = ["APP_ENV", "BILLING_API_URL"].filter((key) => !process.env[key]);
  return Response.json(
    { status: missing.length ? "unhealthy" : "ok", missing },
    { status: missing.length ? 503 : 200 },
  );
}
