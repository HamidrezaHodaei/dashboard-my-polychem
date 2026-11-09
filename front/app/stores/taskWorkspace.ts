import { defineStore } from 'pinia'
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'

export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'
export type TaskStatus = 'todo' | 'in-progress' | 'review' | 'done'
export type TaskSection = 'workspace' | 'your-work' | 'project' | 'views' | 'analytics' | 'drafts' | 'archives'

/** Repeat rule of a recurring task (months/years are Jalali). daily = DAY/1, weekly = WEEK/1, monthly = MONTH/1, yearly = YEAR/1; a manual span is any other interval. */
export interface RecurrenceRule { unit: 'DAY' | 'WEEK' | 'MONTH' | 'YEAR', interval: number, end_date: string | null, next_date?: string | null }

export interface WorkspaceEntity { id: string, name: string, slug: string, ownerId: string }

/** A "project" is a backend department. */
export interface ProjectEntity {
  id: string
  workspaceId: string
  name: string
  code: string
  leadId: string
  description: string
  accent: 'blue' | 'green' | 'indigo' | 'slate'
}

export interface UserEntity {
  id: string
  name: string
  email: string
  teamId: string | null
  departmentId: string | null
}

export interface TeamEntity { id: string, name: string, departmentId: string }

export interface ViewEntity {
  id: string
  workspaceId: string
  name: string
  type: 'board' | 'list' | 'calendar' | 'analytics'
  projectId?: string
}

export interface TaskEntity {
  id: string
  workspaceId: string
  projectId: string
  teamId: string | null
  title: string
  description: string
  assigneeId: string
  assigneeIds: string[]
  creatorId: string
  status: TaskStatus
  priority: TaskPriority
  dueDate: string
  /** Optional time of the deadline, "HH:MM", Tehran time. */
  dueTime: string
  progress: number
  isDraft: boolean
  isArchived: boolean
  /** Full ISO timestamp (UTC, with offset) -- format it with formatTehranDateTime. */
  createdAt: string
  recurrence: RecurrenceRule | null
  recurrenceSourceId: string | null
  /** The caller is a «مدیر» of this task: may rename / delete it and delete its messages, checklist items, others' files. */
  canManage: boolean
}

interface BackendTask {
  id: number
  title: string
  description: string | null
  creator_id: number
  department_id: number
  team_id: number | null
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
  status: 'TODO' | 'IN_PROGRESS' | 'REVIEW' | 'DONE' | 'CANCELLED'
  due_date: string | null
  due_time: string | null
  is_draft: boolean
  is_archived: boolean
  progress: number
  assignee_ids: number[]
  recurrence: RecurrenceRule | null
  recurrence_source_id: number | null
  can_manage: boolean
  created_at: string
}

interface TaskMeta {
  me: { id: number, full_name: string, department_id: number | null }
  departments: { id: number, name: string, organization_id: number }[]
  teams: { id: number, name: string, department_id: number }[]
  assignable_users: { id: number, full_name: string, email: string, department_id: number | null }[]
  /** Who the actor may (re)assign an EXISTING task to -- can differ from
   * `assignable_users` (who they may create a new task for) when a rule
   * is scoped to only one of those two actions. */
  assignable_users_assign: { id: number, full_name: string, email: string, department_id: number | null }[]
  permissions: { create: boolean, update: boolean, delete: boolean, assign: boolean, analytics: boolean, manage: boolean }
  can_manage_rules: boolean
  is_admin: boolean
}

const statusOrder: TaskStatus[] = ['todo', 'in-progress', 'review', 'done']
const accents: ProjectEntity['accent'][] = ['blue', 'green', 'indigo', 'slate']

const STATUS_TO_API: Record<TaskStatus, BackendTask['status']> = {
  'todo': 'TODO',
  'in-progress': 'IN_PROGRESS',
  'review': 'REVIEW',
  'done': 'DONE',
}
const STATUS_FROM_API: Record<BackendTask['status'], TaskStatus> = {
  TODO: 'todo',
  IN_PROGRESS: 'in-progress',
  REVIEW: 'review',
  DONE: 'done',
  CANCELLED: 'done',
}
const progressFor = (s: TaskStatus) => (s === 'done' ? 100 : s === 'review' ? 80 : s === 'in-progress' ? 62 : 24)

const apiMessage = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback)

export const useTaskWorkspaceStore = defineStore('task-workspace', () => {
  const workspace = ref<WorkspaceEntity>({ id: 'ws-1', name: 'فضای کاری', slug: 'workspace', ownerId: '' })
  const users = ref<UserEntity[]>([])
  const assignUsers = ref<UserEntity[]>([])
  const teams = ref<TeamEntity[]>([])
  const projects = ref<ProjectEntity[]>([])
  const tasks = ref<TaskEntity[]>([])
  const views = ref<ViewEntity[]>([
    { id: 'view-board', workspaceId: 'ws-1', name: 'نمای کانبان', type: 'board' },
    { id: 'view-list', workspaceId: 'ws-1', name: 'فهرست امور محوله', type: 'list' },
    { id: 'view-calendar', workspaceId: 'ws-1', name: 'نمای تقویم', type: 'calendar' },
    { id: 'view-analytics', workspaceId: 'ws-1', name: 'نمای پیشرفت', type: 'analytics' },
  ])

  const meId = ref('')
  const loaded = ref(false)
  const loading = ref(false)
  const loadError = ref('')
  const permissions = ref<TaskMeta['permissions']>({
    create: false, update: false, delete: false, assign: false, analytics: false, manage: false,
  })
  const canManageRules = ref(false)
  const isAdmin = ref(false)

  const selectedProjectId = ref('all')
  const activeSection = ref<TaskSection>('your-work')
  const filters = reactive({ search: '', status: 'all', priority: 'all', assignee: 'all' })
  const allTaskStatuses = computed(() => statusOrder)

  // ------------------------------------------------------------ mapping
  function mapTask(t: BackendTask): TaskEntity {
    const status = STATUS_FROM_API[t.status] ?? 'todo'
    const ids = (t.assignee_ids || []).map(String)
    return {
      id: String(t.id),
      workspaceId: workspace.value.id,
      projectId: String(t.department_id),
      teamId: t.team_id ? String(t.team_id) : null,
      title: t.title,
      description: t.description || '',
      assigneeId: ids[0] || '',
      assigneeIds: ids,
      creatorId: String(t.creator_id),
      status,
      priority: (t.priority || 'MEDIUM').toLowerCase() as TaskPriority,
      dueDate: t.due_date || '',
      dueTime: t.due_time || '',
      progress: t.progress || progressFor(status),
      isDraft: t.is_draft,
      isArchived: t.is_archived || t.status === 'CANCELLED',
      createdAt: t.created_at || '',
      recurrence: t.recurrence ?? null,
      recurrenceSourceId: t.recurrence_source_id ? String(t.recurrence_source_id) : null,
      canManage: Boolean(t.can_manage),
    }
  }

  function applyMeta(meta: TaskMeta) {
    meId.value = String(meta.me.id)
    workspace.value.ownerId = meId.value
    permissions.value = meta.permissions
    canManageRules.value = meta.can_manage_rules
    isAdmin.value = meta.is_admin
    projects.value = meta.departments.map((d, i) => ({
      id: String(d.id),
      workspaceId: workspace.value.id,
      name: d.name,
      code: d.name.replace(/\s+/g, '').slice(0, 3).toUpperCase() || `D${d.id}`,
      leadId: '',
      description: 'کارها و وضعیت پیشرفت این واحد.',
      accent: accents[i % accents.length]!,
    }))
    teams.value = meta.teams.map(t => ({ id: String(t.id), name: t.name, departmentId: String(t.department_id) }))
    const list = meta.assignable_users.map(u => ({
      id: String(u.id),
      name: u.full_name,
      email: u.email,
      teamId: null,
      departmentId: u.department_id ? String(u.department_id) : null,
    }))
    if (!list.some(u => u.id === meId.value)) {
      list.unshift({ id: meId.value, name: meta.me.full_name, email: '', teamId: null, departmentId: meta.me.department_id ? String(meta.me.department_id) : null })
    }
    users.value = list

    const assignList = meta.assignable_users_assign.map(u => ({
      id: String(u.id),
      name: u.full_name,
      email: u.email,
      teamId: null,
      departmentId: u.department_id ? String(u.department_id) : null,
    }))
    if (!assignList.some(u => u.id === meId.value)) {
      assignList.unshift({ id: meId.value, name: meta.me.full_name, email: '', teamId: null, departmentId: meta.me.department_id ? String(meta.me.department_id) : null })
    }
    assignUsers.value = assignList
  }

  async function load() {
    loading.value = true
    loadError.value = ''
    try {
      const meta = await apiFetch<TaskMeta>('/tasks/meta')
      applyMeta(meta)
      const all: BackendTask[] = []
      for (let page = 1; page <= 50; page++) {
        const res = await apiFetchPage<BackendTask>('/tasks', { page, per_page: 100 })
        all.push(...res.items)
        if (all.length >= res.total || !res.items.length) break
      }
      tasks.value = all.map(mapTask)
      loaded.value = true
    }
    catch (err) {
      loadError.value = apiMessage(err, 'بارگذاری امور محوله انجام نشد.')
      // The user may hold only assign/analytics permissions (no tasks.task.read).
      if (err instanceof ApiError && err.status === 403 && users.value.length) tasks.value = []
    }
    finally {
      loading.value = false
    }
  }

  async function ensureLoaded() {
    if (!loaded.value && !loading.value) await load()
  }

  function reset() {
    tasks.value = []
    projects.value = []
    users.value = []
    assignUsers.value = []
    teams.value = []
    loaded.value = false
    loadError.value = ''
    canManageRules.value = false
    isAdmin.value = false
  }

  // ------------------------------------------------------------ selectors
  const filteredTasks = computed(() => {
    const term = filters.search.trim().toLowerCase()
    return tasks.value.filter((task) => {
      const projectMatch = selectedProjectId.value === 'all' || task.projectId === selectedProjectId.value
      const statusMatch = filters.status === 'all' || task.status === filters.status
      const priorityMatch = filters.priority === 'all' || task.priority === filters.priority
      const assigneeMatch = filters.assignee === 'all' || task.assigneeIds.includes(filters.assignee)
      const searchMatch = !term || [task.title, task.description, task.projectId].join(' ').toLowerCase().includes(term)
      return projectMatch && statusMatch && priorityMatch && assigneeMatch && searchMatch
    })
  })

  const getProjectById = (projectId: string) => projects.value.find(project => project.id === projectId)
  const getUserById = (userId: string) => {
    if (!userId) return undefined
    return users.value.find(user => user.id === userId)
      ?? { id: userId, name: `کاربر شماره ${userId}`, email: '', teamId: null, departmentId: null }
  }

  /** Users the current user may CREATE a new task of this project for. */
  const usersForProject = (projectId: string) =>
    users.value.filter(u => u.id === meId.value || !projectId || u.departmentId === projectId)

  /** Users the current user may (re)ASSIGN an existing task of this project to. */
  const usersForAssign = (projectId: string) =>
    assignUsers.value.filter(u => u.id === meId.value || !projectId || u.departmentId === projectId)

  const getTasksForSection = (section: TaskSection) => {
    switch (section) {
      case 'workspace':
        return filteredTasks.value.filter(task => !task.isArchived && !task.isDraft)
      case 'your-work':
        return filteredTasks.value.filter(task => task.assigneeIds.includes(meId.value))
      case 'project':
      case 'views':
        return filteredTasks.value.filter(task => !task.isArchived)
      case 'analytics':
        return filteredTasks.value.filter(task => !task.isDraft)
      case 'drafts':
        return filteredTasks.value.filter(task => task.isDraft)
      case 'archives':
        return filteredTasks.value.filter(task => task.isArchived)
      default:
        return filteredTasks.value
    }
  }

  const getSummaryCards = (section: TaskSection) => {
    const sectionTasks = getTasksForSection(section)
    const openTasks = sectionTasks.filter(task => task.status !== 'done').length
    const doneTasks = sectionTasks.filter(task => task.status === 'done').length
    const atRisk = sectionTasks.filter(task => task.priority === 'urgent' && task.status !== 'done').length
    const completion = sectionTasks.length ? Math.round(sectionTasks.reduce((sum, task) => sum + task.progress, 0) / sectionTasks.length) : 0
    return [
      { label: 'امور محوله باز', value: String(openTasks), icon: 'lucide:clipboard-list', trend: '', tone: 'secondary' },
      { label: 'انجام‌شده', value: String(doneTasks), icon: 'lucide:check-circle-2', trend: '', tone: 'success' },
      { label: 'در معرض تأخیر', value: String(atRisk), icon: 'lucide:alert-triangle', trend: '', tone: 'warning' },
      { label: 'پیشرفت', value: `${completion}%`, icon: 'lucide:activity', trend: '', tone: 'info' },
    ]
  }

  // ------------------------------------------------------------ mutations
  function replaceTask(t: BackendTask) {
    const next = mapTask(t)
    const i = tasks.value.findIndex(x => x.id === next.id)
    if (i >= 0) tasks.value[i] = next
    else tasks.value.unshift(next)
    return next
  }

  async function updateTask(taskId: string, payload: Partial<TaskEntity>) {
    const task = tasks.value.find(item => item.id === taskId)
    if (!task) return undefined

    const body: Record<string, unknown> = {}
    if (payload.title !== undefined) body.title = payload.title
    if (payload.description !== undefined) body.description = payload.description
    if (payload.priority !== undefined) body.priority = payload.priority.toUpperCase()
    if (payload.dueDate !== undefined) body.due_date = payload.dueDate || null
    if (payload.dueTime !== undefined) body.due_time = payload.dueTime || null
    if (payload.recurrence !== undefined) body.recurrence = payload.recurrence
    if (payload.isDraft !== undefined) body.is_draft = payload.isDraft
    if (payload.isArchived !== undefined) body.is_archived = payload.isArchived
    if (payload.status !== undefined && payload.status !== task.status) {
      body.status = STATUS_TO_API[payload.status]
      body.progress = progressFor(payload.status)
    }
    else if (payload.progress !== undefined && payload.status === undefined) body.progress = payload.progress

    let updated: BackendTask | null = null
    if (Object.keys(body).length) {
      updated = await apiFetch<BackendTask>(`/tasks/${taskId}`, { method: 'PATCH', body })
    }

    // Any number of assignees at once: one call replaces the whole list.
    if (payload.assigneeIds !== undefined) {
      const same = payload.assigneeIds.length === task.assigneeIds.length
        && payload.assigneeIds.every(id => task.assigneeIds.includes(id))
      if (!same) {
        updated = await apiFetch<BackendTask>(`/tasks/${taskId}/assignees`, {
          method: 'PUT', body: { assignee_user_ids: payload.assigneeIds.map(Number) },
        })
      }
    }
    return updated ? replaceTask(updated) : task
  }

  /** Delete a task (managers only -- the server refuses anyone else). */
  async function removeTask(taskId: string) {
    await apiFetch(`/tasks/${taskId}`, { method: 'DELETE' })
    tasks.value = tasks.value.filter(t => t.id !== taskId)
  }

  /** An assignee hands the task on to someone else; the chain of referrals is kept server-side. */
  async function referTask(taskId: string, toUserId: string, note?: string) {
    await apiFetch(`/tasks/${taskId}/refer`, { method: 'POST', body: { to_user_id: Number(toUserId), note: note?.trim() || null } })
    const fresh = await apiFetch<BackendTask>(`/tasks/${taskId}`)
    return replaceTask(fresh)
  }

  /** The current user is an assignee of the task and therefore restricted
   *  to requesting completion approval (admins are exempt, like the backend). */
  const isAssignee = (task: TaskEntity) => !isAdmin.value && task.assigneeIds.includes(meId.value)

  /** «مدیر»: may rename / delete the task and delete its messages, checklist items and others' files.
   *  Decided by the server (admin or holder of tasks.task.delete at the task's scope). */
  const canManageTask = (task: TaskEntity) => task.canManage

  /** May add checklist items / files, edit non-title fields (creator, update permission, or a manager). */
  const canEditTask = (task: TaskEntity) =>
    task.canManage || task.creatorId === meId.value || useAuthStore().hasPermission('tasks.task.update')

  /** Assigned to the task (admins included) -- may tick checklist items. */
  const isAssignedToMe = (task: TaskEntity) => task.assigneeIds.includes(meId.value)

  /**
   * Statuses the current user may set. An assignee may ONLY request completion
   * approval ('review'); Completed / Cancelled are never self-service for them.
   * Everyone else keeps the existing behaviour.
   */
  const allowedStatuses = (task: TaskEntity): TaskStatus[] =>
    isAssignee(task) ? ['review'] : [...statusOrder]

  const updateTaskStatus = (taskId: string, nextStatus: TaskStatus) => updateTask(taskId, { status: nextStatus })
  const publishTask = (taskId: string) => updateTask(taskId, { isDraft: false })
  const restoreTask = (taskId: string) => updateTask(taskId, { isArchived: false })

  async function createTask(payload: Partial<TaskEntity> & { title: string, assigneeId: string, projectId: string }) {
    const status = payload.status || 'todo'
    const body: Record<string, unknown> = {
      title: payload.title,
      description: payload.description || null,
      department_id: Number(payload.projectId),
      team_id: payload.teamId ? Number(payload.teamId) : null,
      priority: (payload.priority || 'medium').toUpperCase(),
      status: STATUS_TO_API[status],
      due_date: payload.dueDate || null,
      due_time: payload.dueTime || null,
      is_draft: Boolean(payload.isDraft),
      progress: payload.progress ?? progressFor(status),
      assignee_user_ids: (payload.assigneeIds?.length ? payload.assigneeIds : payload.assigneeId ? [payload.assigneeId] : []).map(Number),
      recurrence: payload.recurrence ?? null,
    }
    const created = await apiFetch<BackendTask>('/tasks', { method: 'POST', body })
    return replaceTask(created)
  }

  /** Projects are departments: needs core.department.create. */
  async function createProject(payload: { name: string, code?: string, description?: string, accent?: ProjectEntity['accent'], leadId?: string }) {
    const auth = useAuthStore()
    const orgId = auth.user?.organization_id
    if (!orgId) throw new ApiError(0, 'NO_ORGANIZATION', 'حساب شما به هیچ سازمانی متصل نیست.')
    const dept = await apiFetch<{ id: number, name: string, organization_id: number }>('/core/departments', {
      method: 'POST',
      body: { name: payload.name, organization_id: orgId },
    })
    await load()
    return projects.value.find(p => p.id === String(dept.id))
  }

  const setActiveSection = (section: TaskSection) => {
    activeSection.value = section
  }

  const resetFilters = () => {
    filters.search = ''
    filters.status = 'all'
    filters.priority = 'all'
    filters.assignee = 'all'
    selectedProjectId.value = 'all'
  }

  return {
    workspace, users, assignUsers, teams, projects, views, tasks, filters, selectedProjectId, activeSection,
    meId, loaded, loading, loadError, permissions, canManageRules, isAdmin,
    allTaskStatuses, filteredTasks,
    load, ensureLoaded, reset,
    getTasksForSection, getSummaryCards, getProjectById, getUserById, usersForProject, usersForAssign, isAssignee, isAssignedToMe, canManageTask, canEditTask, allowedStatuses,
    updateTaskStatus, updateTask, referTask, removeTask, createTask, createProject, publishTask, restoreTask,
    setActiveSection, resetFilters,
  }
})
