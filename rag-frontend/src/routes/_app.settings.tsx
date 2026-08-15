import { createFileRoute } from "@tanstack/react-router";
import { FormEvent, useEffect, useState } from "react";
import { Mail, ShieldCheck, UserRound } from "lucide-react";
import { atlasAgentApi } from "@/lib/api/atlasAgentApi";
import { authApi } from "@/lib/api/authApi";
import { toApiError } from "@/lib/api/client";
import { useAuthStore } from "@/store/authStore";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/settings")({
  head: () => ({ meta: [{ title: "Settings — Atlas" }, { name: "description", content: "Workspace, profile, security, and integrations." }] }),
  component: Settings,
});

function Settings() {
  const user = useAuthStore(s => s.user); const hydrate = useAuthStore(s => s.hydrate);
  const [profile, setProfile] = useState({ name: user?.name ?? "", email: user?.email ?? "", current_password: "", new_password: "" });
  const [connection, setConnection] = useState<{ connected: boolean; email?: string; scopes: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { atlasAgentApi.googleConnection().then(setConnection).catch(err => setError(err instanceof Error ? err.message : "Unable to load Google connection")); }, []);
  const connect = async () => { try { const result = await atlasAgentApi.googleConnect(); window.location.assign(result.authorizationUrl); } catch (err) { setError(err instanceof Error ? err.message : "Unable to start Google OAuth"); } };
  useEffect(() => { if (user) setProfile(v => ({ ...v, name: user.name ?? "", email: user.email })); }, [user]);
  const saveProfile = async (event: FormEvent) => { event.preventDefault(); try { await authApi.updateMe({ name: profile.name, email: profile.email, ...(profile.new_password ? { current_password: profile.current_password, new_password: profile.new_password } : {}) }); await hydrate(); setProfile(v => ({...v,current_password:"",new_password:""})); toast.success("Profile updated"); } catch(e) { toast.error(toApiError(e).message); } };
  const field = "h-10 w-full rounded-md border border-border bg-surface px-3 text-sm outline-none focus:border-primary/50";
  return <div className="mx-auto max-w-3xl space-y-6"><div><h1 className="font-display text-2xl font-semibold">Settings</h1><p className="mt-1 text-sm text-muted-foreground">Profile, security, and connected services.</p></div>
    <section className="rounded-xl border border-border bg-card p-6"><h2 className="flex items-center gap-2 font-semibold"><UserRound className="h-4 w-4 text-primary"/>Profile</h2><form onSubmit={saveProfile} className="mt-4 grid gap-4 sm:grid-cols-2"><label className="text-xs text-muted-foreground">Name<input required value={profile.name} onChange={e=>setProfile({...profile,name:e.target.value})} className={`${field} mt-1.5`}/></label><label className="text-xs text-muted-foreground">Email<input required type="email" value={profile.email} onChange={e=>setProfile({...profile,email:e.target.value})} className={`${field} mt-1.5`}/></label><label className="text-xs text-muted-foreground">Current password<input type="password" value={profile.current_password} onChange={e=>setProfile({...profile,current_password:e.target.value})} className={`${field} mt-1.5`} placeholder="Required to change password"/></label><label className="text-xs text-muted-foreground">New password<input type="password" minLength={7} value={profile.new_password} onChange={e=>setProfile({...profile,new_password:e.target.value})} className={`${field} mt-1.5`} placeholder="At least 7 characters"/></label><button className="w-fit rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground">Save profile</button></form></section>
    <section className="rounded-xl border border-border bg-card p-6"><div className="flex items-start justify-between gap-4"><div><h2 className="flex items-center gap-2 font-semibold"><Mail className="h-4 w-4 text-primary" />Google Account</h2>{connection?.connected ? <><p className="mt-2 text-sm">Connected as {connection.email ?? "Google user"}</p><p className="mt-2 text-xs text-muted-foreground">Permissions: Gmail send and Google Docs read-only</p></> : <p className="mt-2 text-sm text-muted-foreground">Connect Google to import PRDs and send approved assignment notifications.</p>}</div>{!connection?.connected && <button onClick={connect} className="rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground">Connect Google</button>}</div>{error && <p className="mt-4 text-xs text-destructive">{error}</p>}<div className="mt-5 flex items-start gap-2 rounded-lg bg-surface p-3 text-xs text-muted-foreground"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />Provider tokens remain server-side and are encrypted at rest. Atlas never exposes them to the browser.</div></section></div>;
}
