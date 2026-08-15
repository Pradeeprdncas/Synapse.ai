import { apiClient } from "./client";

export type ManagedUser = { id: number; name: string; email: string; role: "ADMIN" | "MEMBER"; is_active: boolean; created_at: string };
export type ProjectMemberInput = { user_id: number; project_role: string; skills: string[]; experience_level: string; current_capacity: number };

export const adminApi = {
  users: () => apiClient.get<ManagedUser[]>("/admin/users").then(r => r.data),
  createUser: (payload: { name: string; email: string; password: string; role: string; send_email: boolean }) =>
    apiClient.post<ManagedUser & { credential_email_status: string }>("/admin/users", payload).then(r => r.data),
  updateUser: (id: number, payload: Partial<ManagedUser> & { password?: string }) =>
    apiClient.patch<ManagedUser>(`/admin/users/${id}`, payload).then(r => r.data),
  createProject: (payload: { name: string; description?: string; manager_user_id: number }) =>
    apiClient.post("/admin/projects", null, { params: payload }).then(r => r.data),
  projectMembers: (projectId: string) => apiClient.get(`/projects/${projectId}/members`).then(r => r.data),
  eligibleProjectMembers: (projectId: string) => apiClient.get<ManagedUser[]>(`/projects/${projectId}/eligible-members`).then(r => r.data),
  addProjectMember: (projectId: string, payload: ProjectMemberInput) => apiClient.post(`/projects/${projectId}/members`, payload).then(r => r.data),
};
