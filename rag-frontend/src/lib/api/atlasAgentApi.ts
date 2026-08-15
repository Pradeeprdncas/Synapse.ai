import { apiClient } from "./client";

export type AtlasRequirement = {
  id: string; title: string; description: string; category: string; priority: string; confidence: number;
  source: { documentId: number; section?: string; text: string }; taskIds: number[]; proposalIds: number[];
};
export type TaskProposal = {
  id: number; title: string; description?: string; priority: string; state: string; confidence: number;
  requirementIds: string[]; acceptanceCriteria: string[]; dependencies: string[]; createdTaskId?: number;
};
export type Coverage = { requirementsTotal: number; covered: number; partiallyCovered: number; uncovered: number; coveragePercent: number };
export type Health = { completionPercent: number; prdCoveragePercent: number; blockedTasks: number; unassignedTasks: number; overdueTasks: number | null; overdueTrackingSupported: boolean; uncoveredRequirements: number; pendingApprovals: number; pendingAssignmentApprovals: number; members: number; membersWithHighWorkload: number };
export type Workload = { memberId: number; userId: number; name: string; projectRole: string; skills: string[]; activeTasks: number; highPriorityTasks: number; completedTasks: number; workloadIndicator: string };
export type Recommendation = { id: number; taskId: number; recommendedMemberId: number; score: number; breakdown: Record<string, number>; reason: string[]; alternatives: Array<{ memberId: number; name: string; score: number; projectRole: string }>; requiredSkills: string[]; state: string };
export type Activity = { id: number; actorType: string; actorUserId?: number; action: string; targetType: string; targetId: number; metadata: Record<string, unknown>; createdAt: string };
export type AssignmentResult = { taskId: number; assignedUserId: number; notification: { status: string; requirementsShared?: number; documentsShared?: number }; contextShared: { requirements: number; documents: number } };

export const atlasAgentApi = {
  requirements: (projectId: string) => apiClient.get<AtlasRequirement[]>(`/projects/${projectId}/requirements`).then(r => r.data),
  proposals: (projectId: string) => apiClient.get<TaskProposal[]>(`/projects/${projectId}/task-proposals`).then(r => r.data),
  coverage: (projectId: string) => apiClient.get<Coverage>(`/projects/${projectId}/coverage`).then(r => r.data),
  health: (projectId: string) => apiClient.get<Health>(`/projects/${projectId}/health`).then(r => r.data),
  analyze: (projectId: string) => apiClient.post(`/projects/${projectId}/agent/analyze`).then(r => r.data),
  generate: (projectId: string, requirementIds: string[]) => apiClient.post(`/projects/${projectId}/task-proposals/generate`, { requirement_ids: requirementIds }).then(r => r.data),
  approve: (proposalId: number) => apiClient.post(`/task-proposals/${proposalId}/approve`).then(r => r.data),
  reject: (proposalId: number) => apiClient.post(`/task-proposals/${proposalId}/reject`).then(r => r.data),
  workload: (projectId: string) => apiClient.get<Workload[]>(`/projects/${projectId}/team/workload`).then(r => r.data),
  recommendations: (projectId: string) => apiClient.get<Recommendation[]>(`/projects/${projectId}/assignment-recommendations`).then(r => r.data),
  recommend: (taskId: number) => apiClient.post<Recommendation>(`/tasks/${taskId}/assignment-recommendations`).then(r => r.data),
  approveAssignment: (id: number, memberId?: number) => apiClient.post<AssignmentResult>(`/assignment-recommendations/${id}/approve`, { member_id: memberId }).then(r => r.data),
  retryAssignmentEmail: (taskId: number) => apiClient.post<AssignmentResult>(`/tasks/${taskId}/assignment-notification/retry`).then(r => r.data),
  activity: (projectId: string) => apiClient.get<Activity[]>(`/projects/${projectId}/activity`).then(r => r.data),
  tasks: (projectId: string) => apiClient.get<Array<{ id: number; title: string; assigned_to?: number; complexity: string; priority: string }>>(`/tasks/project/${projectId}`).then(r => r.data),
  googleConnection: () => apiClient.get<{ connected: boolean; email?: string; scopes: string[] }>("/google/connection").then(r => r.data),
  googleConnect: () => apiClient.get<{ authorizationUrl: string }>("/google/oauth/start").then(r => r.data),
};
