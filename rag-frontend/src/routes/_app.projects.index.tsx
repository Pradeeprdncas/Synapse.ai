import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Search, FolderKanban, SlidersHorizontal, Plus } from "lucide-react";
import { useProjectStore } from "@/store/projectStore";
import { PageHeader, EmptyState, Skeleton, Modal } from "@/components/common/Primitives";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { useAuthStore } from "@/store/authStore";
import { adminApi, type ManagedUser } from "@/lib/api/adminApi";
import { toast } from "sonner";
import { toApiError } from "@/lib/api/client";

export const Route = createFileRoute("/_app/projects/")({
  head: () => ({
    meta: [
      { title: "Projects — Atlas" },
      { name: "description", content: "All AI-generated execution workspaces with live health, risk, and progress." },
    ],
  }),
  component: ProjectsPage,
});

function ProjectsPage() {
  const { projects, loading, fetchProjects, filters, setFilter, createProject, deleteProject } = useProjectStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({ name: "", description: "" });
  const user = useAuthStore(s => s.user); const isAdmin = user?.role === "ADMIN";
  const [managerId, setManagerId] = useState(0); const [users, setUsers] = useState<ManagedUser[]>([]);

  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);
  useEffect(() => { if (isAdmin) adminApi.users().then(setUsers).catch(() => undefined); }, [isAdmin]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    let success;
    if (isAdmin && managerId) {
      try { success = await adminApi.createProject({ ...formData, manager_user_id: managerId }); await fetchProjects(); toast.success("Project created and manager assigned"); }
      catch (err) { toast.error(toApiError(err).message); success = null; }
    } else success = await createProject(formData);
    setIsSubmitting(false);
    if (success) {
      setIsModalOpen(false);
      setFormData({ name: "", description: "" });
    }
  };

  const filtered = useMemo(() => {
    let items = [...projects];
    if (filters.search.trim()) {
      const q = filters.search.toLowerCase();
      items = items.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          (p.description ?? "").toLowerCase().includes(q),
      );
    }
    if (filters.status) items = items.filter((p) => p.status === filters.status);
    if (filters.minHealth !== null)
      items = items.filter((p) => (p.health_score ?? 0) >= filters.minHealth!);
    if (filters.sortBy === "name")
      items.sort((a, b) => a.name.localeCompare(b.name));
    else if (filters.sortBy === "health")
      items.sort((a, b) => (b.health_score ?? 0) - (a.health_score ?? 0));
    else
      items.sort((a, b) =>
        (b.updated_at ?? "").localeCompare(a.updated_at ?? ""),
      );
    return items;
  }, [projects, filters]);

  const statuses = useMemo(() => {
    const set = new Set<string>();
    projects.forEach((p) => p.status && set.add(p.status));
    return Array.from(set);
  }, [projects]);

  return (
    <div>
      <PageHeader
        eyebrow="Workspaces"
        title="Projects"
        description="Each project is an AI-generated execution workspace built from your documents."
        actions={
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground transition hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" /> New Project
          </button>
        }
      />

      {/* Filter bar */}
      <div className="mb-6 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card p-3">
        <div className="flex h-9 flex-1 min-w-[240px] items-center gap-2 rounded-md border border-border bg-surface/60 px-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            value={filters.search}
            onChange={(e) => setFilter("search", e.target.value)}
            placeholder="Search projects, descriptions…"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
        </div>
        <select
          value={filters.status ?? ""}
          onChange={(e) => setFilter("status", e.target.value || null)}
          className="h-9 rounded-md border border-border bg-surface/60 px-3 text-xs"
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={filters.sortBy}
          onChange={(e) => setFilter("sortBy", e.target.value as typeof filters.sortBy)}
          className="h-9 rounded-md border border-border bg-surface/60 px-3 text-xs"
        >
          <option value="updated">Recently updated</option>
          <option value="name">Name (A–Z)</option>
          <option value="health">Health score</option>
        </select>
        <button className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border bg-surface/60 px-3 text-xs">
          <SlidersHorizontal className="h-3.5 w-3.5" /> More filters
        </button>
      </div>

      {loading && projects.length === 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects match"
          description="Try clearing filters or upload a document to spin up a new workspace."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((p, i) => (
            <ProjectCard key={p.id} project={p} index={i} />
          ))}
        </div>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create New Project"
        footer={
          <>
            <button
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              form="project-form"
              disabled={isSubmitting}
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? "Creating..." : "Create Project"}
            </button>
          </>
        }
      >
        <form id="project-form" onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
              Project Name
            </label>
            <input
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Apollo Phase II"
              className="h-10 w-full rounded-md border border-border bg-surface px-3 text-sm outline-none focus:border-primary/50"
            />
          </div>
          {isAdmin && <div><label className="mb-1.5 block text-xs font-medium text-muted-foreground">Project manager</label><select required value={managerId || ""} onChange={e=>setManagerId(Number(e.target.value))} className="h-10 w-full rounded-md border border-border bg-surface px-3 text-sm"><option value="">Select manager</option>{users.filter(u=>u.is_active).map(u=><option key={u.id} value={u.id}>{u.name} — {u.email}</option>)}</select><p className="mt-1 text-[11px] text-muted-foreground">The selected user receives the MANAGER project role.</p></div>}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
              Description (optional)
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="What is this workspace about?"
              rows={3}
              className="w-full rounded-md border border-border bg-surface p-3 text-sm outline-none focus:border-primary/50"
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
