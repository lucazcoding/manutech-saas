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
      setError(err instanceof Error ? err.message : "Credenciais inválidas ou serviço indisponível.");
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
        <p>Entre com suas credenciais</p>

        <label className="field">
          <span>Usuário</span>
          <input
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            autoComplete="username"
            placeholder="admin"
            required
          />
        </label>
        <label className="field">
          <span>Senha</span>
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
          Entrar
        </button>
        {error ? <div className="form-error">{error}</div> : null}
        <small className="login-hint">
          Acesso padrão de desenvolvimento: <code>admin</code> / <code>admin123</code>
        </small>
        <details className="login-hint" style={{ textAlign: "left" }}>
          <summary style={{ cursor: "pointer", textAlign: "center" }}>Perfis do sistema e o que cada um faz</summary>
          <ul style={{ margin: "10px 0 0", paddingLeft: 18, lineHeight: 1.55 }}>
            <li><strong>Administrador</strong> — gerencia usuários, operação, finanças e auditoria.</li>
            <li><strong>Supervisor</strong> — cria e atribui ordens, gerencia materiais e custos.</li>
            <li><strong>Técnico</strong> — executa as OS que estão com você (inicia e conclui).</li>
            <li><strong>Atendente</strong> — registra novas ordens vindas do cliente (balcão/telefone).</li>
          </ul>
        </details>
      </form>
    </main>
  );
}
