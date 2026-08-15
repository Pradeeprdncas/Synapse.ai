import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Sparkles,
  AlertTriangle,
  GitBranch,
  FileText,
  Users,
  ListChecks,
  Layers,
  CalendarDays,
  Lightbulb,
  Network,
  RefreshCw,
  Bot,
} from "lucide-react";
import { useProjectStore } from "@/store/projectStore";
import { useAIStore } from "@/store/aiStore";
import { useTaskStore } from "@/store/taskStore";
import { useDocumentStore } from "@/store/documentStore";
import { Pill, Skeleton, EmptyState } from "@/components/common/Primitives";
import { ModuleNode } from "@/components/projects/ModuleNode";
import { DocumentUploader } from "@/components/documents/DocumentUploader";
import { cn } from "@/lib/utils";
import { AtlasAgentPanel } from "@/components/projects/AtlasAgentPanel";

export const Route = createFileRoute("/_app/projects/$projectId")({
  head: ({ params }) => ({
    meta: [
      { title: `Workspace ${params.projectId} — Atlas` },
      {
        name: "description",
        content: "AI-generated execution workspace: modules, tasks, risks, dependencies, and recommendations.",
      },
    ],
  }),
  component: ProjectWorkspace,
});

const SECTIONS = [
  { id: "atlas-agent", label: "Atlas Agent", icon: Bot },
  { id: "overview", label: "Overview", icon: Layers },
  { id: "ai-summary", label: "AI Summary", icon: Sparkles },
  { id: "modules", label: "Modules", icon: Network },
  { id: "tasks", label: "Tasks", icon: ListChecks },
  { id: "checklists", label: "Checklists", icon: ListChecks },
  { id: "risks", label: "Risks", icon: AlertTriangle },
  { id: "dependencies", label: "Dependencies", icon: GitBranch },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "team", label: "Team Activity", icon: Users },
  { id: "recommendations", label: "Recommendations", icon: Lightbulb },
  { id: "sprint", label: "Sprint Planning", icon: CalendarDays },
] as const;

function ProjectWorkspace() {
  const { projectId } = Route.useParams();
  const project = useProjectStore((s) => s.byId[projectId]);
  const fetchProject = useProjectStore((s) => s.fetchProject);
  const aiSummary = useAIStore((s) => s.summaries[projectId]);
  const aiModules = useAIStore((s) => s.modules[projectId]);
  const aiRisks = useAIStore((s) => s.risks[projectId]);
  const aiLoading = useAIStore((s) => s.loading[projectId]);
  const fetchAI = useAIStore((s) => s.fetchAll);
  const triggerAnalysis = useAIStore((s) => s.triggerAnalysis);
  const projectTasks = useTaskStore((s) => s.byProject[projectId]);
  const fetchTasks = useTaskStore((s) => s.fetchByProject);
  const storedDocuments = useDocumentStore((s) => s.documents);
  const fetchDocuments = useDocumentStore((s) => s.fetch);

  const [active, setActive] = useState<string>("overview");

  useEffect(() => {
    void fetchProject(projectId);
    void fetchAI(projectId);
    void fetchTasks(projectId);
    void fetchDocuments(projectId);
  }, [projectId, fetchProject, fetchAI, fetchTasks, fetchDocuments]);

  // Prefer AI store data; fall back to project payload — backend may return either shape.
  const summary = aiSummary?.summary ?? (project?.ai_summary as string | undefined);
  const modules = useMemo(
    () => aiModules ?? ((project?.modules ?? []) as Record<string, any>[]),
    [aiModules, project?.modules],
  );
  const risks = useMemo(
    () => aiRisks ?? ((project?.risks ?? []) as Record<string, any>[]),
    [aiRisks, project?.risks],
  );
  const tasks = (projectTasks ?? project?.tasks ?? []) as Record<string, any>[];
  const checklistItems = useMemo<Record<string, any>[]>(() => {
    const fromTasks = tasks.flatMap((task) =>
      ((task.checklist ?? task.checklists ?? []) as Record<string, any>[]).map((item) => ({
        ...item,
        task_title: task.title ?? task.name,
      })),
    );
    const fromModules = modules.flatMap((module) => ((module as any).checklist ?? []) as Record<string, any>[]);
    const projectLevel = (project?.checklists ?? project?.checklist ?? []) as Record<string, any>[];
    return [...projectLevel, ...fromTasks, ...fromModules];
  }, [modules, project?.checklist, project?.checklists, tasks]);
  const dependencies = (project?.dependencies ?? []) as Record<string, any>[];
  const documents = (storedDocuments.length > 0 ? storedDocuments : project?.documents ?? []) as Record<string, any>[];
  const team = (project?.team_activity ?? []) as Record<string, any>[];
  const recommendations = (project?.recommendations ?? []) as Record<string, any>[];

  if (!project) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const progress = Math.max(0, Math.min(100, project.progress ?? 0));

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
        <Link to="/projects" className="inline-flex items-center gap-1 hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Projects
        </Link>
        <span>/</span>
        <span className="text-foreground">{project.name}</span>
      </div>

      {/* Hero */}
      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="relative mb-8 overflow-hidden rounded-2xl border border-border bg-card p-7"
      >
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-gradient-to-br from-primary/30 to-accent/20 blur-3xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-6">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Pill tone="primary">{project.status ?? "Active"}</Pill>
              {project.risk_level && (
                <Pill tone="destructive">
                  <AlertTriangle className="h-2.5 w-2.5" />
                  {project.risk_level} risk
                </Pill>
              )}
              <Pill tone="muted">
                <Sparkles className="h-2.5 w-2.5" />
                AI generated
              </Pill>
            </div>
            <h1 className="mt-3 font-display text-3xl font-semibold leading-tight">
              {project.name}
            </h1>
            {project.description && (
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">{project.description}</p>
            )}
            <div className="mt-5 flex flex-wrap items-center gap-6 text-xs">
              <Stat label="Progress" value={`${progress}%`} />
              <Stat label="Health" value={project.health_score ? `${Math.round(project.health_score)}` : "—"} />
              <Stat label="Modules" value={modules.length} />
              <Stat label="Tasks" value={tasks.length} />
              <Stat label="Documents" value={documents.length} />
              <Stat label="Risks" value={risks.length} />
            </div>
          </div>
          <button
            onClick={() => triggerAnalysis(projectId)}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-primary/30 bg-primary/10 px-3 text-xs font-medium text-primary transition hover:bg-primary/20"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Re-run AI analysis
          </button>
        </div>
        {/* Progress bar */}
        <div className="relative mt-6 h-1.5 overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
            style={{ width: `${progress}%` }}
          />
        </div>
      </motion.section>

      <div className="flex gap-8">
        {/* Sticky section nav */}
        <nav className="sticky top-20 hidden h-fit w-44 shrink-0 lg:block">
          <ul className="space-y-0.5">
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a
                  href={`#${s.id}`}
                  onClick={() => setActive(s.id)}
                  className={cn(
                    "group flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs transition",
                    active === s.id
                      ? "bg-surface text-foreground"
                      : "text-muted-foreground hover:bg-surface/50 hover:text-foreground",
                  )}
                >
                  <s.icon
                    className={cn(
                      "h-3.5 w-3.5",
                      active === s.id && "text-primary",
                    )}
                  />
                  {s.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        {/* Sections */}
        <div className="min-w-0 flex-1 space-y-10">
          <Block id="atlas-agent" title="Atlas Agent" icon={Bot}>
            <AtlasAgentPanel projectId={projectId} />
          </Block>
          <Block id="overview" title="Overview" icon={Layers}>
            <div className="grid gap-4 md:grid-cols-2">
              <Card title="Status">
                <p className="text-sm text-muted-foreground">
                  {project.status ?? "Workspace is active and being orchestrated by Atlas."}
                </p>
              </Card>
              <Card title="Last activity">
                <p className="text-sm text-muted-foreground">
                  {project.updated_at
                    ? new Date(project.updated_at).toLocaleString()
                    : "No recent updates yet."}
                </p>
              </Card>
            </div>
          </Block>

          <Block id="ai-summary" title="AI Summary" icon={Sparkles}>
            <div className="relative rounded-xl border border-primary/20 bg-gradient-to-br from-primary/8 to-accent/5 p-5">
              <div className="absolute inset-0 -z-10 rounded-xl bg-primary/5 blur-xl" />
              {aiLoading && !summary ? (
                <Skeleton className="h-24 w-full" />
              ) : summary ? (
                <p className="text-sm leading-relaxed">{summary}</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  AI hasn't generated a summary for this workspace yet.
                </p>
              )}
              {aiSummary?.highlights && aiSummary.highlights.length > 0 && (
                <ul className="mt-4 space-y-1.5">
                  {aiSummary.highlights.map((h, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs">
                      <Sparkles className="mt-0.5 h-3 w-3 text-primary" />
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Block>

          <Block id="modules" title="Modules" icon={Network} count={modules.length}>
            {modules.length === 0 ? (
              <EmptyState
                icon={Network}
                title="No modules yet"
                description="Atlas will generate modules once it has analyzed your documents."
              />
            ) : (
              <div className="space-y-2">
                {modules.map((m, i) => (
                  <ModuleNode key={String((m as any).id ?? i)} module={m as any} />
                ))}
              </div>
            )}
          </Block>

          <Block id="tasks" title="Tasks" icon={ListChecks} count={tasks.length}>
            {tasks.length === 0 ? (
              <EmptyState
                icon={ListChecks}
                title="No tasks yet"
                description="Tasks will appear once modules are generated."
              />
            ) : (
              <ul className="space-y-1.5">
                {tasks.map((t, i) => (
                  <li
                    key={String(t.id ?? i)}
                    className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {String(t.title ?? t.name ?? "Task")}
                      </div>
                      {t.module_name && (
                        <div className="text-[11px] text-muted-foreground">
                          {String(t.module_name)}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {t.priority && <Pill tone="warning">{String(t.priority)}</Pill>}
                      {t.status && <Pill tone="muted">{String(t.status)}</Pill>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Block>

          <Block id="checklists" title="Checklist Items" icon={ListChecks} count={checklistItems.length}>
            {checklistItems.length === 0 ? (
              <EmptyState
                icon={ListChecks}
                title="No checklist items yet"
                description="Checklist items will appear when AI converts the source material into executable tasks."
              />
            ) : (
              <ul className="space-y-1.5">
                {checklistItems.map((item, index) => {
                  const done = Boolean(item.done ?? item.is_completed ?? item.completed);
                  return (
                    <li
                      key={String(item.id ?? index)}
                      className="flex items-start gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm"
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px]",
                          done ? "border-success bg-success/20 text-success" : "border-border",
                        )}
                      >
                        {done && "✓"}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className={cn("truncate", done && "text-muted-foreground line-through")}>
                          {String(item.label ?? item.title ?? item.name ?? "Checklist item")}
                        </div>
                        {item.task_title && (
                          <div className="mt-0.5 text-[11px] text-muted-foreground">
                            {String(item.task_title)}
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </Block>

          <Block id="risks" title="Risks" icon={AlertTriangle} count={risks.length}>
            {risks.length === 0 ? (
              <EmptyState icon={AlertTriangle} title="No risks detected" />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {risks.map((r, i) => (
                  <div
                    key={String((r as any).id ?? i)}
                    className="rounded-lg border border-destructive/30 bg-destructive/5 p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium">
                        {String((r as any).title ?? "Risk")}
                      </div>
                      {(r as any).severity && (
                        <Pill tone="destructive">{String((r as any).severity)}</Pill>
                      )}
                    </div>
                    {(r as any).description && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        {String((r as any).description)}
                      </p>
                    )}
                    {(r as any).mitigation && (
                      <div className="mt-3 rounded border border-border bg-background/40 p-2 text-[11px]">
                        <span className="font-medium text-primary">Mitigation: </span>
                        {String((r as any).mitigation)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Block>

          <Block id="dependencies" title="Dependencies" icon={GitBranch} count={dependencies.length}>
            {dependencies.length === 0 ? (
              <EmptyState icon={GitBranch} title="No dependencies mapped" />
            ) : (
              <div className="flex flex-wrap gap-2">
                {dependencies.map((d, i) => (
                  <Pill key={String(d.id ?? i)} tone="default">
                    {String(d.name ?? d.title ?? d)}
                  </Pill>
                ))}
              </div>
            )}
          </Block>

          <Block id="documents" title="Documents" icon={FileText} count={documents.length}>
            <div className="mb-4">
              <DocumentUploader
                projectId={projectId}
                onComplete={async () => {
                  await Promise.all([fetchProject(projectId), fetchAI(projectId), fetchTasks(projectId), fetchDocuments(projectId)]);
                }}
              />
            </div>
            {documents.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="No documents uploaded"
                description="Drag a BRD, PRD, or transcript into the Documents page to begin analysis."
              />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {documents.map((d, i) => (
                  <div
                    key={String(d.id ?? i)}
                    className="flex items-start gap-3 rounded-lg border border-border bg-card p-4"
                  >
                    <FileText className="mt-0.5 h-4 w-4 text-primary" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">
                        {String(d.name ?? "Document")}
                      </div>
                      <div className="mt-0.5 text-[11px] text-muted-foreground">
                        {String(d.status ?? "ready")}
                        {d.chunk_count != null && ` · ${d.chunk_count} chunks`}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Block>

          <Block id="team" title="Team Activity" icon={Users} count={team.length}>
            {team.length === 0 ? (
              <EmptyState icon={Users} title="No activity yet" />
            ) : (
              <ul className="space-y-2">
                {team.map((a, i) => (
                  <li
                    key={String(a.id ?? i)}
                    className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-[11px] font-semibold text-primary-foreground">
                      {String(a.user ?? a.actor ?? "U")[0]?.toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate">{String(a.message ?? a.action ?? "Activity")}</div>
                      {a.timestamp && (
                        <div className="text-[11px] text-muted-foreground">
                          {new Date(String(a.timestamp)).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Block>

          <Block id="recommendations" title="AI Recommendations" icon={Lightbulb} count={recommendations.length}>
            {recommendations.length === 0 ? (
              <EmptyState icon={Lightbulb} title="No recommendations yet" />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {recommendations.map((r, i) => (
                  <div
                    key={String(r.id ?? i)}
                    className="rounded-lg border border-primary/20 bg-primary/5 p-4"
                  >
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Sparkles className="h-3.5 w-3.5 text-primary" />
                      {String(r.title ?? "Recommendation")}
                    </div>
                    {r.description && (
                      <p className="mt-1.5 text-xs text-muted-foreground">{String(r.description)}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Block>

          <Block id="sprint" title="Sprint Planning" icon={CalendarDays}>
            <EmptyState
              icon={CalendarDays}
              title="Sprint planner coming soon"
              description="Atlas will propose sprint structures from generated modules and team capacity."
            />
          </Block>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-display text-base font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function Block({
  id,
  title,
  icon: Icon,
  count,
  children,
}: {
  id: string;
  title: string;
  icon: React.ElementType;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-primary" />
        <h2 className="font-display text-lg font-semibold">{title}</h2>
        {typeof count === "number" && (
          <span className="rounded-full bg-surface px-1.5 py-0.5 text-[10px] tabular-nums text-muted-foreground">
            {count}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {title}
      </div>
      {children}
    </div>
  );
}
