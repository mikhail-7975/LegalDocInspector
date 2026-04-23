import { useCallback, useState, type FormEvent } from "react";
import { login } from "../api/client";

type Props = {
  onLoggedIn: (displayName: string) => void;
};

export function LoginScreen({ onLoggedIn }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setBusy(true);
      setError(null);
      try {
        const r = await login(username.trim(), password);
        const u = r.user ?? username.trim();
        onLoggedIn(`${u}@example.local`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка входа");
      } finally {
        setBusy(false);
      }
    },
    [onLoggedIn, password, username]
  );

  return (
    <div className="login-only">
      <div className="login-only__card panel">
        <h1 className="login-only__title">LegalDocInspector</h1>
        <p className="hint-muted" style={{ marginTop: 0 }}>
          Войдите, чтобы продолжить работу с пакетом документов.
        </p>
        <form className="login-card" onSubmit={onSubmit} style={{ margin: 0 }}>
          <label htmlFor="login-username">Логин</label>
          <input
            id="login-username"
            name="username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={busy}
          />
          <label htmlFor="login-password">Пароль</label>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={busy}
          />
          {error ? (
            <p className="login-only__error" role="alert">
              {error}
            </p>
          ) : null}
          <button type="submit" className="btn btn--primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Вход…" : "Войти"}
          </button>
        </form>
      </div>
    </div>
  );
}
