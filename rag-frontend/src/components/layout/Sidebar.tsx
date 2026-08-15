import { Link, useRouterState } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  FolderKanban,
  FileText,
  CheckSquare,
  Sparkles,
  Users,
  Bell,
  Plug,
  BarChart3,
  Settings,
  Bot,
  GitBranch,
  Calendar,
  Workflow,
  Activity,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { cn } from "@/lib/utils";

type NavItem = { label: string; to: string; icon: React.ElementType; badge?: string };

const primaryNav: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Projects", to: "/projects", icon: FolderKanban },
  { label: "Documents", to: "/documents", icon: FileText },
  { label: "Tasks", to: "/tasks", icon: CheckSquare },
  { label: "AI Insights", to: "/ai", icon: Sparkles, badge: "AI" },
  { label: "AI Copilot", to: "/copilot", icon: Bot },
  { label: "Team", to: "/team", icon: Users },
];

const systemNav: NavItem[] = [
  { label: "Notifications", to: "/notifications", icon: Bell },
  { label: "Integrations", to: "/integrations", icon: Plug },
  { label: "Analytics", to: "/analytics", icon: BarChart3 },
  { label: "Settings", to: "/settings", icon: Settings },
];

const futureNav: NavItem[] = [
  { label: "Knowledge Graph", to: "/knowledge-graph", icon: GitBranch },
  { label: "Sprint Planning", to: "/sprints", icon: Calendar },
  { label: "Automation", to: "/automation", icon: Workflow },
  { label: "CI/CD", to: "/cicd", icon: Activity },
];

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggle = useUIStore((s) => s.toggleSidebar);
  const pathname = useRouterState({ select: (r) => r.location.pathname });

  return (
    <aside
      className={cn(
        "relative hidden h-screen flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-300 ease-out md:flex",
        collapsed ? "w-[72px]" : "w-[260px]",
      )}
    >
      {/* Brand */}
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-4">
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
          <Sparkles className="h-4 w-4 text-primary-foreground" />
          <span className="absolute -inset-0.5 -z-10 rounded-lg bg-primary/40 blur-md" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate font-display text-sm font-semibold">Atlas</div>
            <div className="truncate text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Intelligence OS
            </div>
          </div>
        )}
      </div>

      {/* Nav sections */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <SidebarSection label="Workspace" items={primaryNav} pathname={pathname} collapsed={collapsed} />
        <SidebarSection label="System" items={systemNav} pathname={pathname} collapsed={collapsed} />
        <SidebarSection
          label="Future"
          items={futureNav}
          pathname={pathname}
          collapsed={collapsed}
          dim
        />
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={toggle}
        className="m-3 flex items-center justify-center gap-2 rounded-md border border-sidebar-border bg-sidebar-accent/40 px-2 py-2 text-xs text-muted-foreground transition hover:bg-sidebar-accent hover:text-foreground"
      >
        {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  );
}

function SidebarSection({
  label,
  items,
  pathname,
  collapsed,
  dim,
}: {
  label: string;
  items: NavItem[];
  pathname: string;
  collapsed: boolean;
  dim?: boolean;
}) {
  return (
    <div className="mb-4">
      {!collapsed && (
        <div className="mb-2 px-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground/70">
          {label}
        </div>
      )}
      <ul className="space-y-0.5">
        {items.map((item) => {
          const active = pathname === item.to || pathname.startsWith(item.to + "/");
          return (
            <li key={item.to}>
              <Link
                to={item.to}
                className={cn(
                  "group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-sm transition",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground",
                  dim && !active && "opacity-60",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r bg-primary shadow-[0_0_12px_var(--primary)]"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <item.icon className={cn("h-4 w-4 shrink-0", active && "text-primary")} />
                {!collapsed && (
                  <>
                    <span className="flex-1 truncate">{item.label}</span>
                    {item.badge && (
                      <span className="rounded-sm bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
