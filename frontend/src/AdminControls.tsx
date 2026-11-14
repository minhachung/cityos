import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle2, KeyRound, LoaderCircle, LogOut, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { getAdminStatus, loginAdmin, logoutAdmin } from './api';
import type { AdminStatus } from './types';

type Props = { onSync: () => Promise<void>; syncing: boolean };

export default function AdminControls({ onSync, syncing }: Props) {
  const [admin, setAdmin] = useState<AdminStatus>({
    enabled: false, requires_auth: import.meta.env.PROD, authenticated: false
  });
  const [checking, setChecking] = useState(true);
  const [dialog, setDialog] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let active = true;
    getAdminStatus().then(s => { if (active) setAdmin(s); })
      .catch(() => { if (active) setMessage('Admin status is unavailable.'); })
      .finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, []);

  async function signIn(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      await loginAdmin(password);
      setAdmin(s => ({ ...s, authenticated: true }));
      setPassword('');
      setDialog(false);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to sign in');
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    setMessage('');
    try {
      await logoutAdmin();
      setAdmin(s => ({ ...s, authenticated: false }));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to sign out');
    } finally { setBusy(false); }
  }

  const canSync = !admin.requires_auth || admin.authenticated;
  return <>
    <div className="admin-controls">
      {checking ? <span className="btn btn-public-demo"><LoaderCircle size={15}/> Checking access…</span> : <>
        {canSync ? <>
          {admin.authenticated && <span className="admin-signed"><CheckCircle2 size={15}/> Admin</span>}
          <button className="btn btn-primary" onClick={onSync} disabled={syncing || busy}>
            <RefreshCw size={16} className={syncing ? 'spin' : ''}/>{syncing ? 'Syncing NYC 311…' : 'Sync NYC 311 data'}
          </button>
          {admin.authenticated && <button className="admin-link" onClick={signOut} disabled={busy}><LogOut size={14}/> Sign out</button>}
        </> : <>
          <span className="btn btn-public-demo"><ShieldCheck size={16}/> Read-only public demo</span>
          <button className="admin-link" onClick={() => {setMessage(''); setDialog(true);}}><KeyRound size={15}/> Admin sign in</button>
        </>}
      </>}
      {!dialog && message && <span className="admin-error-inline" role="alert">{message}</span>}
    </div>
    {dialog && <div className="admin-modal-backdrop" onMouseDown={e => {
      if (e.target === e.currentTarget && !busy) setDialog(false);
    }}>
      <div className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="admin-modal-title">
        <button className="admin-modal-close" aria-label="Close" disabled={busy} onClick={() => {setDialog(false); setPassword('');}}><X size={19}/></button>
        <div className="admin-modal-icon"><KeyRound size={22}/></div>
        <h2 id="admin-modal-title">CityOS admin</h2>
        <p>Public visitors can explore requests and simulations. Only the owner can refresh NYC 311 data.</p>
        {!admin.enabled ? <div className="admin-login-message">Owner setup required: configure <code>CITYOS_ADMIN_PASSWORD_HASH</code> in Render → Environment.</div>
          : <form onSubmit={signIn}>
            <label htmlFor="cityos-admin-password">Admin password</label>
            <input id="cityos-admin-password" type="password" autoComplete="current-password"
              value={password} onChange={e=>setPassword(e.target.value)}
              minLength={1} maxLength={1024} required autoFocus />
            {message && <div className="admin-login-error" role="alert">{message}</div>}
            <button className="btn btn-primary" type="submit" disabled={busy || !password}>
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </form>}
      </div>
    </div>}
  </>;
}
