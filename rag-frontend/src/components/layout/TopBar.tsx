import { Search, Command, Bell, Sparkles, Plus } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { Link } from "@tanstack/react-router";

export function TopBar() {
  const setCommand = useUIStore((s) => s.setCommand);
  const setAIPanel = useUIStore((s) => s.setAIPanel);
  const setNotifications = useUIStore((s) => s.setNotifications);
  const user = useAuthStore((s) => s.user);

  const initials = (user?.name || user?.email || "U")
    .split(/\s|@/)
    .filter(Boolean)
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-border bg-background/70 px-3 backdrop-blur-xl sm:gap-3 sm:px-6">
      {/* Command */}
      <button
        onClick={() => setCommand(true)}
        className="group hidden h-9 min-w-0 flex-1 max-w-xl items-center gap-2 rounded-md border border-border bg-surface/60 px-3 text-sm text-muted-foreground transition hover:border-border-strong hover:bg-surface sm:flex"
      >
        <Search className="h-4 w-4" />
        <span>Search projects, documents, tasks…</span>
        <span className="ml-auto flex items-center gap-1 rounded border border-border bg-background/60 px-1.5 py-0.5 font-mono text-[10px]">
          <Command className="h-3 w-3" /> K
        </span>
      </button>

      <div className="ml-auto flex items-center gap-2">
        <button className="hidden h-9 items-center gap-2 rounded-md border border-border bg-surface/60 px-3 text-xs font-medium transition hover:bg-surface md:inline-flex">
          <Plus className="h-3.5 w-3.5" /> New Project
        </button>
        <button
          onClick={() => setAIPanel(true)}
          className="relative inline-flex h-9 items-center gap-2 rounded-md border border-primary/30 bg-primary/10 px-2 text-xs font-medium text-primary transition hover:bg-primary/20 sm:px-3"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">AI Assistant</span>
          <span className="absolute -right-1 -top-1 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
        </button>
        <button
          onClick={() => setNotifications(true)}
          className="relative flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface/60 transition hover:bg-surface"
        >
          <Bell className="h-4 w-4" />
        </button>
        <Link to="/settings" aria-label="Open profile settings" className="flex h-9 items-center gap-2 rounded-md border border-border bg-surface/60 pl-1 pr-3 transition hover:bg-surface">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-gradient-to-br from-primary to-accent text-[11px] font-semibold text-primary-foreground">
            {initials}
          </div>
          <div className="hidden text-xs leading-tight md:block">
            <div className="font-medium">{user?.name || user?.email?.split("@")[0] || "Guest"}</div>
            <div className="text-[10px] text-muted-foreground">{user?.role || "Member"}</div>
          </div>
        </Link>
      </div>
    </header>
  );
}
