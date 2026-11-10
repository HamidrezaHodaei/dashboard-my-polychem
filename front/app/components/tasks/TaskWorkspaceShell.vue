<template>
  <ContainerWrapper
    :class="projectId
      ? 'min-h-full bg-background px-3 py-3 sm:px-5 md:px-6'
      : 'space-y-6 py-6 md:py-8'"
  >
    <Dialog v-model:open="dialogOpen">
      <DialogContent
        dir="rtl"
        class="max-h-[92vh] overflow-y-auto sm:max-w-2xl"
      >
        <DialogHeader class="text-right">
          <DialogTitle>ایجاد امور محوله</DialogTitle>
          <DialogDescription>
            امور محوله جدید را برای واحد خود تعریف کنید و آن را به یک یا چند نفر واگذار کنید.
          </DialogDescription>
        </DialogHeader>

        <form
          class="space-y-4"
          @submit.prevent="submitTask"
        >
          <div class="grid gap-4 md:grid-cols-2">
            <label class="space-y-2 text-sm">
              <span class="text-muted-foreground">عنوان امور محوله</span>
              <Input
                v-model="form.title"
                dir="rtl"
                class="text-right placeholder:text-right"
                placeholder="مثلاً: تهیه گزارش فروش ماهانه"
                required
              />
            </label>

            <label class="space-y-2 text-sm">
              <span class="text-muted-foreground">کارتابل واحد</span>
              <select
                v-model="form.projectId"
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option
                  v-for="project in store.projects"
                  :key="project.id"
                  :value="project.id"
                >
                  {{ project.name }}
                </option>
              </select>
            </label>
          </div>

          <div class="space-y-2 text-sm">
            <span class="text-muted-foreground">مسئولان امور محوله (یک یا چند نفر)</span>
            <TasksAssigneePicker
              v-model="form.assigneeIds"
              :users="projectUsers"
              :me-id="store.meId"
            />
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <label class="space-y-2 text-sm">
              <span class="text-muted-foreground">اولویت</span>
              <select
                v-model="form.priority"
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="low">کم</option>
                <option value="medium">متوسط</option>
                <option value="high">زیاد</option>
                <option value="urgent">فوری</option>
              </select>
            </label>

            <label class="space-y-2 text-sm">
              <span class="text-muted-foreground">وضعیت</span>
              <select
                v-model="form.status"
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="todo">در انتظار انجام</option>
                <option value="in-progress">در حال انجام</option>
                <option value="review">درخواست تأیید تکمیل</option>
                <option
                  value="done"
                  :disabled="form.assigneeIds.includes(store.meId)"
                >انجام‌شده</option>
              </select>
            </label>
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-2 text-sm">
              <span class="text-muted-foreground">موعد انجام (تاریخ شمسی)</span>
              <JalaliDateInput v-model="form.dueDate" />
            </div>

            <label class="space-y-2 text-sm">
              <span class="text-muted-foreground">ساعت موعد (به وقت تهران، اختیاری)</span>
              <Input
                v-model="form.dueTime"
                type="time"
                dir="ltr"
                class="text-right"
              />
            </label>
          </div>

          <div class="space-y-2 text-sm">
            <span class="text-muted-foreground">تکرار امور محوله</span>
            <TasksRecurrenceField v-model="form.recurrence" />
          </div>

          <label class="block space-y-2 text-sm">
            <span class="text-muted-foreground">توضیحات</span>
            <textarea
              v-model="form.description"
              dir="rtl"
              rows="4"
              class="flex min-h-27.5 w-full rounded-md border border-input bg-background px-3 py-2 text-right text-sm ring-offset-background placeholder:text-right placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              placeholder="خلاصه‌ی کار و نتیجه‌ی مورد انتظار را بنویسید."
            />
          </label>

          <DialogFooter class="gap-2">
            <Button
              type="button"
              variant="outline"
              @click="dialogOpen = false"
            >
              انصراف
            </Button>
            <Button type="submit">
              ذخیره امور محوله
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
    <div
      v-if="!['project', 'views'].includes(section)"
      class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between"
    >
      <div>
        <div class="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <NuxtLink
            to="/"
            class="hover:text-foreground"
          >
            داشبورد
          </NuxtLink>
          <Icon
            name="lucide:chevron-right"
            class="size-3"
          />
          <span>مدیریت امور محوله</span>
        </div>

        <h1 class="text-2xl font-semibold tracking-tight md:text-3xl">
          {{ sectionTitle }}
        </h1>

        <p class="mt-1 text-sm text-muted-foreground">
          {{ sectionDescription }}
        </p>
      </div>

      <div
        v-if="section !== 'workspace'"
        class="flex flex-wrap items-center gap-2"
      >
        <Button
          variant="outline"
          class="gap-2"
          @click="createQuickTask"
        >
          <Icon
            name="lucide:plus-circle"
            class="size-4"
          />
          امور محوله سریع
        </Button>

        <Button
          class="gap-2"
          @click="openProjectTaskDialog"
        >
          <Icon
            name="lucide:plus"
            class="size-4"
          />
          امور محوله جدید
        </Button>
      </div>
    </div>

    <div
      v-if="!['project', 'views'].includes(section)"
      class="grid gap-4 md:grid-cols-2 xl:grid-cols-4"
    >
      <Card
        v-for="metric in summaryCards"
        :key="metric.label"
        class="min-w-0 gap-3 p-4 shadow-none"
      >
        <div class="flex items-center justify-between">
          <div class="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon
              :name="metric.icon"
              class="size-5"
            />
          </div>
          <Badge
            :variant="metric.tone"
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

    <section
      v-if="section === 'workspace'"
      class="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,0.9fr)]"
    >
      <Card class="min-w-0 overflow-hidden p-0 shadow-none">
        <div class="flex flex-col gap-3 border-b p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 class="text-lg font-semibold">
              برد فضای کاری
            </h2>
            <p class="text-sm text-muted-foreground">
              همه‌ی امور محوله فعال این فضای کاری.
            </p>
          </div>

          <div class="relative w-full max-w-xs">
            <Icon
              name="lucide:search"
              class="absolute left-3 top-2.5 size-4 text-muted-foreground"
            />
            <Input
              v-model="store.filters.search"
              dir="rtl"
              class="pl-9 pr-9 text-right placeholder:text-right"
              placeholder="جستجوی امور محوله..."
            />
          </div>
        </div>

        <div class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,17rem),1fr))] gap-4 p-4">
          <div
            v-for="column in boardColumns"
            :key="column"
            class="min-w-0 rounded-xl border bg-muted/30 p-3"
          >
            <div class="mb-3 flex items-center justify-between">
              <span class="text-sm font-medium text-foreground">
                {{ columnLabel(column) }}
              </span>
              <Badge variant="secondary">
                {{ boardTasks[column]?.length || 0 }}
              </Badge>
            </div>

            <div class="space-y-3">
              <div
                v-for="task in visibleBoard(column)"
                :key="task.id"
                class="min-w-0 cursor-pointer overflow-hidden rounded-xl border bg-background p-3 shadow-sm transition-colors hover:border-primary/50 hover:bg-muted/20"
                @click="openTask(task.id, task.projectId)"
              >
                <div class="mb-3 flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
                  <TaskPriorityBadge :priority="task.priority" />
                  <span class="min-w-0 break-words [overflow-wrap:anywhere] text-[11px] text-muted-foreground">
                    {{ getProjectName(task.projectId) }}
                  </span>
                </div>

                <h3 class="font-medium leading-5 break-words [overflow-wrap:anywhere]">
                  {{ task.title }}
                </h3>
                <p class="mt-2 line-clamp-2 text-sm text-muted-foreground break-words [overflow-wrap:anywhere]">
                  {{ task.description }}
                </p>

                <div class="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <span class="min-w-0 break-words [overflow-wrap:anywhere]">{{ getAssigneeNames(task) }}</span>
                  <span class="whitespace-nowrap">{{ fmtDue(task) }}</span>
                </div>

                <div class="mt-3">
                  <div class="mb-1 flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
                    <span>پیشرفت</span>
                    <span>{{ task.progress }}٪</span>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      class="h-full rounded-full bg-primary"
                      :style="{ width: `${task.progress}%` }"
                    />
                  </div>
                </div>

                <div class="mt-4 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    @click.stop="advanceTask(task.id)"
                  >
                    مرحله بعد
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    @click.stop="markDone(task.id)"
                  >
                    {{ store.isAssignee(task) ? 'درخواست تأیید' : 'انجام شد' }}
                  </Button>
                </div>
              </div>

              <Button
                v-if="(boardTasks[column]?.length || 0) > BOARD_LIMIT"
                variant="ghost"
                size="sm"
                class="w-full justify-center gap-1 text-xs text-muted-foreground"
                @click="toggleColumn(column)"
              >
                <Icon
                  :name="expandedColumns.has(column) ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                  class="size-3.5"
                />
                {{ expandedColumns.has(column) ? 'نمایش کمتر' : `بیشتر (${(boardTasks[column]?.length || 0) - BOARD_LIMIT} مورد دیگر)` }}
              </Button>

              <div
                v-if="!boardTasks[column]?.length"
                class="rounded-xl border border-dashed border-border bg-background/50 p-4 text-center text-sm text-muted-foreground"
              >
                موردی در این ستون نیست.
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div class="min-w-0 space-y-6">
        <PrintableChart
          title="Monthly Productivity Overview"
          class="gap-4 p-4 shadow-none"
        >
          <div class="pl-16">
            <h3 class="text-base font-semibold">
              Monthly Productivity Overview
            </h3>
            <p class="text-xs text-muted-foreground">
              وضعیت بهره‌وری و فعالیت اعضا در بازهٔ ماهانه
            </p>
          </div>
          <TaskProductivityChart :points="monthlyPoints" />
          <div
            v-if="memberMonthActivity.length"
            class="space-y-2 border-t pt-3"
          >
            <p class="text-xs font-medium text-muted-foreground">
              فعالیت اعضا در {{ currentMonthLabel }} (وظایف تکمیل‌شده)
            </p>
            <div
              v-for="member in memberMonthActivity"
              :key="member.name"
              class="space-y-1"
            >
              <div class="flex items-center justify-between gap-3 text-sm">
                <span class="min-w-0 truncate">{{ member.name }}</span>
                <span class="shrink-0 whitespace-nowrap text-xs text-muted-foreground">{{ member.completed }} از {{ member.assigned }}</span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  class="h-full rounded-full bg-success"
                  :style="{ width: `${member.width}%` }"
                />
              </div>
            </div>
          </div>
        </PrintableChart>

        <Card class="gap-4 p-4 shadow-none">
          <h3 class="text-base font-semibold">
            وضعیت اولویت‌ها
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
      </div>
    </section>

    <section
      v-else-if="section === 'your-work'"
      class="space-y-6"
    >
      <Card class="overflow-hidden p-0 shadow-none">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b p-4">
          <div class="min-w-0">
            <h2 class="text-lg font-semibold">
              امور محوله من
            </h2>
            <p class="text-sm text-muted-foreground">
              اموری که به شما واگذار شده است.
            </p>
          </div>
          <Badge variant="info">
            {{ myTasks.length }} مورد فعال
          </Badge>
        </div>

        <div class="space-y-3 p-4">
          <div
            v-for="task in myTasks"
            :key="task.id"
            class="rounded-xl border bg-background p-4"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div class="min-w-0">
                <div class="mb-2 flex flex-wrap items-center gap-2">
                  <TaskPriorityBadge :priority="task.priority" />
                  <span class="text-xs text-muted-foreground">
                    {{ getProjectName(task.projectId) }}
                  </span>
                </div>
                <h3 class="font-medium break-words [overflow-wrap:anywhere]">
                  {{ task.title }}
                </h3>
              </div>

              <div class="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  @click="advanceTask(task.id)"
                >
                  به‌روزرسانی
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  @click="markDone(task.id)"
                >
                  {{ store.isAssignee(task) ? 'درخواست تأیید' : 'انجام شد' }}
                </Button>
              </div>
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span>موعد: {{ fmtDue(task) }}</span>
              <span>وضعیت: {{ columnLabel(task.status) }}</span>
              <span>پیشرفت: {{ task.progress }}٪</span>
            </div>
          </div>
        </div>
      </Card>
    </section>

    <section
      v-else-if="section === 'project' && projectId"
      class="min-h-[calc(100vh-7rem)] space-y-4 rounded-lg bg-background"
    >
      <div class="flex min-h-20 flex-wrap items-center gap-3 border-b border-border/70 px-2 py-3 sm:flex-nowrap">
        <div class="flex items-center gap-3 text-sm font-medium text-foreground">
          <span class="flex size-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Icon
              name="lucide:house"
              class="size-5"
            />
          </span>
          <span class="max-w-44 truncate">{{ selectedProject?.name }}</span>
        </div>
        <Icon
          name="lucide:chevron-right"
          class="size-4 text-muted-foreground"
        />
        <div class="flex items-center gap-2 text-lg font-semibold">
          <Icon
            name="lucide:clipboard-list"
            class="size-5 text-muted-foreground"
          />
          امور محوله
          <Badge
            variant="secondary"
            class="rounded-full bg-primary/20 text-primary"
          >
            {{ projectDetailTasks.length }}
          </Badge>
        </div>
      </div>

      <div class="overflow-hidden rounded-xl border border-border/80 bg-card">
        <div class="flex flex-wrap items-center gap-2 border-b border-border/80 px-5 py-4">
          <div class="flex min-w-0 items-center gap-3">
            <span class="flex size-6 shrink-0 items-center justify-center rounded-full border border-dashed border-muted-foreground/50 text-xs text-muted-foreground">
              <Icon name="lucide:circle-dashed" class="size-3.5" />
            </span>
            <h2 class="truncate text-lg font-semibold">
              همه‌ی امور محوله {{ projectDetailTasks.length }}
            </h2>
            <Button
              variant="ghost"
              size="icon"
              class="size-8 rounded-md text-muted-foreground"
              aria-label="افزودن امور محوله"
              @click="openProjectTaskDialog"
            >
              <Icon name="lucide:plus" class="size-4" />
            </Button>
          </div>

          <div class="ml-auto flex flex-wrap items-center gap-2">
            <div class="relative w-48">
              <Icon name="lucide:search" class="absolute left-3 top-2.5 size-4 text-muted-foreground" />
              <Input v-model="projectSearch" dir="rtl" class="h-9 pl-9 pr-9 text-right placeholder:text-right" placeholder="جستجوی امور محوله..." />
            </div>
            <Button
              variant="outline"
              class="h-9 gap-2 rounded-md"
              @click="openProjectTaskDialog"
            >
              <Icon name="lucide:plus" class="size-4" />
              افزودن امور محوله
            </Button>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-border/80 px-5 py-3">
          <div class="flex items-center gap-1 rounded-lg border border-border/80 bg-muted/30 p-1">
            <Button
              :variant="projectView === 'list' ? 'secondary' : 'ghost'"
              size="icon"
              class="size-8 rounded-md"
              aria-label="نمای فهرست"
              title="نمای فهرست"
              @click="projectView = 'list'"
            >
              <Icon name="lucide:list" class="size-4" />
            </Button>
            <Button
              :variant="projectView === 'board' ? 'secondary' : 'ghost'"
              size="icon"
              class="size-8 rounded-md"
              aria-label="نمای برد"
              title="نمای برد"
              @click="projectView = 'board'"
            >
              <Icon name="lucide:columns-2" class="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              class="size-8 rounded-md text-muted-foreground"
              aria-label="نمای تقویم"
              title="رفتن به تقویم"
              @click="navigateTo('/tasks/calendar')"
            >
              <Icon name="lucide:calendar-days" class="size-4" />
            </Button>
          </div>

          <div
            v-if="selectedIds.size"
            class="flex flex-wrap items-center gap-2 text-sm"
          >
            <span class="text-muted-foreground">{{ selectedIds.size }} مورد انتخاب شد</span>
            <Button size="sm" variant="outline" class="gap-1.5" @click="bulkDone">
              <Icon name="lucide:check-check" class="size-4" /> انجام شد
            </Button>
            <Button size="sm" variant="outline" class="gap-1.5" @click="bulkArchive">
              <Icon name="lucide:archive" class="size-4" /> بایگانی
            </Button>
            <Button size="sm" variant="ghost" @click="selectedIds = new Set()">
              لغو انتخاب
            </Button>
          </div>

          <div class="flex items-center gap-2">
            <Button
              variant="outline"
              class="h-9 gap-2 rounded-md"
              title="ستون‌ها: عنوان، توضیحات، اولویت (کم/متوسط/زیاد/فوری)، موعد (۱۴۰۵/۰۸/۲۰)"
              @click="csvInput?.click()"
            >
              <Icon name="lucide:upload" class="size-4" />
              درون‌ریزی CSV
            </Button>
            <input
              ref="csvInput"
              type="file"
              accept=".csv,text/csv"
              class="hidden"
              @change="onCsvPicked"
            >
          </div>
        </div>

        <!-- board view of this department -->
        <div
          v-if="projectView === 'board'"
          class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,16rem),1fr))] gap-4 bg-muted/10 p-4"
        >
          <div
            v-for="column in ['todo', 'in-progress', 'review', 'done']"
            :key="column"
            class="min-w-0 rounded-xl border bg-muted/20 p-3"
          >
            <div class="mb-3 flex items-center justify-between">
              <span class="text-sm font-medium">{{ columnLabel(column) }}</span>
              <Badge variant="secondary">{{ projectBoard[column]?.length || 0 }}</Badge>
            </div>
            <div class="max-h-[28rem] space-y-2 overflow-y-auto pr-0.5">
              <button
                v-for="task in projectBoard[column]"
                :key="task.id"
                type="button"
                class="block w-full rounded-lg border bg-background p-3 text-right text-sm hover:border-primary"
                @click="openTask(task.id)"
              >
                <span class="block break-words font-medium [overflow-wrap:anywhere]">{{ task.title }}</span>
                <span class="mt-1 flex items-center justify-between gap-2 text-xs text-muted-foreground">
                  <span>{{ fmtDue(task) }}</span>
                  <TaskPriorityBadge :priority="task.priority" />
                </span>
              </button>
              <p v-if="!projectBoard[column]?.length" class="py-4 text-center text-xs text-muted-foreground">
                موردی نیست
              </p>
            </div>
          </div>
        </div>

        <div
          v-if="projectView === 'list'"
          class="divide-y divide-border/80"
        >
          <div
            v-for="task in projectDetailTasks"
            :key="task.id"
            class="group flex min-h-16 cursor-pointer items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/30 sm:px-5"
            @click="openTask(task.id)"
          >
            <input
              type="checkbox"
              class="size-4 shrink-0 accent-primary"
              :aria-label="`انتخاب ${task.title}`"
              :checked="selectedIds.has(task.id)"
              @click.stop
              @change="toggleSelected(task.id)"
            >
            <button
              type="button"
              class="flex size-7 shrink-0 items-center justify-center rounded-md border border-border/80 text-muted-foreground hover:border-primary hover:text-primary"
              :aria-label="`مرحله بعد: ${task.title}`"
              title="مرحله بعد"
              @click.stop="advanceTask(task.id)"
            >
              <Icon name="lucide:minus" class="size-3.5" />
            </button>

            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium text-primary">
                  {{ selectedProject?.code }}-{{ task.id.replace('task-', '') }}
                </span>
                <span class="truncate text-sm text-foreground">
                  {{ task.title }}
                </span>
              </div>
              <p class="mt-1 truncate text-xs text-muted-foreground">
                {{ task.description }}
              </p>
            </div>

            <TaskStatusBadge :status="task.status" class="hidden shrink-0 sm:inline-flex" />
            <span class="hidden items-center gap-1 rounded-md bg-muted/50 px-2 py-1 text-xs text-muted-foreground md:flex">
              <Icon name="lucide:calendar-days" class="size-3.5" />
              {{ fmtDue(task) }}
            </span>
            <span
              class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground"
              :title="getAssigneeNames(task)"
            >
              {{ getProjectInitial(getAssigneeNames(task)) }}
            </span>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button
                  variant="ghost"
                  size="icon"
                  class="size-8 shrink-0 text-muted-foreground opacity-60 transition-opacity group-hover:opacity-100"
                  aria-label="عملیات امور محوله"
                  @click.stop
                >
                  <Icon name="lucide:ellipsis" class="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem @select="openTask(task.id)">
                  <Icon name="lucide:external-link" class="size-4" /> باز کردن
                </DropdownMenuItem>
                <DropdownMenuItem @select="advanceTask(task.id)">
                  <Icon name="lucide:arrow-left-to-line" class="size-4" /> مرحله بعد
                </DropdownMenuItem>
                <DropdownMenuItem @select="markDone(task.id)">
                  <Icon name="lucide:check" class="size-4" /> {{ store.isAssignee(task) ? 'درخواست تأیید تکمیل' : 'انجام شد' }}
                </DropdownMenuItem>
                <DropdownMenuItem @select="archiveOne(task.id)">
                  <Icon name="lucide:archive" class="size-4" /> بایگانی
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div v-if="!projectDetailTasks.length" class="px-5 py-16 text-center">
            <p class="text-sm text-muted-foreground">در این کارتابل واحد، امور محوله‌ای وجود ندارد.</p>
            <Button variant="outline" class="mt-4 gap-2 rounded-md" @click="openProjectTaskDialog">
              <Icon name="lucide:plus" class="size-4" />
              امور محوله جدید
            </Button>
          </div>
        </div>

        <Button
          v-if="projectDetailTasks.length"
          variant="ghost"
          class="m-4 gap-2 border border-dashed border-border/80 text-muted-foreground"
          @click="openProjectTaskDialog"
        >
          <Icon name="lucide:plus" class="size-4" />
          امور محوله جدید
        </Button>
      </div>
    </section>

    <section
      v-else-if="section === 'project'"
      class="space-y-6"
    >
      <div class="overflow-hidden rounded-xl border border-border/80 bg-card">
        <div class="flex flex-col gap-3 border-b border-border/80 bg-muted/30 p-4 md:flex-row md:items-center md:justify-between">
          <div class="flex items-center gap-3">
            <div class="flex size-9 items-center justify-center rounded-md bg-primary/15 text-primary">
              <Icon
                name="lucide:building-2"
                class="size-5"
              />
            </div>
            <div>
              <h2 class="text-2xl font-semibold text-foreground">
                کارتابل واحد
              </h2>
              <p class="text-xs text-muted-foreground">
                {{ visibleProjects.length }} واحد · {{ prefs.favorites.value.length }} مورد در علاقه‌مندی‌ها
              </p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <div
              v-if="projectSearchOpen"
              class="relative"
            >
              <Icon
                name="lucide:search"
                class="absolute right-3 top-3 size-4 text-muted-foreground"
              />
              <Input
                v-model="projectQuery"
                dir="rtl"
                class="h-10 w-56 pr-9 text-right"
                placeholder="جستجوی نام یا کد واحد..."
                autofocus
              />
            </div>
            <Button
              variant="outline"
              size="icon"
              class="h-10 w-10 rounded-md"
              :class="projectSearchOpen && 'border-primary text-primary'"
              aria-label="جستجوی کارتابل واحد"
              title="جستجو"
              @click="toggleProjectSearch"
            >
              <Icon
                :name="projectSearchOpen ? 'lucide:x' : 'lucide:search'"
                class="size-4"
              />
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button
                  variant="outline"
                  class="h-10 rounded-md px-3 text-sm"
                >
                  <span class="flex items-center gap-2">
                    <Icon
                      name="lucide:arrow-up-down"
                      class="size-4"
                    />
                    {{ PROJECT_SORT_LABELS[projectSort] }}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem
                  v-for="(label, key) in PROJECT_SORT_LABELS"
                  :key="key"
                  @select="projectSort = key"
                >
                  {{ label }}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button
                  variant="outline"
                  class="h-10 rounded-md px-3 text-sm"
                  :class="(onlyFavorites || onlyWithTasks) && 'border-primary text-primary'"
                >
                  <span class="flex items-center gap-2">
                    <Icon
                      name="lucide:sliders-horizontal"
                      class="size-4"
                    />
                    فیلترها
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuCheckboxItem
                  :model-value="onlyFavorites"
                  @update:model-value="onlyFavorites = !!$event"
                >
                  فقط علاقه‌مندی‌ها
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  :model-value="onlyWithTasks"
                  @update:model-value="onlyWithTasks = !!$event"
                >
                  فقط واحدهای دارای امور محوله
                </DropdownMenuCheckboxItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <Dialog v-model:open="projectDialogOpen">
              <DialogTrigger as-child>
                <Button class="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground">
                  <span class="flex items-center gap-2">
                    <Icon
                      name="lucide:plus"
                      class="size-4"
                    />
                    افزودن کارتابل واحد
                  </span>
                </Button>
              </DialogTrigger>

              <DialogContent class="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>ایجاد کارتابل واحد</DialogTitle>
                  <DialogDescription>
                    یک کارتابل واحد جدید (واحد سازمانی) ایجاد کنید.
                  </DialogDescription>
                </DialogHeader>

                <form
                  class="space-y-4"
                  @submit.prevent="submitProject"
                >
                  <label class="space-y-2 text-sm">
                    <span class="text-muted-foreground">نام کارتابل واحد</span>
                    <Input
                      v-model="projectForm.name"
                      dir="rtl"
                      class="text-right placeholder:text-right"
                      placeholder="مثلاً عملیات"
                      required
                    />
                  </label>

                  <div class="grid gap-4 sm:grid-cols-2">
                    <label class="space-y-2 text-sm">
                      <span class="text-muted-foreground">کد</span>
                      <Input
                        v-model="projectForm.code"
                        dir="rtl"
                        class="text-right placeholder:text-right"
                        placeholder="مثلاً OPS"
                      />
                    </label>

                    <label class="space-y-2 text-sm">
                      <span class="text-muted-foreground">رنگ</span>
                      <select
                        v-model="projectForm.accent"
                        class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      >
                        <option value="blue">آبی</option>
                        <option value="green">سبز</option>
                        <option value="indigo">نیلی</option>
                        <option value="slate">طوسی</option>
                      </select>
                    </label>
                  </div>

                  <label class="space-y-2 text-sm">
                    <span class="text-muted-foreground">توضیحات</span>
                    <textarea
                      v-model="projectForm.description"
                      rows="3"
                      dir="rtl"
                      class="flex min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-right text-sm placeholder:text-right"
                      placeholder="توضیح کوتاه کارتابل واحد"
                    />
                  </label>

                  <DialogFooter>
                    <Button
                      type="button"
                      variant="outline"
                      @click="projectDialogOpen = false"
                    >
                      انصراف
                    </Button>
                    <Button type="submit">
                      ایجاد کارتابل واحد
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <div class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,19rem),1fr))] gap-4 p-3 sm:p-4">
          <NuxtLink
            v-for="project in visibleProjects"
            :key="project.id"
            :to="`/tasks/project/${project.id}`"
            class="group block min-w-0 overflow-hidden rounded-xl border border-border/80 bg-background transition-shadow hover:shadow-md"
          >
            <div
              :class="[
                'flex min-h-36 items-start justify-between gap-3 p-5',
                projectAccent(project.accent),
              ]"
            >
              <div class="mt-2 flex min-w-0 items-center gap-4 text-white">
                <div class="flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/30 bg-white/10 backdrop-blur-sm">
                  <img
                    v-if="prefs.logos.value[project.id]"
                    :src="prefs.logos.value[project.id]"
                    alt=""
                    class="size-full object-cover"
                  >
                  <Icon
                    v-else
                    name="lucide:building-2"
                    class="size-5"
                  />
                </div>
                <div class="min-w-0 leading-tight">
                  <div class="text-xl font-semibold tracking-tight sm:text-2xl break-words [overflow-wrap:anywhere]">
                    {{ project.name }}
                  </div>
                  <div class="mt-1 truncate text-xs text-white/75">
                    {{ project.code }}
                  </div>
                </div>
              </div>

              <!-- star: add / remove from favourites (pinned first); never opens the card -->
              <button
                type="button"
                class="flex size-9 shrink-0 items-center justify-center rounded-full border border-white/25 bg-white/10 text-white/90 transition hover:bg-white/20"
                :class="prefs.isFavorite(project.id) && 'bg-white/25'"
                :aria-pressed="prefs.isFavorite(project.id)"
                :aria-label="prefs.isFavorite(project.id) ? 'حذف از علاقه‌مندی‌ها' : 'افزودن به علاقه‌مندی‌ها'"
                :title="prefs.isFavorite(project.id) ? 'حذف از علاقه‌مندی‌ها' : 'افزودن به علاقه‌مندی‌ها'"
                @click.prevent.stop="toggleProjectFavorite(project)"
              >
                <Icon
                  name="lucide:star"
                  class="size-4"
                  :class="prefs.isFavorite(project.id) && 'fill-yellow-300 text-yellow-300'"
                />
              </button>
            </div>

            <div class="flex items-center justify-between gap-3 bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
              <span class="min-w-0 truncate font-medium text-foreground/90">
                {{ project.description || 'بدون توضیح' }}
              </span>

              <button
                type="button"
                class="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-foreground/70 hover:text-foreground"
                aria-label="تنظیمات کارتابل واحد"
                title="تنظیمات"
                @click.prevent.stop="openProjectSettings(project)"
              >
                <Icon
                  name="lucide:settings"
                  class="size-4"
                />
              </button>
            </div>

            <div class="flex items-center justify-between gap-3 border-t border-border/80 bg-muted/30 px-4 py-3">
              <!-- the department's picture instead of the responsible person's name -->
              <span class="inline-flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-full border bg-background">
                <img
                  v-if="prefs.logos.value[project.id]"
                  :src="prefs.logos.value[project.id]"
                  alt=""
                  class="size-full object-cover"
                >
                <Icon
                  v-else
                  name="lucide:building-2"
                  class="size-4 text-muted-foreground"
                />
              </span>
              <span class="flex items-center gap-1.5 whitespace-nowrap text-xs text-muted-foreground">
                <Icon
                  name="lucide:list-checks"
                  class="size-3.5"
                />
                {{ getProjectTaskCount(project.id) }} مورد
              </span>
            </div>
          </NuxtLink>

          <div
            v-if="!visibleProjects.length"
            class="col-span-full rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground"
          >
            واحدی با این فیلتر پیدا نشد.
          </div>
        </div>
      </div>

      <!-- department settings: picture (logo) + quick actions -->
      <Dialog v-model:open="settingsOpen">
        <DialogContent class="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>تنظیمات {{ settingsProject?.name }}</DialogTitle>
            <DialogDescription>تصویر این واحد روی کارت و کارتابل نمایش داده می‌شود (فقط برای شما).</DialogDescription>
          </DialogHeader>
          <div
            v-if="settingsProject"
            class="space-y-4"
          >
            <div class="flex items-center gap-4">
              <span class="inline-flex size-16 items-center justify-center overflow-hidden rounded-full border bg-muted/40">
                <img
                  v-if="prefs.logos.value[settingsProject.id]"
                  :src="prefs.logos.value[settingsProject.id]"
                  alt=""
                  class="size-full object-cover"
                >
                <Icon
                  v-else
                  name="lucide:building-2"
                  class="size-7 text-muted-foreground"
                />
              </span>
              <div class="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  class="gap-2"
                  @click="logoInput?.click()"
                >
                  <Icon
                    name="lucide:image-up"
                    class="size-4"
                  /> انتخاب تصویر
                </Button>
                <Button
                  v-if="prefs.logos.value[settingsProject.id]"
                  variant="ghost"
                  size="sm"
                  @click="prefs.removeLogo(settingsProject.id)"
                >
                  حذف تصویر
                </Button>
              </div>
              <input
                ref="logoInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="onLogoPicked"
              >
            </div>
            <div class="flex flex-wrap gap-2">
              <Button
                class="gap-2"
                as-child
              >
                <NuxtLink :to="`/tasks/project/${settingsProject.id}`">
                  <Icon
                    name="lucide:arrow-left-circle"
                    class="size-4"
                  /> ورود به کارتابل
                </NuxtLink>
              </Button>
              <Button
                variant="outline"
                class="gap-2"
                @click="toggleProjectFavorite(settingsProject)"
              >
                <Icon
                  name="lucide:star"
                  class="size-4"
                  :class="prefs.isFavorite(settingsProject.id) && 'fill-yellow-400 text-yellow-400'"
                />
                {{ prefs.isFavorite(settingsProject.id) ? 'حذف از علاقه‌مندی‌ها' : 'افزودن به علاقه‌مندی‌ها' }}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </section>

    <section
      v-else-if="section === 'views'"
      class="space-y-6"
    >
      <Card class="overflow-hidden bg-card p-0 text-card-foreground shadow-none">
        <div class="flex flex-col gap-3 border-b p-3 sm:flex-row sm:items-center sm:justify-between sm:p-4">
          <div>
            <h2 class="text-lg font-semibold">
              همه‌ی امور محوله {{ sectionTasks.length }}
            </h2>
          </div>

          <div class="flex w-full items-center gap-1 rounded-lg border bg-muted/30 p-1 sm:w-auto">
            <Button
              v-for="mode in viewModes"
              :key="mode.value"
              :variant="viewMode === mode.value ? 'secondary' : 'ghost'"
              size="icon"
              class="size-9 rounded-md"
              :aria-label="mode.label"
              :title="mode.label"
              @click="viewMode = mode.value"
            >
              <Icon
                :name="mode.icon"
                class="size-4"
              />
            </Button>
          </div>
        </div>

        <div
          v-if="viewMode === 'list'"
          class="divide-y"
        >
          <div
            v-for="task in sectionTasks"
            :key="task.id"
            class="flex cursor-pointer flex-col items-start gap-2 px-4 py-3 transition-colors hover:bg-muted/20 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3"
            @click="openTask(task.id, task.projectId)"
          >
            <span class="flex size-8 items-center justify-center rounded-md border text-xs text-muted-foreground">
              {{ getProjectInitial(getProjectName(task.projectId)) }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="font-medium break-words [overflow-wrap:anywhere]">
                {{ task.title }}
              </p>
              <p class="mt-1 truncate text-xs text-muted-foreground">
                {{ task.description }}
              </p>
            </div>
            <span class="text-xs text-muted-foreground sm:ml-auto">
              {{ getProjectName(task.projectId) }}
            </span>
            <TaskPriorityBadge :priority="task.priority" />
            <TaskStatusBadge :status="task.status" />
            <span class="text-xs text-muted-foreground">
              {{ fmtDue(task) }}
            </span>
          </div>

          <div
            v-if="!sectionTasks.length"
            class="p-10 text-center text-sm text-muted-foreground"
          >
            در این نما امور محوله‌ای وجود ندارد.
          </div>
        </div>

        <div
          v-else-if="viewMode === 'board'"
          class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,17rem),1fr))] gap-4 bg-muted/10 p-4"
        >
          <div
            v-for="column in boardColumns"
            :key="column"
            class="min-w-0 rounded-xl border bg-muted/20 p-3"
          >
            <div class="mb-3 flex items-center justify-between">
              <span class="text-sm font-medium">
                {{ columnLabel(column) }}
              </span>
              <Badge variant="secondary">
                {{ boardTasks[column]?.length || 0 }}
              </Badge>
            </div>
            <div class="space-y-3">
              <div
                v-for="task in visibleBoard(column)"
                :key="task.id"
                class="min-w-0 cursor-pointer overflow-hidden rounded-xl border bg-background p-3 shadow-sm transition-colors hover:border-primary/50 hover:bg-muted/20"
                @click="openTask(task.id, task.projectId)"
              >
                <div class="flex flex-wrap items-start justify-between gap-x-2 gap-y-1">
                  <TaskPriorityBadge :priority="task.priority" />
                  <span class="min-w-0 break-words [overflow-wrap:anywhere] text-[11px] text-muted-foreground">
                    {{ getProjectName(task.projectId) }}
                  </span>
                </div>
                <p class="mt-3 font-medium leading-5 break-words [overflow-wrap:anywhere]">
                  {{ task.title }}
                </p>
                <p class="mt-2 line-clamp-2 text-sm text-muted-foreground break-words [overflow-wrap:anywhere]">
                  {{ task.description }}
                </p>
                <div class="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <span class="min-w-0 break-words [overflow-wrap:anywhere]">{{ getAssigneeNames(task) }}</span>
                  <span class="whitespace-nowrap">{{ fmtDue(task) }}</span>
                </div>
              </div>
              <Button
                v-if="(boardTasks[column]?.length || 0) > BOARD_LIMIT"
                variant="ghost"
                size="sm"
                class="w-full justify-center gap-1 text-xs text-muted-foreground"
                @click="toggleColumn(column)"
              >
                <Icon
                  :name="expandedColumns.has(column) ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                  class="size-3.5"
                />
                {{ expandedColumns.has(column) ? 'نمایش کمتر' : `بیشتر (${(boardTasks[column]?.length || 0) - BOARD_LIMIT} مورد دیگر)` }}
              </Button>

              <div
                v-if="!boardTasks[column]?.length"
                class="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground"
              >
                بدون امور محوله
              </div>
            </div>
          </div>
        </div>

        <div v-else>
          <div class="flex flex-col gap-3 border-b px-3 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:px-4">
            <div class="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                class="size-8"
                aria-label="ماه قبل"
                @click="changeCalendarMonth(-1)"
              >
                <Icon name="lucide:chevron-left" class="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                class="size-8"
                aria-label="ماه بعد"
                @click="changeCalendarMonth(1)"
              >
                <Icon name="lucide:chevron-right" class="size-4" />
              </Button>
              <h3 class="ml-2 text-base font-semibold sm:text-lg">
                {{ calendarMonthLabel }}
              </h3>
              <Button
                variant="outline"
                class="ml-2 h-8 rounded-md px-3 text-xs"
                @click="goToToday"
              >
                امروز
              </Button>
            </div>

            <div class="flex items-center gap-1 self-start rounded-md border bg-muted/30 p-1 sm:self-auto">
              <Button
                variant="secondary"
                class="h-8 rounded px-3 text-xs"
              >
                ماه
              </Button>
              <Button
                variant="ghost"
                class="h-8 rounded px-3 text-xs text-muted-foreground"
              >
                هفته
              </Button>
              <label class="ml-2 flex items-center gap-2 px-2 text-xs text-muted-foreground">
                <input
                  v-model="showWeekends"
                  type="checkbox"
                  class="size-4 accent-primary"
                >
                نمایش جمعه
              </label>
            </div>
          </div>

          <div class="overflow-x-auto">
            <div class="min-w-[40rem]">
              <div :class="['grid border-b bg-muted/20', showWeekends ? 'grid-cols-7' : 'grid-cols-6']">
                <div
                  v-for="day in visibleWeekdays"
                  :key="day"
                  class="border-r px-3 py-2 text-xs font-semibold text-muted-foreground last:border-r-0"
                >
                  {{ day }}
                </div>
              </div>

              <div
                :class="[
                  'grid gap-px bg-border',
                  showWeekends ? 'grid-cols-7' : 'grid-cols-6',
                ]"
              >
                <div
                  v-for="day in calendarDays"
                  :key="day.date"
                  :class="[
                    'min-h-32 bg-background p-2 sm:min-h-40',
                    !day.isCurrentMonth && 'bg-muted/20 text-muted-foreground',
                  ]"
                >
                  <span
                    :class="[
                      'flex size-7 items-center justify-center rounded-full text-sm',
                      day.isToday && 'bg-primary font-semibold text-primary-foreground',
                    ]"
                  >
                    {{ day.dayNumber }}
                  </span>

                  <div class="mt-2 space-y-1">
                    <div
                      v-for="task in day.tasks"
                      :key="task.id"
                      class="truncate rounded-md border border-success/30 bg-success/10 px-2 py-1 text-xs text-foreground"
                      :title="task.title"
                    >
                      <span class="mr-1 inline-block size-2 rounded-full bg-success" />
                      {{ task.title }}
                    </div>
                    <div
                      v-for="task in day.upcoming"
                      :key="`${task.id}-${day.date}`"
                      class="truncate rounded-md border border-dashed border-primary/50 bg-primary/5 px-2 py-1 text-xs text-foreground"
                      :title="`${task.title} (تکرار آینده)`"
                    >
                      <Icon name="lucide:repeat" class="mr-1 inline-block size-3 text-primary" />
                      {{ task.title }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </section>

    <section
      v-else-if="section === 'analytics'"
      class="space-y-6"
    >
      <TaskKpiPanel
        :tasks="store.tasks"
        :users="store.users"
        :projects="store.projects"
        :assignee-names="getAssigneeNames"
        :status-label="columnLabel"
        :due-text="fmtDue"
        @export-excel="exportReport"
      />
    </section>

    <section
      v-else-if="section === 'drafts'"
      class="space-y-6"
    >
      <Card class="overflow-hidden p-0 shadow-none">
        <div class="border-b p-4">
          <h2 class="text-lg font-semibold">
            پیش‌نویس‌ها
          </h2>
        </div>
        <div class="space-y-3 p-4">
          <div
            v-for="task in drafts"
            :key="task.id"
            class="rounded-xl border bg-background p-4"
          >
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="min-w-0 flex-1">
                <p class="font-medium break-words [overflow-wrap:anywhere]">
                  {{ task.title }}
                </p>
                <p class="text-sm text-muted-foreground break-words [overflow-wrap:anywhere]">
                  {{ task.description }}
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                @click="publishTask(task.id)"
              >
                انتشار
              </Button>
            </div>
          </div>

          <div
            v-if="!drafts.length"
            class="rounded-xl border border-dashed border-border bg-background/50 p-6 text-center text-sm text-muted-foreground"
          >
            هنوز پیش‌نویسی وجود ندارد.
          </div>
        </div>
      </Card>
    </section>

    <section
      v-else
      class="space-y-6"
    >
      <Card class="overflow-hidden p-0 shadow-none">
        <div class="border-b p-4">
          <h2 class="text-lg font-semibold">
            بایگانی
          </h2>
        </div>
        <div class="space-y-3 p-4">
          <div
            v-for="task in archives"
            :key="task.id"
            class="rounded-xl border bg-background p-4"
          >
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="min-w-0 flex-1">
                <p class="font-medium break-words [overflow-wrap:anywhere]">
                  {{ task.title }}
                </p>
                <p class="text-sm text-muted-foreground break-words [overflow-wrap:anywhere]">
                  {{ task.description }}
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                @click="restoreTask(task.id)"
              >
                بازیابی
              </Button>
            </div>
          </div>

          <div
            v-if="!archives.length"
            class="rounded-xl border border-dashed border-border bg-background/50 p-6 text-center text-sm text-muted-foreground"
          >
            امور محوله‌ی بایگانی‌شده‌ای وجود ندارد.
          </div>
        </div>
      </Card>
    </section>
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import TaskPriorityBadge from '~/components/tasks/TaskPriorityBadge.vue'
import TaskProductivityChart from '~/components/tasks/TaskProductivityChart.vue'
import TaskKpiPanel from '~/components/tasks/TaskKpiPanel.vue'
import TaskStatusBadge from '~/components/tasks/TaskStatusBadge.vue'
import { projectOccurrences } from '~/utils/recurrence'
import { formatHours, kpiFor, monthlyCreatedVsCompleted, tehranDay } from '~/utils/taskKpi'
import {
  useTaskWorkspaceStore,
  type RecurrenceRule,
  type TaskEntity,
  type TaskPriority,
  type TaskSection,
  type TaskStatus,
} from '~/stores/taskWorkspace'

type Props = {
  section?: TaskSection
  projectId?: string
}

type TaskViewMode = 'list' | 'board' | 'calendar'

const props = withDefaults(defineProps<Props>(), {
  section: 'workspace',
})

const store = useTaskWorkspaceStore()
const dialogOpen = ref(false)
const projectDialogOpen = ref(false)
const projectSearch = ref('')
const viewMode = ref<TaskViewMode>('list')
const showWeekends = ref(true)
const viewModes: Array<{ value: TaskViewMode, label: string, icon: string }> = [
  { value: 'list', label: 'نمای شبکه‌ای', icon: 'lucide:layout-grid' },
  { value: 'board', label: 'نمای کانبان', icon: 'lucide:columns-3' },
  { value: 'calendar', label: 'نمای تقویم', icon: 'lucide:calendar-days' },
]

const projectForm = reactive({
  name: '',
  code: '',
  description: '',
  accent: 'blue' as 'blue' | 'green' | 'indigo' | 'slate',
})

store.setActiveSection(props.section)
onMounted(() => store.ensureLoaded())

const boardColumns = ['todo', 'in-progress', 'review', 'done'] as const

const columnLabel = (value: string) => {
  const labels: Record<string, string> = {
    'todo': 'در انتظار انجام',
    'in-progress': 'در حال انجام',
    'review': 'درخواست تأیید تکمیل',
    'done': 'انجام‌شده',
  }

  return labels[value] || value
}

const sectionMap: Record<TaskSection, { title: string, description: string }> = {
  'workspace': {
    title: 'نمای کلی فضای کاری',
    description: 'کارهای تیم، زمان‌بندی‌ها و اولویت‌های روزانه را یک‌جا مدیریت کنید.',
  },
  'your-work': {
    title: 'کارهای من',
    description: 'امور محوله واگذارشده به شما و مهم‌ترین اولویت‌ها.',
  },
  'project': {
    title: 'کارتابل واحد',
    description: 'پیگیری امور محوله در کارتابل واحدهای سازمان.',
  },
  'views': {
    title: 'نماها',
    description: 'برنامه‌ریزی امور محوله بر اساس تقویم شمسی و زمان‌بندی.',
  },
  'analytics': {
    title: 'تحلیل‌ها',
    description: 'روند انجام کارها، وضعیت اولویت‌ها و سرعت پیشرفت.',
  },
  'drafts': {
    title: 'پیش‌نویس‌ها',
    description: 'کارهایی که هنوز منتشر نشده‌اند.',
  },
  'archives': {
    title: 'بایگانی',
    description: 'امور محوله تکمیل‌شده یا بایگانی‌شده برای مراجعه‌ی بعدی.',
  },
}

const selectedProject = computed(() => props.projectId ? store.getProjectById(props.projectId) : undefined)
const sectionTitle = computed(() => selectedProject.value ? selectedProject.value.name : sectionMap[props.section].title)
const sectionDescription = computed(() => selectedProject.value
  ? `امور محوله و وضعیت پیشرفت کارتابل واحد ${selectedProject.value.name}`
  : sectionMap[props.section].description)
const summaryCards = computed(() => store.getSummaryCards(props.section))
const sectionTasks = computed(() => store.getTasksForSection(props.section))
const boardTasks = computed<Record<string, TaskEntity[]>>(() => {
  const map: Record<string, TaskEntity[]> = {
    'todo': [],
    'in-progress': [],
    'review': [],
    'done': [],
  }

  for (const task of sectionTasks.value) {
    const bucket = map[task.status]
    if (!bucket) {
      map[task.status] = [task]
      continue
    }

    bucket.push(task)
  }

  return map
})

const myTasks = computed<TaskEntity[]>(() => store.getTasksForSection('your-work'))
const projectDetailTasks = computed<TaskEntity[]>(() => {
  const term = projectSearch.value.trim().toLowerCase()

  return store.tasks.filter((task: TaskEntity) => {
    const belongsToProject = task.projectId === props.projectId && !task.isArchived
    const matchesSearch = !term || `${task.title} ${task.description}`.toLowerCase().includes(term)
    return belongsToProject && matchesSearch
  })
})
const drafts = computed<TaskEntity[]>(() => store.getTasksForSection('drafts'))
const archives = computed<TaskEntity[]>(() => store.getTasksForSection('archives'))
const completedTasks = computed<number>(() => store.tasks.filter((task: TaskEntity) => task.status === 'done').length)
const atRiskTasks = computed<number>(() => store.tasks.filter((task: TaskEntity) => task.priority === 'urgent' && task.status !== 'done').length)
const velocity = computed<number>(() => Math.min(96, Math.round((completedTasks.value / (store.tasks.length || 1)) * 100)))

// real numbers: how many (non-archived) tasks each visible project holds
const departmentSummary = computed<Array<{ label: string, value: number }>>(() =>
  store.projects.map(p => ({
    label: p.name,
    value: store.tasks.filter((t: TaskEntity) => t.projectId === p.id && !t.isArchived).length,
  })))

const workloadStats = computed<Array<{ name: string, count: number, width: number }>>(() => {
  const assignees = store.users.map((user: { name: string }) => user.name)
  const maxCount = Math.max(
    ...assignees.map((name: string) => {
      const user = store.users.find((item: { name: string }) => item.name === name)
      return user ? store.tasks.filter((task: TaskEntity) => task.assigneeIds.includes(user.id)).length : 0
    }),
    1,
  )

  return assignees.map((name: string) => {
    const user = store.users.find((item: { name: string }) => item.name === name)
    const count = user ? store.tasks.filter((task: TaskEntity) => task.assigneeIds.includes(user.id)).length : 0
    return {
      name,
      count,
      width: Math.max(30, (count / maxCount) * 100),
    }
  })
})

/* ── board tiles: only a few cards per column, the rest behind «بیشتر» ── */
const BOARD_LIMIT = 4
const expandedColumns = ref<Set<string>>(new Set())
const visibleBoard = (column: string): TaskEntity[] => {
  const list = boardTasks.value[column] ?? []
  return expandedColumns.value.has(column) ? list : list.slice(0, BOARD_LIMIT)
}
const toggleColumn = (column: string) => {
  const next = new Set(expandedColumns.value)
  if (next.has(column)) next.delete(column)
  else next.add(column)
  expandedColumns.value = next
}

/* ── Monthly Productivity Overview (dashboard) ── */
const monthlyPoints = computed(() => monthlyCreatedVsCompleted(store.tasks, 6))
const currentMonthLabel = computed(() => monthlyPoints.value[monthlyPoints.value.length - 1]?.label ?? '')
const memberMonthActivity = computed(() => {
  const now = isoToJalali(todayIso())!
  const rows = store.users.map((user: { id: string, name: string }) => {
    const mine = store.tasks.filter((t: TaskEntity) => t.assigneeIds.includes(user.id) && !t.isDraft && !t.isArchived)
    const doneThisMonth = mine.filter((t: TaskEntity) => {
      const j = t.status === 'done' ? isoToJalali(tehranDay(t.completedAt)) : null
      return j && j.jy === now.jy && j.jm === now.jm
    }).length
    return { name: user.name, completed: doneThisMonth, assigned: mine.length }
  }).filter(r => r.assigned > 0).sort((a, b) => b.completed - a.completed).slice(0, 6)
  const max = Math.max(1, ...rows.map(r => r.assigned))
  return rows.map(r => ({ ...r, width: Math.max(r.completed ? 6 : 0, (r.completed / max) * 100) }))
})

const prioritySummary = computed<Array<{ label: string, key: string, dotClass: string, count: number }>>(() => {
  const summary = [
    { label: 'فوری', key: 'urgent', dotClass: 'bg-destructive' },
    { label: 'زیاد', key: 'high', dotClass: 'bg-primary' },
    { label: 'متوسط', key: 'medium', dotClass: 'bg-warning' },
    { label: 'کم', key: 'low', dotClass: 'bg-success' },
  ]

  return summary.map((item: { label: string, key: string, dotClass: string }) => ({
    ...item,
    count: store.tasks.filter((task: TaskEntity) => task.priority === item.key).length,
  }))
})

const getProjectName = (projectId: string) => store.getProjectById(projectId)?.name || 'عمومی'
const getUserName = (userId: string) => store.getUserById(userId)?.name || 'بدون مسئول'
const getProjectInitial = (name: string) => name.trim().split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase() || 'پ'

/** all the people on a task (a task can have several), by name */
const getAssigneeNames = (task: TaskEntity) =>
  task.assigneeIds.length ? task.assigneeIds.map(id => getUserName(id)).join('، ') : 'بدون مسئول'
/** due date in Jalali (+ time, Tehran) */
const fmtDue = (task: TaskEntity) => formatDueDateTime(task.dueDate, task.dueTime) || 'بدون موعد'
/* ── department worklists: favourites (star), search / sort / filter, logo ── */
const prefs = useProjectPrefs()
const projectSearchOpen = ref(false)
const projectQuery = ref('')
const PROJECT_SORT_LABELS = { name: 'نام واحد', tasks: 'بیشترین امور محوله', newest: 'جدیدترین' } as const
const projectSort = ref<keyof typeof PROJECT_SORT_LABELS>('name')
const onlyFavorites = ref(false)
const onlyWithTasks = ref(false)
const toggleProjectSearch = () => {
  projectSearchOpen.value = !projectSearchOpen.value
  if (!projectSearchOpen.value) projectQuery.value = ''
}
const visibleProjects = computed(() => {
  const q = projectQuery.value.trim().toLowerCase()
  let list = store.projects.filter(p =>
    (!q || `${p.name} ${p.code} ${p.description}`.toLowerCase().includes(q))
    && (!onlyFavorites.value || prefs.isFavorite(p.id))
    && (!onlyWithTasks.value || getProjectTaskCount(p.id) > 0))
  list = [...list].sort((a, b) =>
    projectSort.value === 'tasks' ? getProjectTaskCount(b.id) - getProjectTaskCount(a.id)
      : projectSort.value === 'newest' ? Number(b.id) - Number(a.id)
        : a.name.localeCompare(b.name, 'fa'))
  // starred departments are pinned to the top
  return [...list.filter(p => prefs.isFavorite(p.id)), ...list.filter(p => !prefs.isFavorite(p.id))]
})
const toggleProjectFavorite = (project: { id: string, name: string }) => {
  const adding = !prefs.isFavorite(project.id)
  prefs.toggleFavorite(project.id)
  notify.success(adding ? `«${project.name}» به علاقه‌مندی‌ها اضافه شد` : `«${project.name}» از علاقه‌مندی‌ها حذف شد`)
}
const settingsOpen = ref(false)
const settingsProject = ref<{ id: string, name: string } | null>(null)
const logoInput = ref<HTMLInputElement | null>(null)
const openProjectSettings = (project: { id: string, name: string }) => {
  settingsProject.value = project
  settingsOpen.value = true
}
async function onLogoPicked(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !settingsProject.value) return
  try {
    await prefs.setLogo(settingsProject.value.id, file)
  }
  catch {
    notify.error('این تصویر خوانده نشد؛ فایل دیگری انتخاب کنید.')
  }
}
const getProjectTaskCount = (projectId: string) => store.tasks.filter((task: TaskEntity) => task.projectId === projectId).length
const openTask = (taskId: string, taskProjectId?: string) => navigateTo(`/tasks/project/${taskProjectId || props.projectId || store.tasks.find(task => task.id === taskId)?.projectId}/task/${taskId}`)

const projectAccent = (accent: string) => {
  const map: Record<string, string> = {
    blue: 'bg-[#4b6ecf] text-white',
    green: 'bg-[#1f8f6f] text-white',
    indigo: 'bg-[#3d5fa8] text-white',
    slate: 'bg-[#4c5f7a] text-white',
  }

  return map[accent] || map.blue
}

const defaultDue = () => {
  const [y, m, d] = todayIso().split('-').map(Number)
  return new Date(Date.UTC(y!, m! - 1, d! + 7)).toISOString().slice(0, 10)
}
const defaultProjectId = () => props.projectId || store.projects[0]?.id || ''

const form = reactive<{
  title: string
  projectId: string
  assigneeIds: string[]
  priority: TaskPriority
  status: TaskStatus
  dueDate: string
  dueTime: string
  recurrence: RecurrenceRule | null
  description: string
}>({
  title: '',
  projectId: '',
  assigneeIds: [],
  priority: 'medium',
  status: 'todo',
  dueDate: defaultDue(),
  dueTime: '',
  recurrence: null,
  description: '',
})

const projectUsers = computed(() => store.usersForProject(form.projectId))

// keep the assignees valid for the selected project (backend: an assignee must belong to the department)
watch(() => [form.projectId, store.users.length], () => {
  const allowed = store.usersForProject(form.projectId)
  form.assigneeIds = form.assigneeIds.filter(id => allowed.some(u => u.id === id))
  if (!form.assigneeIds.length) {
    const fallback = allowed.find(u => u.id === store.meId)?.id || allowed[0]?.id
    if (fallback) form.assigneeIds = [fallback]
  }
})

const createQuickTask = () => {
  form.title = 'امور محوله سریع'
  form.projectId = defaultProjectId()
  form.assigneeIds = [store.meId]
  form.priority = 'medium'
  form.status = 'todo'
  form.dueDate = defaultDue()
  form.dueTime = ''
  form.recurrence = null
  form.description = ''
  submitTask()
}

const openProjectTaskDialog = () => {
  form.projectId = defaultProjectId()
  form.assigneeIds = [store.meId]
  dialogOpen.value = true
}

const requestApproval = async (task: TaskEntity) => {
  if (task.status === 'review') {
    notify.info(`«${task.title}» از قبل در انتظار تأیید تکمیل است`)
    return
  }
  if (task.status === 'done') {
    return
  }
  try {
    await store.updateTaskStatus(task.id, 'review')
    notify.success(`«${task.title}»: درخواست تأیید تکمیل ثبت شد`)
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'ثبت درخواست تأیید تکمیل انجام نشد'))
  }
}

/* ── department detail: view switch, selection (bulk), per-task menu, CSV import ── */
const projectView = ref<'list' | 'board'>('list')
const projectBoard = computed<Record<string, TaskEntity[]>>(() => {
  const map: Record<string, TaskEntity[]> = { 'todo': [], 'in-progress': [], 'review': [], 'done': [] }
  for (const t of projectDetailTasks.value) (map[t.status] ??= []).push(t)
  return map
})
const selectedIds = ref<Set<string>>(new Set())
const toggleSelected = (id: string) => {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}
const archiveOne = async (taskId: string) => {
  const task = store.tasks.find((t: TaskEntity) => t.id === taskId)
  try {
    await store.updateTask(taskId, { isArchived: true })
    notify.success(`«${task?.title ?? ''}» بایگانی شد`)
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'بایگانی انجام نشد'))
  }
}
const bulkDone = async () => {
  for (const id of selectedIds.value) await markDone(id)
  selectedIds.value = new Set()
}
const bulkArchive = async () => {
  for (const id of selectedIds.value) await archiveOne(id)
  selectedIds.value = new Set()
}

const csvInput = ref<HTMLInputElement | null>(null)
/** minimal CSV reader (quotes, commas inside quotes, CRLF) */
function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]!
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++ }
      else if (ch === '"') quoted = false
      else cell += ch
    }
    else if (ch === '"') quoted = true
    else if (ch === ',') { row.push(cell); cell = '' }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++
      row.push(cell); cell = ''
      if (row.some(c => c.trim())) rows.push(row)
      row = []
    }
    else cell += ch
  }
  row.push(cell)
  if (row.some(c => c.trim())) rows.push(row)
  return rows
}
const PRIORITY_FROM_FA: Record<string, string> = { 'کم': 'low', 'متوسط': 'medium', 'زیاد': 'high', 'فوری': 'urgent', 'low': 'low', 'medium': 'medium', 'high': 'high', 'urgent': 'urgent' }
async function onCsvPicked(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !props.projectId) return
  const rows = parseCsv((await file.text()).replace(/^\ufeff/, ''))
  const [head, ...body] = rows
  if (!head || !body.length) {
    notify.error('فایل CSV خالی است', 'ستون‌ها: عنوان، توضیحات، اولویت، موعد')
    return
  }
  const col = (names: string[]) => head.findIndex(h => names.includes(h.trim().toLowerCase()))
  const iTitle = col(['عنوان', 'title'])
  const iDesc = col(['توضیحات', 'description'])
  const iPri = col(['اولویت', 'priority'])
  const iDue = col(['موعد', 'due', 'due_date'])
  if (iTitle < 0) {
    notify.error('ستون «عنوان» در فایل پیدا نشد')
    return
  }
  let created = 0
  let failed = 0
  for (const r of body) {
    const title = (r[iTitle] ?? '').trim()
    if (!title) continue
    let due = (iDue >= 0 ? r[iDue] ?? '' : '').trim()
    if (/^1[34]\d{2}[/-]\d{1,2}[/-]\d{1,2}$/.test(due)) {
      const [jy, jm, jd] = due.split(/[/-]/).map(Number) as [number, number, number]
      due = jalaliToIso(jy, jm, jd)
    }
    try {
      await store.createTask({
        title,
        description: iDesc >= 0 ? (r[iDesc] ?? '').trim() : '',
        priority: (PRIORITY_FROM_FA[(iPri >= 0 ? r[iPri] ?? '' : '').trim().toLowerCase()] ?? 'medium') as TaskPriority,
        dueDate: /^\d{4}-\d{2}-\d{2}$/.test(due) ? due : '',
        assigneeId: store.meId,
        assigneeIds: [store.meId],
        projectId: props.projectId,
      } as never)
      created++
    }
    catch {
      failed++
    }
  }
  if (created) notify.success(`${created} امور محوله وارد شد`, failed ? `${failed} ردیف وارد نشد` : undefined)
  else notify.error('هیچ ردیفی وارد نشد')
}

const advanceTask = async (taskId: string) => {
  const task = store.tasks.find((item: TaskEntity) => item.id === taskId)
  if (!task) {
    return
  }

  // Assignees can only request completion approval.
  if (store.isAssignee(task)) {
    await requestApproval(task)
    return
  }

  const statusSequence: TaskStatus[] = ['todo', 'in-progress', 'review', 'done']
  const currentIndex = statusSequence.indexOf(task.status)
  const nextStatus: TaskStatus = statusSequence[Math.min(currentIndex + 1, statusSequence.length - 1)] ?? 'done'
  try {
    await store.updateTaskStatus(taskId, nextStatus)
    notify.success(`«${task.title}» به «${columnLabel(String(nextStatus))}» منتقل شد`)
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'به‌روزرسانی امور محوله انجام نشد'))
  }
}

const markDone = async (taskId: string) => {
  const task = store.tasks.find((item: TaskEntity) => item.id === taskId)
  if (!task) {
    return
  }

  // Assignees cannot complete a task directly: "Done" becomes a completion request.
  if (store.isAssignee(task)) {
    await requestApproval(task)
    return
  }

  try {
    await store.updateTaskStatus(taskId, 'done')
    notify.success(`«${task.title}» انجام‌شده ثبت شد`)
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'به‌روزرسانی امور محوله انجام نشد'))
  }
}

const submitTask = async () => {
  if (!form.title.trim()) {
    notify.error('لطفاً عنوان امور محوله را وارد کنید')
    return
  }
  if (!form.projectId) {
    notify.error('لطفاً کارتابل واحد را انتخاب کنید')
    return
  }

  try {
    await store.createTask({
      title: form.title.trim(),
      projectId: form.projectId,
      assigneeId: form.assigneeIds[0] || '',
      assigneeIds: [...form.assigneeIds],
      priority: form.priority,
      status: form.status,
      dueDate: form.dueDate || defaultDue(),
      dueTime: form.dueTime,
      recurrence: form.recurrence,
      description: form.description.trim(),
    })
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'ایجاد امور محوله انجام نشد'))
    return
  }

  notify.success(`امور محوله «${form.title.trim()}» ایجاد شد`)
  dialogOpen.value = false
  Object.assign(form, {
    title: '',
    projectId: defaultProjectId(),
    assigneeIds: [store.meId],
    priority: 'medium',
    status: 'todo',
    dueDate: defaultDue(),
    dueTime: '',
    recurrence: null,
    description: '',
  })
}

const submitProject = async () => {
  if (!projectForm.name.trim()) {
    notify.error('لطفاً نام کارتابل واحد را وارد کنید')
    return
  }

  try {
    await store.createProject({ name: projectForm.name.trim() })
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'ایجاد کارتابل واحد انجام نشد'))
    return
  }

  notify.success(`کارتابل واحد «${projectForm.name.trim()}» ایجاد شد`)
  projectDialogOpen.value = false
  Object.assign(projectForm, {
    name: '',
    code: '',
    description: '',
    accent: 'blue',
  })
}

const publishTask = async (taskId: string) => {
  const task = store.tasks.find((item: TaskEntity) => item.id === taskId)
  if (!task) {
    return
  }

  try {
    await store.publishTask(taskId)
    notify.success(`«${task.title}» منتشر شد`)
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'انتشار امور محوله انجام نشد'))
  }
}

const restoreTask = async (taskId: string) => {
  const task = store.tasks.find((item: TaskEntity) => item.id === taskId)
  if (!task) {
    return
  }

  try {
    await store.restoreTask(taskId)
    notify.success(`«${task.title}» بازیابی شد`)
  }
  catch (err) {
    notify.error(taskErrorMessage(err, 'بازیابی امور محوله انجام نشد'))
  }
}

const exportReport = () => {
  const priorityFa: Record<string, string> = { low: 'کم', medium: 'متوسط', high: 'زیاد', urgent: 'فوری' }
  const cell = (v: string) => `"${String(v).replace(/"/g, '""')}"`
  const rows = store.tasks.map((task: TaskEntity) => [
    task.title, getAssigneeNames(task), columnLabel(task.status), priorityFa[task.priority] ?? task.priority, fmtDue(task),
  ].map(cell).join(','))
  const csv = [['عنوان', 'مسئولان', 'وضعیت', 'اولویت', 'موعد'].map(cell).join(','), ...rows].join('\r\n')
  // the BOM makes Excel read the file as UTF-8, so Persian text is not garbled
  const blob = new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'employee-task-report.csv'
  link.click()
  URL.revokeObjectURL(url)
  notify.success('گزارش امور محوله دریافت شد')
}

const calendarWeekdays = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
const visibleWeekdays = computed(() => (showWeekends.value ? calendarWeekdays : calendarWeekdays.slice(0, 6)))

// The calendar works on Jalali months. `calendarMonth` = the month on screen.
const nowJ = isoToJalali(todayIso())!
const calendarMonth = ref({ jy: nowJ.jy, jm: nowJ.jm })
const calendarMonthLabel = computed(() => jalaliMonthTitle(calendarMonth.value.jy, calendarMonth.value.jm))

const calendarDays = computed(() => {
  const { jy, jm } = calendarMonth.value
  const len = jalaliMonthLength(jy, jm)
  const first = jalaliWeekday(jy, jm, 1) // 0 = Saturday
  const today = todayIso()
  const days: { date: string, dayNumber: string, isCurrentMonth: boolean, isToday: boolean, tasks: TaskEntity[], upcoming: TaskEntity[] }[] = []
  const rows = Math.ceil((first + len) / 7)
  // Future repeats of recurring tasks: the server only creates a copy when its day arrives, so every
  // later occurrence is projected here for the whole visible range (any month, any distance ahead).
  const gStart = toGregorian(jy, jm, 1)
  const rangeFrom = new Date(Date.UTC(gStart.gy, gStart.gm - 1, gStart.gd - first)).toISOString().slice(0, 10)
  const rangeTo = new Date(Date.UTC(gStart.gy, gStart.gm - 1, gStart.gd - first + rows * 7 - 1)).toISOString().slice(0, 10)
  const upcomingByDate = new Map<string, TaskEntity[]>()
  for (const t of sectionTasks.value as TaskEntity[]) {
    if (!t.recurrence || t.recurrenceSourceId || t.isDraft || t.isArchived || !t.dueDate) continue
    for (const d of projectOccurrences(t, rangeFrom, rangeTo)) {
      if (!upcomingByDate.has(d)) upcomingByDate.set(d, [])
      upcomingByDate.get(d)!.push(t)
    }
  }
  for (let index = 0; index < rows * 7; index += 1) {
    const offset = index - first + 1 // day-of-month, may fall outside this month
    const weekday = index % 7
    if (!showWeekends.value && weekday === 6) continue
    // normalise via a Date so days of the neighbouring months get correct labels
    const g = toGregorian(jy, jm, 1)
    const base = new Date(Date.UTC(g.gy, g.gm - 1, g.gd + offset - 1))
    const iso = base.toISOString().slice(0, 10)
    const j = isoToJalali(iso)!
    days.push({
      date: iso,
      dayNumber: toPersianDigits(j.jd),
      isCurrentMonth: j.jy === jy && j.jm === jm,
      isToday: iso === today,
      tasks: sectionTasks.value.filter((task: TaskEntity) => task.dueDate === iso),
      upcoming: upcomingByDate.get(iso) ?? [],
    })
  }
  return days
})

const changeCalendarMonth = (amount: number) => {
  const total = calendarMonth.value.jy * 12 + (calendarMonth.value.jm - 1) + amount
  calendarMonth.value = { jy: Math.floor(total / 12), jm: (total % 12 + 12) % 12 + 1 }
}

const goToToday = () => {
  const j = isoToJalali(todayIso())!
  calendarMonth.value = { jy: j.jy, jm: j.jm }
}

usePageSeoMeta({ title: 'مدیریت امور محوله' })
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
