<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div>
        <div class="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <NuxtLink
            to="/"
            class="hover:text-foreground"
          >
            Dashboard
          </NuxtLink>
          <Icon
            name="lucide:chevron-right"
            class="size-3"
          />
          <span>Employee Task Manager</span>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight md:text-3xl">
          Employee Task Manager
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Keep work organized across the team, timelines, and daily priorities.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          class="gap-2"
          @click="createQuickTask"
        >
          <Icon
            name="lucide:plus-circle"
            class="size-4"
          />
          Quick task
        </Button>

        <Dialog v-model:open="dialogOpen">
          <DialogTrigger as-child>
            <Button class="gap-2">
              <Icon
                name="lucide:plus"
                class="size-4"
              />
              New task
            </Button>
          </DialogTrigger>

          <DialogContent class="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>Create task</DialogTitle>
              <DialogDescription>
                Add a task for the team and assign it to the right owner.
              </DialogDescription>
            </DialogHeader>

            <form
              class="space-y-4"
              @submit.prevent="submitTask"
            >
              <div class="grid gap-4 md:grid-cols-2">
                <label class="space-y-2 text-sm">
                  <span class="text-muted-foreground">Task title</span>
                  <Input
                    v-model="form.title"
                    dir="rtl"
                    class="text-right placeholder:text-right"
                    placeholder="Prepare sprint update"
                    required
                  />
                </label>

                <label class="space-y-2 text-sm">
                  <span class="text-muted-foreground">Project</span>
                  <Input
                    v-model="form.project"
                    dir="rtl"
                    class="text-right placeholder:text-right"
                    placeholder="Operations"
                  />
                </label>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <label class="space-y-2 text-sm">
                  <span class="text-muted-foreground">Assignee</span>
                  <select
                    v-model="form.assignee"
                    class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <option value="Maya">Maya</option>
                    <option value="Ava">Ava</option>
                    <option value="Leo">Leo</option>
                    <option value="Noah">Noah</option>
                    <option value="Emma">Emma</option>
                    <option value="Omar">Omar</option>
                  </select>
                </label>

                <label class="space-y-2 text-sm">
                  <span class="text-muted-foreground">Priority</span>
                  <select
                    v-model="form.priority"
                    class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                    <option value="Urgent">Urgent</option>
                  </select>
                </label>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <label class="space-y-2 text-sm">
                  <span class="text-muted-foreground">Due date</span>
                  <Input
                    v-model="form.dueDate"
                    type="date"
                  />
                </label>

                <label class="space-y-2 text-sm">
                  <span class="text-muted-foreground">Status</span>
                  <select
                    v-model="form.status"
                    class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <option value="To do">To do</option>
                    <option value="In progress">In progress</option>
                    <option value="Review">Review</option>
                    <option value="Done">Done</option>
                  </select>
                </label>
              </div>

              <label class="space-y-2 text-sm">
                <span class="text-muted-foreground">Description</span>
                <textarea
                  v-model="form.description"
                  rows="4"
                  dir="rtl"
                  class="flex min-h-[110px] w-full rounded-md border border-input bg-background px-3 py-2 text-right text-sm ring-offset-background placeholder:text-right placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder="Summarize the task and expected outcome."
                />
              </label>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  @click="dialogOpen = false"
                >
                  Cancel
                </Button>
                <Button type="submit">
                  Save task
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Card
        v-for="metric in summaryCards"
        :key="metric.label"
        class="gap-3 p-4 shadow-none"
      >
        <div class="flex items-center justify-between">
          <div class="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon
              :name="metric.icon"
              class="size-5"
            />
          </div>
          <Badge
            :variant="metric.trendTone"
            class="text-[10px]"
          >
            {{ metric.trend }}
          </Badge>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">
            {{ metric.label }}
          </p>
          <p class="mt-2 text-2xl font-semibold tracking-tight">
            {{ metric.value }}
          </p>
        </div>
      </Card>
    </div>

    <div class="flex flex-wrap gap-2">
      <NuxtLink
        v-for="tab in tabs"
        :key="tab.href"
        :to="tab.href"
        class="inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition-colors"
        :class="tab.href === currentHref ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-background text-muted-foreground hover:text-foreground'"
      >
        <Icon
          :name="tab.icon"
          class="size-4"
        />
        {{ tab.label }}
      </NuxtLink>
    </div>

    <section
      v-if="mode === 'dashboard'"
      class="grid gap-6 xl:grid-cols-[1.5fr_0.9fr]"
    >
      <Card class="overflow-hidden p-0 shadow-none">
        <div class="flex flex-col gap-3 border-b p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 class="text-lg font-semibold">
              Team board
            </h2>
            <p class="text-sm text-muted-foreground">
              All tasks in the current sprint.
            </p>
          </div>

          <div class="relative w-full max-w-xs">
            <Icon
              name="lucide:search"
              class="absolute left-3 top-2.5 size-4 text-muted-foreground"
            />
            <Input
              v-model="search"
              dir="rtl"
              class="pl-9 pr-9 text-right placeholder:text-right"
              placeholder="Search task"
            />
          </div>
        </div>

        <div class="grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-4">
          <div
            v-for="column in boardColumns"
            :key="column"
            class="rounded-xl border bg-muted/30 p-3"
          >
            <div class="mb-3 flex items-center justify-between">
              <span class="text-sm font-medium text-foreground">
                {{ column }}
              </span>
              <Badge variant="secondary">
                {{ columnTasks[column]?.length || 0 }}
              </Badge>
            </div>

            <div class="space-y-3">
              <div
                v-for="task in columnTasks[column]"
                :key="task.id"
                class="rounded-xl border bg-background p-3 shadow-sm"
              >
                <div class="mb-3 flex items-start justify-between gap-3">
                  <Badge
                    :variant="priorityTone(task.priority)"
                    class="text-[10px]"
                  >
                    {{ task.priority }}
                  </Badge>
                  <span class="text-[11px] text-muted-foreground">
                    {{ task.project }}
                  </span>
                </div>

                <h3 class="font-medium leading-5">
                  {{ task.title }}
                </h3>
                <p class="mt-2 line-clamp-2 text-sm text-muted-foreground">
                  {{ task.description }}
                </p>

                <div class="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                  <span>{{ task.assignee }}</span>
                  <span>{{ task.dueDate }}</span>
                </div>

                <div class="mt-3">
                  <div class="mb-1 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span>Progress</span>
                    <span>{{ task.progress }}%</span>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      class="h-full rounded-full bg-primary"
                      :style="{ width: `${task.progress}%` }"
                    />
                  </div>
                </div>

                <div class="mt-4 flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    @click="advanceTask(task.id)"
                  >
                    Advance
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    @click="markDone(task.id)"
                  >
                    Done
                  </Button>
                </div>
              </div>

              <div
                v-if="!columnTasks[column]?.length"
                class="rounded-xl border border-dashed border-border bg-background/50 p-4 text-center text-sm text-muted-foreground"
              >
                No items in this column.
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div class="space-y-6">
        <Card class="gap-4 p-4 shadow-none">
          <h3 class="text-base font-semibold">
            Team workload
          </h3>
          <div class="space-y-4">
            <div
              v-for="member in workloadStats"
              :key="member.name"
              class="space-y-2"
            >
              <div class="flex items-center justify-between text-sm">
                <span>{{ member.name }}</span>
                <span class="text-muted-foreground">{{ member.count }} tasks</span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  class="h-full rounded-full bg-secondary"
                  :style="{ width: `${member.width}%` }"
                />
              </div>
            </div>
          </div>
        </Card>

        <Card class="gap-4 p-4 shadow-none">
          <h3 class="text-base font-semibold">
            Priority snapshot
          </h3>
          <div class="space-y-3">
            <div
              v-for="item in prioritySummary"
              :key="item.label"
              class="flex items-center justify-between rounded-md border bg-muted/20 px-3 py-2 text-sm"
            >
              <div class="flex items-center gap-2">
                <span
                  class="inline-block size-2.5 rounded-full"
                  :class="item.dotClass"
                />
                <span>{{ item.label }}</span>
              </div>
              <Badge variant="secondary">
                {{ item.count }}
              </Badge>
            </div>
          </div>
        </Card>

        <Card class="gap-4 p-4 shadow-none">
          <h3 class="text-base font-semibold">
            Recent activity
          </h3>
          <div class="space-y-3 text-sm text-muted-foreground">
            <div
              v-for="item in recentActivity"
              :key="item.id"
              class="flex items-start gap-3 rounded-md border bg-muted/20 p-3"
            >
              <div class="mt-1 size-2 rounded-full bg-primary" />
              <div>
                <p class="font-medium text-foreground">
                  {{ item.title }}
                </p>
                <p>{{ item.detail }}</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </section>

    <section
      v-else-if="mode === 'my'"
      class="grid gap-6 xl:grid-cols-[1.5fr_0.9fr]"
    >
      <Card class="overflow-hidden p-0 shadow-none">
        <div class="flex items-center justify-between border-b p-4">
          <div>
            <h2 class="text-lg font-semibold">
              My tasks
            </h2>
            <p class="text-sm text-muted-foreground">
              Tasks assigned to Maya.
            </p>
          </div>
          <Badge variant="info">
            {{ myTasks.length }} active
          </Badge>
        </div>

        <div class="space-y-3 p-4">
          <div
            v-for="task in myTasks"
            :key="task.id"
            class="rounded-xl border bg-background p-4"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div class="mb-2 flex items-center gap-2">
                  <Badge :variant="priorityTone(task.priority)">
                    {{ task.priority }}
                  </Badge>
                  <span class="text-xs text-muted-foreground">
                    {{ task.project }}
                  </span>
                </div>
                <h3 class="font-medium">
                  {{ task.title }}
                </h3>
              </div>

              <div class="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  @click="advanceTask(task.id)"
                >
                  Update
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  @click="markDone(task.id)"
                >
                  Done
                </Button>
              </div>
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span>Due: {{ task.dueDate }}</span>
              <span>Status: {{ task.status }}</span>
              <span>Progress: {{ task.progress }}%</span>
            </div>
          </div>
        </div>
      </Card>

      <Card class="gap-4 p-4 shadow-none">
        <h3 class="text-base font-semibold">
          Today focus
        </h3>
        <div class="space-y-3">
          <div
            v-for="item in todayFocus"
            :key="item.label"
            class="rounded-md border bg-muted/20 p-3 text-sm"
          >
            <p class="font-medium text-foreground">
              {{ item.label }}
            </p>
            <p class="mt-1 text-muted-foreground">
              {{ item.value }}
            </p>
          </div>
        </div>
      </Card>
    </section>

    <section
      v-else-if="mode === 'team'"
      class="space-y-6"
    >
      <Card class="overflow-hidden p-0 shadow-none">
        <div class="flex flex-col gap-3 border-b p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 class="text-lg font-semibold">
              Team tasks
            </h2>
            <p class="text-sm text-muted-foreground">
              Cross-functional work across departments.
            </p>
          </div>
          <div class="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              @click="assignTaskToMember('Ava')"
            >
              Assign to Ava
            </Button>
            <Button
              size="sm"
              @click="createQuickTask"
            >
              Add team task
            </Button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Task</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Project</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Due</TableHead>
                <TableHead class="text-right">
                  Actions
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="task in teamTasks"
                :key="task.id"
              >
                <TableCell>
                  <div>
                    <p class="font-medium">
                      {{ task.title }}
                    </p>
                    <p class="text-xs text-muted-foreground">
                      {{ task.description }}
                    </p>
                  </div>
                </TableCell>
                <TableCell>{{ task.assignee }}</TableCell>
                <TableCell>{{ task.project }}</TableCell>
                <TableCell>
                  <Badge :variant="statusTone(task.status)">
                    {{ task.status }}
                  </Badge>
                </TableCell>
                <TableCell>{{ task.dueDate }}</TableCell>
                <TableCell class="text-right">
                  <div class="flex justify-end gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      @click="advanceTask(task.id)"
                    >
                      Advance
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      @click="markDone(task.id)"
                    >
                      Done
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </Card>
    </section>

    <section
      v-else-if="mode === 'calendar'"
      class="space-y-6"
    >
      <div class="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <Card class="gap-4 p-4 shadow-none">
          <h2 class="text-lg font-semibold">
            Calendar view
          </h2>
          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div
              v-for="item in calendarItems"
              :key="item.date"
              class="rounded-xl border bg-muted/20 p-3"
            >
              <p class="text-xs uppercase tracking-wide text-muted-foreground">
                {{ item.day }}
              </p>
              <p class="mt-1 text-2xl font-semibold">
                {{ item.dateNumber }}
              </p>
              <div class="mt-3 space-y-2">
                <div
                  v-for="task in item.tasks"
                  :key="task.id"
                  class="rounded-md border bg-background p-2 text-sm"
                >
                  <div class="flex items-center justify-between gap-3">
                    <span class="font-medium">
                      {{ task.title }}
                    </span>
                    <Badge :variant="priorityTone(task.priority)">
                      {{ task.priority }}
                    </Badge>
                  </div>
                  <p class="mt-1 text-muted-foreground">
                    {{ task.assignee }} · {{ task.project }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card class="gap-4 p-4 shadow-none">
          <h3 class="text-base font-semibold">
            Upcoming milestones
          </h3>
          <div class="space-y-3">
            <div
              v-for="item in upcomingMilestones"
              :key="item.title"
              class="rounded-md border bg-muted/20 p-3"
            >
              <p class="font-medium text-foreground">
                {{ item.title }}
              </p>
              <p class="mt-1 text-sm text-muted-foreground">
                {{ item.date }} · {{ item.owner }}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </section>

    <section
      v-else
      class="space-y-6"
    >
      <div class="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <Card class="gap-4 p-4 shadow-none">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold">
              Task reports
            </h2>
            <Button
              variant="outline"
              @click="exportReport"
            >
              Export report
            </Button>
          </div>

          <div class="grid gap-4 md:grid-cols-3">
            <div class="rounded-xl border bg-muted/20 p-4">
              <p class="text-sm text-muted-foreground">
                Completed
              </p>
              <p class="mt-2 text-2xl font-semibold">
                {{ completedTasks }}
              </p>
            </div>
            <div class="rounded-xl border bg-muted/20 p-4">
              <p class="text-sm text-muted-foreground">
                At risk
              </p>
              <p class="mt-2 text-2xl font-semibold text-warning">
                {{ atRiskTasks }}
              </p>
            </div>
            <div class="rounded-xl border bg-muted/20 p-4">
              <p class="text-sm text-muted-foreground">
                Velocity
              </p>
              <p class="mt-2 text-2xl font-semibold text-primary">
                {{ velocity }}%
              </p>
            </div>
          </div>
        </Card>

        <Card class="gap-4 p-4 shadow-none">
          <h3 class="text-base font-semibold">
            Department summary
          </h3>
          <div class="space-y-3">
            <div
              v-for="item in departmentSummary"
              :key="item.label"
              class="flex items-center justify-between rounded-md border bg-muted/20 px-3 py-2 text-sm"
            >
              <span>{{ item.label }}</span>
              <Badge variant="secondary">
                {{ item.value }}
              </Badge>
            </div>
          </div>
        </Card>
      </div>
    </section>
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()

withDefaults(
  defineProps<{
    mode?: 'dashboard' | 'my' | 'team' | 'calendar' | 'reports'
  }>(),
  {
    mode: 'dashboard',
  },
)

const boardColumns = ['To do', 'In progress', 'Review', 'Done'] as const
const tabs = [
  { label: 'Dashboard', href: '/tasks', icon: 'lucide:layout-dashboard' },
  { label: 'My Tasks', href: '/tasks/my-tasks', icon: 'lucide:user-round' },
  { label: 'Team Tasks', href: '/tasks/team', icon: 'lucide:users-round' },
  { label: 'Task Calendar', href: '/tasks/calendar', icon: 'lucide:calendar-days' },
  { label: 'Task Reports', href: '/tasks/reports', icon: 'lucide:bar-chart-3' },
] as const

const route = useRoute()
const currentHref = computed(() => route.path)
const dialogOpen = ref(false)
const search = ref('')

const taskTemplates = [
  { title: 'Client onboarding checklist', assignee: 'Ava', project: 'Client Ops', priority: 'High', status: 'To do', dueDate: '2026-09-12', description: 'Finalize the welcome flow and handover notes for new client accounts.' },
  { title: 'QA regression pass', assignee: 'Maya', project: 'Platform', priority: 'Urgent', status: 'In progress', dueDate: '2026-09-09', description: 'Review the latest release fixes and ensure no workflow regressions remain.' },
  { title: 'Marketing launch review', assignee: 'Leo', project: 'Growth', priority: 'Medium', status: 'Review', dueDate: '2026-09-13', description: 'Verify campaign assets, redirect links, and final approval notes for the launch.' },
  { title: 'Partner reporting update', assignee: 'Emma', project: 'Partnerships', priority: 'Low', status: 'Done', dueDate: '2026-09-08', description: 'Share the monthly performance summary with all active strategic partners.' },
  { title: 'Service performance tuning', assignee: 'Noah', project: 'Operations', priority: 'High', status: 'To do', dueDate: '2026-09-14', description: 'Review slow service endpoints and optimize the handoff process before the next release.' },
  { title: 'Team retrospective notes', assignee: 'Maya', project: 'People Ops', priority: 'Medium', status: 'In progress', dueDate: '2026-09-11', description: 'Collect notes from sprint review and document follow-up actions for the next cycle.' },
]

const tasks = ref(
  taskTemplates.map((task, index) => ({
    id: index + 1,
    progress: task.status === 'Done' ? 100 : task.status === 'Review' ? 80 : task.status === 'In progress' ? 62 : 24,
    ...task,
  })),
)

const form = reactive({
  title: '',
  project: 'Operations',
  assignee: 'Maya',
  priority: 'Medium',
  status: 'To do',
  dueDate: '2026-09-15',
  description: '',
})

const summaryCards = computed(() => {
  const openTasks = tasks.value.filter(task => task.status !== 'Done').length
  const doneTasks = tasks.value.filter(task => task.status === 'Done').length
  const overdue = tasks.value.filter(task => task.status !== 'Done' && new Date(task.dueDate) < new Date()).length
  const completion = Math.round(tasks.value.reduce((sum, task) => sum + task.progress, 0) / tasks.value.length)

  return [
    { label: 'Open tasks', value: openTasks, icon: 'lucide:clipboard-list', trend: '+12%', trendTone: 'secondary' },
    { label: 'Completed', value: doneTasks, icon: 'lucide:check-circle-2', trend: '+8%', trendTone: 'success' },
    { label: 'At risk', value: overdue, icon: 'lucide:alert-triangle', trend: '-4%', trendTone: 'warning' },
    { label: 'Progress', value: `${completion}%`, icon: 'lucide:activity', trend: '+6%', trendTone: 'info' },
  ]
})

const filteredTasks = computed(() => {
  const term = search.value.trim().toLowerCase()

  return tasks.value.filter((task) => {
    if (!term) return true

    return [task.title, task.project, task.assignee, task.priority, task.status]
      .join(' ')
      .toLowerCase()
      .includes(term)
  })
})

const columnTasks = computed(() => {
  const map = Object.fromEntries(boardColumns.map(column => [column, []]))

  for (const task of filteredTasks.value) {
    map[task.status] ??= []
    map[task.status].push(task)
  }

  return map
})

const myTasks = computed(() => tasks.value.filter(task => task.assignee === 'Maya'))
const teamTasks = computed(() => tasks.value.filter(task => task.assignee !== 'Maya'))
const completedTasks = computed(() => tasks.value.filter(task => task.status === 'Done').length)
const atRiskTasks = computed(() => tasks.value.filter(task => task.status !== 'Done' && task.priority === 'Urgent').length)
const velocity = computed(() => Math.min(96, Math.round((completedTasks.value / tasks.value.length) * 100)))

const workloadStats = computed(() => {
  const members = ['Maya', 'Ava', 'Leo', 'Noah', 'Emma']
  const overall = Math.max(...members.map(name => tasks.value.filter(task => task.assignee === name).length), 1)

  return members.map((name) => {
    const count = tasks.value.filter(task => task.assignee === name).length
    return { name, count, width: Math.max(30, (count / overall) * 100) }
  })
})

const prioritySummary = computed(() => {
  const map = [
    { label: 'Urgent', key: 'Urgent', dotClass: 'bg-destructive' },
    { label: 'High', key: 'High', dotClass: 'bg-primary' },
    { label: 'Medium', key: 'Medium', dotClass: 'bg-warning' },
    { label: 'Low', key: 'Low', dotClass: 'bg-success' },
  ]

  return map.map(item => ({
    ...item,
    count: tasks.value.filter(task => task.priority === item.key).length,
  }))
})

const recentActivity = computed(() => [
  { id: 1, title: 'Sprint review scheduled', detail: 'Operations team moved 3 tasks into review.' },
  { id: 2, title: 'Client portal update', detail: 'Maya completed the onboarding checklist draft.' },
  { id: 3, title: 'New request added', detail: 'Ava created a new customer workflow task yesterday.' },
])

const todayFocus = computed(() => [
  { label: 'High priority', value: tasks.value.filter(task => task.priority === 'High').length + ' tasks to action' },
  { label: 'Pending review', value: tasks.value.filter(task => task.status === 'Review').length + ' tasks waiting for approval' },
  { label: 'Team check-in', value: '2:30 PM daily sync call' },
])

const calendarItems = computed(() => {
  const upcomingDates = ['2026-09-09', '2026-09-11', '2026-09-12', '2026-09-14']

  return upcomingDates.map((date, index) => ({
    date,
    day: ['Tue', 'Thu', 'Fri', 'Sun'][index],
    dateNumber: date.split('-')[2],
    tasks: tasks.value.filter(task => task.dueDate === date).slice(0, 3),
  }))
})

const upcomingMilestones = computed(() => [
  { title: 'Release readiness review', date: '2026-09-10', owner: 'Operations' },
  { title: 'Marketing approval deadline', date: '2026-09-12', owner: 'Growth' },
  { title: 'Client onboarding signoff', date: '2026-09-15', owner: 'Customer Success' },
])

const deptSummaryData = [
  { label: 'Operations', value: 7 },
  { label: 'Product', value: 5 },
  { label: 'Marketing', value: 4 },
  { label: 'Support', value: 3 },
]

const departmentSummary = computed(() => deptSummaryData)

const priorityTone = (priority: string) => {
  const toneMap: Record<string, 'secondary' | 'warning' | 'info' | 'destructive' | 'success'> = {
    Low: 'success',
    Medium: 'warning',
    High: 'info',
    Urgent: 'destructive',
  }

  return toneMap[priority] || 'secondary'
}

const statusTone = (status: string) => {
  const toneMap: Record<string, 'secondary' | 'warning' | 'info' | 'success'> = {
    'To do': 'secondary',
    'In progress': 'info',
    'Review': 'warning',
    'Done': 'success',
  }

  return toneMap[status] || 'secondary'
}

const createQuickTask = () => {
  const templates = [
    'Customer onboarding sync',
    'QA update for release candidate',
    'Design validation check',
    'Partner follow-up call',
  ]

  const nextTask = templates[Math.floor(Math.random() * templates.length)] || 'Team follow-up'
  form.title = nextTask
  form.project = 'Operations'
  form.assignee = 'Ava'
  form.priority = 'Medium'
  form.status = 'To do'
  form.dueDate = '2026-09-16'
  form.description = 'Created from the quick action button to keep the work queue moving.'
  submitTask()
}

const assignTaskToMember = (member: string) => {
  const task = tasks.value[0]
  if (!task) return

  task.assignee = member
  notify.success(`${task.title} assigned to ${member}`)
}

const advanceTask = (taskId: number) => {
  const task = tasks.value.find(item => item.id === taskId)
  if (!task) return

  const currentIndex = boardColumns.indexOf(task.status as typeof boardColumns[number])
  const nextStatus = boardColumns[Math.min(currentIndex + 1, boardColumns.length - 1)]
  task.status = nextStatus
  task.progress = nextStatus === 'Done' ? 100 : nextStatus === 'Review' ? 80 : nextStatus === 'In progress' ? 62 : 24
  notify.success(`${task.title} moved to ${nextStatus}`)
}

const markDone = (taskId: number) => {
  const task = tasks.value.find(item => item.id === taskId)
  if (!task) return

  task.status = 'Done'
  task.progress = 100
  notify.success(`${task.title} marked as done`)
}

const submitTask = () => {
  if (!form.title.trim()) {
    notify.error('Please provide a title for the task')
    return
  }

  const newTask = {
    id: Date.now(),
    title: form.title.trim(),
    project: form.project.trim() || 'Operations',
    assignee: form.assignee,
    priority: form.priority,
    status: form.status,
    dueDate: form.dueDate || '2026-09-15',
    description: form.description.trim() || 'Task created from the task manager.',
    progress: form.status === 'Done' ? 100 : form.status === 'Review' ? 80 : form.status === 'In progress' ? 62 : 24,
  }

  tasks.value.unshift(newTask)
  notify.success(`Task created: ${newTask.title}`)
  dialogOpen.value = false
  Object.assign(form, {
    title: '',
    project: 'Operations',
    assignee: 'Maya',
    priority: 'Medium',
    status: 'To do',
    dueDate: '2026-09-15',
    description: '',
  })
}

const exportReport = () => {
  const rows = tasks.value.map(task => `${task.title},${task.assignee},${task.status},${task.priority}`)
  const csv = ['Title,Assignee,Status,Priority', ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'employee-task-report.csv'
  link.click()
  URL.revokeObjectURL(url)
  notify.success('Task report exported')
}

usePageSeoMeta({ title: 'Employee Task Manager' })
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
