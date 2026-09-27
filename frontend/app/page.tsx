import { getBackendReadiness } from "@/lib/api";

export default async function Home() {
  const readiness = await getBackendReadiness();

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>AI Knowledge Assistant</h1>
      <p>v0.1 Foundation skeleton.</p>

      <section
        style={{
          marginTop: "1.5rem",
          padding: "1rem",
          border: "1px solid #ddd",
          borderRadius: "8px",
          maxWidth: "480px",
        }}
      >
        <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>
          Backend connectivity
        </h2>
        {readiness.error ? (
          <p style={{ color: "#b00020" }}>
            Could not reach backend: {readiness.error}
          </p>
        ) : (
          <>
            <p>
              Reachable: <strong>{readiness.ok ? "yes" : "no"}</strong>
            </p>
            <p>
              Status: <code>{readiness.data?.status}</code>
            </p>
            {readiness.data?.database && (
              <p>
                Database: <code>{readiness.data.database}</code>
              </p>
            )}
          </>
        )}
      </section>
    </main>
  );
}
