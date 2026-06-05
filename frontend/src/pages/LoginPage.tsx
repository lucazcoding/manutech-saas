import { FormEvent, useState } from "react";
import { Loader2, Wrench } from "lucide-react";

interface LoginPageProps {
  onLogin: (login: string, password: string) => Promise<void>;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onLogin(login, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Credenciais invalidas ou servico indisponivel.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-screen">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-icon">
          <Wrench size={64} />
        </div>
        <h1>MANUTECH</h1>
        <p>Introduza as suas credenciais</p>

        <label className="field">
          <span>Utilizador</span>
          <input
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            autoComplete="username"
            placeholder="admin@manutech.com"
            required
          />
        </label>
        <label className="field">
          <span>Palavra-passe</span>
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <button className="button button-primary button-full" type="submit" disabled={loading}>
          {loading ? <Loader2 className="spin" size={18} /> : null}
          Entrar no Sistema
        </button>
        {error ? <div className="form-error">{error}</div> : null}
      </form>
    </main>
  );
}
