<template>
  <ContainerWrapper
    dir="rtl"
    class="space-y-5 py-5 md:py-8"
  >
    <div
      v-if="task && project"
      class="space-y-5"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <NuxtLink
            to="/tasks/project"
            class="hover:text-foreground"
          >
            کارتابل واحد
          </NuxtLink>
          <Icon
            name="lucide:chevron-left"
            class="size-4"
          />
          <NuxtLink
            :to="`/tasks/project/${project.id}`"
            class="hover:text-foreground"
          >
            {{ project.name }}
          </NuxtLink>
          <Icon
            name="lucide:chevron-left"
            class="size-4"
          />
          <span class="text-foreground">جزئیات امور محوله</span>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            class="gap-2"
            @click="navigateTo(`/tasks/project/${project.id}`)"
          >
            <Icon
              name="lucide:arrow-right"
              class="size-4"
            />
            بازگشت به کارتابل واحد
          </Button>
          <Button
            v-if="canDelete"
            variant="outline"
            class="gap-2 text-destructive"
            @click="deleteTask"
          >
            <Icon
              name="lucide:trash-2"
              class="size-4"
            />
            حذف امور محوله
          </Button>
          <Button
            v-if="isAssignee"
            class="gap-2"
            :disabled="task.status === 'review' || task.status === 'done' || requesting"
            @click="requestCompletion"
          >
            <Icon
              name="lucide:send"
              class="size-4"
            />
            {{ task.status === 'review' ? 'در انتظار تأیید تکمیل' : 'درخواست تأیید تکمیل' }}
          </Button>
          <Button
            v-else
            class="gap-2"
            @click="saveTask"
          >
            <Icon
              name="lucide:save"
              class="size-4"
            />
            ذخیره تغییرات
          </Button>
        </div>
      </div>

      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">
              {{ project.code }}-{{ toPersianDigits(task.id) }}
            </Badge>
            <span>ایجاد: {{ formatTehranDateTime(task.createdAt) }} (وقت تهران)</span>
            <Badge
              v-if="task.recurrenceSourceId"
              variant="outline"
              class="gap-1"
            >
              <Icon
                name="lucide:repeat"
                class="size-3"
              /> نمونه‌ای از یک وظیفه‌ی تکرارشونده
            </Badge>
          </div>
          <h1 class="text-2xl font-semibold tracking-tight md:text-3xl">
            {{ form.title || 'امور محوله بدون عنوان' }}
          </h1>
          <p class="mt-1 text-sm text-muted-foreground">
            جزئیات را کامل کنید تا تیم همه‌چیز را برای انجام این کار در اختیار داشته باشد.
          </p>
        </div>
        <TaskStatusBadge :status="form.status" />
      </div>

      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div class="space-y-5">
          <!-- ── Brief ── -->
          <Card class="p-5 shadow-none">
            <div class="mb-5 flex items-center gap-3">
              <span class="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon
                name="lucide:clipboard-pen-line"
                class="size-5"
              /></span>
              <div>
                <h2 class="font-semibold">
                  شرح امور محوله
                </h2>
                <p class="text-sm text-muted-foreground">
                  نتیجه‌ی مورد انتظار و زمینه‌ی کار را روشن بنویسید.
                </p>
              </div>
            </div>
            <div class="space-y-4">
              <label class="block space-y-2 text-sm">
                <span class="font-medium">عنوان امور محوله</span>
                <Input
                  v-model="form.title"
                  dir="rtl"
                  class="h-11 text-right placeholder:text-right"
                  placeholder="چه کاری باید انجام شود؟"
                  :disabled="!canRename"
                />
                <span
                  v-if="!canRename"
                  class="block text-xs text-muted-foreground"
                >تغییر عنوان فقط توسط مدیر امکان‌پذیر است.</span>
              </label>
              <label class="block space-y-2 text-sm">
                <span class="font-medium">توضیحات</span>
                <Textarea
                  v-model="form.description"
                  dir="rtl"
                  class="min-h-36 resize-y text-right placeholder:text-right"
                  placeholder="نتیجه‌ی مورد انتظار، زمینه و معیارهای پذیرش را شرح دهید."
                  :disabled="restricted"
                />
              </label>
              <div class="grid gap-4 md:grid-cols-2">
                <div class="block space-y-2 text-sm">
                  <span class="font-medium">موعد انجام (تاریخ شمسی)</span>
                  <JalaliDateInput
                    v-model="form.dueDate"
                    :disabled="restricted"
                  />
                </div>
                <label class="block space-y-2 text-sm">
                  <span class="font-medium">ساعت موعد (به وقت تهران)</span>
                  <Input
                    v-model="form.dueTime"
                    type="time"
                    dir="ltr"
                    class="text-right"
                    :disabled="restricted"
                  />
                </label>
              </div>
            </div>
          </Card>

          <!-- ── Recurrence ── -->
          <Card class="p-5 shadow-none">
            <div class="mb-4 flex items-center gap-3">
              <span class="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon
                name="lucide:repeat"
                class="size-5"
              /></span>
              <div>
                <h2 class="font-semibold">
                  تکرار امور محوله
                </h2>
                <p class="text-sm text-muted-foreground">
                  روزانه، هفتگی، ماهانه، سالانه یا یک بازه‌ی دلخواه (ماه و سال بر اساس تقویم شمسی).
                </p>
              </div>
            </div>
            <TasksRecurrenceField
              v-model="form.recurrence"
              :disabled="restricted || !!task.recurrenceSourceId"
            />
            <p
              v-if="task.recurrence?.next_date"
              class="mt-3 text-xs text-muted-foreground"
            >
              امور محوله بعدی در تاریخ {{ formatJalali(task.recurrence.next_date) }} ساخته می‌شود.
            </p>
            <p
              v-if="task.recurrenceSourceId"
              class="mt-3 text-xs text-muted-foreground"
            >
              این امور محوله خودکار از روی یک وظیفه‌ی تکرارشونده ساخته شده است؛ تنظیم تکرار در امور محوله اصلی انجام می‌شود.
            </p>
          </Card>

          <!-- ── Checklist ── -->
          <Card class="p-5 shadow-none">
            <div class="mb-5 flex items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon
                  name="lucide:list-checks"
                  class="size-5"
                /></span>
                <div>
                  <h2 class="font-semibold">
                    چک‌لیست
                  </h2>
                  <p class="text-sm text-muted-foreground">
                    کار را به گام‌های مشخص تقسیم کنید.
                  </p>
                </div>
              </div>
              <span class="text-xs text-muted-foreground">{{ toPersianDigits(completedChecklist) }} از {{ toPersianDigits(checklist.length) }} انجام شد</span>
            </div>
            <div class="space-y-2">
              <p
                v-if="extrasLoading"
                class="py-2 text-sm text-muted-foreground"
              >
                در حال بارگذاری چک‌لیست…
              </p>
              <p
                v-else-if="!checklist.length"
                class="py-2 text-sm text-muted-foreground"
              >
                هنوز موردی در چک‌لیست نیست.
              </p>
              <label
                v-for="item in checklist"
                :key="item.id"
                class="flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm hover:bg-muted/30"
              >
                <input
                  type="checkbox"
                  class="size-4 accent-primary"
                  :checked="item.is_done"
                  :disabled="!canTick || busyItemId === item.id"
                  @change="toggleChecklistItem(item)"
                >
                <span
                  dir="auto"
                  :class="item.is_done ? 'text-muted-foreground line-through' : 'text-foreground'"
                >{{ item.title }}</span>
                <!-- deleting a checklist item is a manager-only action -->
                <button
                  v-if="canManage"
                  type="button"
                  class="mr-auto text-muted-foreground hover:text-destructive"
                  :aria-label="`حذف «${item.title}»`"
                  @click.prevent="removeChecklistItem(item)"
                >
                  <Icon
                    name="lucide:x"
                    class="size-4"
                  />
                </button>
              </label>
              <div
                v-if="canAddItems"
                class="flex gap-2 pt-2"
              >
                <Input
                  v-model="newChecklistItem"
                  dir="rtl"
                  class="text-right placeholder:text-right"
                  placeholder="افزودن مورد به چک‌لیست"
                  @keyup.enter="addChecklistItem"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label="افزودن به چک‌لیست"
                  :disabled="!newChecklistItem.trim()"
                  @click="addChecklistItem"
                >
                  <Icon
                    name="lucide:plus"
                    class="size-4"
                  />
                </Button>
              </div>
            </div>
          </Card>

          <!-- ── Files ── -->
          <Card class="p-5 shadow-none">
            <div class="mb-4 flex items-center gap-3">
              <span class="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon
                name="lucide:paperclip"
                class="size-5"
              /></span>
              <div>
                <h2 class="font-semibold">
                  فایل‌های پیوست
                </h2>
                <p class="text-sm text-muted-foreground">
                  هر تعداد فایل (حداکثر {{ toPersianDigits(MAX_UPLOAD_MB) }} مگابایت برای هر فایل) پیوست کنید.
                </p>
              </div>
            </div>
            <div class="space-y-3">
              <SupplierFileDropzone
                v-if="canAttach"
                label="فایل‌ها را بکشید و رها کنید یا برای انتخاب کلیک کنید"
                :accept="TASK_FILE_ACCEPT"
                multiple
                :loading="filesUploading"
                @files="uploadFiles"
              />
              <p
                v-if="extrasLoading"
                class="text-sm text-muted-foreground"
              >
                در حال بارگذاری فایل‌ها…
              </p>
              <p
                v-else-if="!files.length"
                class="text-sm text-muted-foreground"
              >
                هنوز فایلی پیوست نشده است.
              </p>
              <ul
                v-else
                class="space-y-2"
              >
                <li
                  v-for="f in files"
                  :key="f.id"
                  class="flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5 text-sm"
                >
                  <Icon
                    name="lucide:file"
                    class="size-4 shrink-0 text-muted-foreground"
                  />
                  <button
                    type="button"
                    class="min-w-0 flex-1 truncate text-right font-medium hover:underline"
                    dir="auto"
                    @click="downloadFile(f)"
                  >
                    {{ f.name }}
                  </button>
                  <span class="text-xs text-muted-foreground">
                    {{ fileSize(f.size) }} · {{ f.uploaded_by_name || '—' }} · {{ formatTehranDateTime(f.created_at) }}
                  </span>
                  <button
                    v-if="canManage || f.uploaded_by_user_id === Number(store.meId)"
                    type="button"
                    class="text-muted-foreground hover:text-destructive"
                    aria-label="حذف فایل"
                    @click="removeFile(f)"
                  >
                    <Icon
                      name="lucide:trash-2"
                      class="size-4"
                    />
                  </button>
                </li>
              </ul>
            </div>
          </Card>

          <!-- ── Messages ── -->
          <Card class="p-5 shadow-none">
            <div class="mb-4 flex items-center gap-3">
              <span class="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon
                name="lucide:message-square-text"
                class="size-5"
              /></span>
              <div>
                <h2 class="font-semibold">
                  پیام‌های داخلی
                </h2>
                <p class="text-sm text-muted-foreground">
                  گفتگو درباره‌ی امور محوله را همین‌جا نگه دارید. با نوشتن «@» می‌توانید همکاران را منشن کنید.
                </p>
              </div>
            </div>
            <div class="space-y-3">
              <div class="relative">
                <Textarea
                  ref="noteBox"
                  v-model="newNote"
                  dir="rtl"
                  class="min-h-24 resize-y text-right placeholder:text-right"
                  placeholder="برای تیم پیام بنویسید... (برای منشن، @ را تایپ کنید)"
                  @input="onNoteInput"
                  @keydown.esc="mention.open = false"
                />
                <ul
                  v-if="mention.open && mentionMatches.length"
                  class="absolute z-20 mt-1 max-h-48 w-64 overflow-y-auto rounded-lg border bg-popover p-1 text-sm shadow-md"
                >
                  <li
                    v-for="c in mentionMatches"
                    :key="c.id"
                  >
                    <button
                      type="button"
                      class="w-full rounded-md px-3 py-1.5 text-right hover:bg-muted"
                      dir="auto"
                      @mousedown.prevent="pickMention(c)"
                    >
                      {{ c.full_name }}
                    </button>
                  </li>
                </ul>
              </div>
              <div class="flex justify-end">
                <Button
                  type="button"
                  size="sm"
                  class="gap-2"
                  :disabled="!newNote.trim() || notesSaving"
                  @click="addNote"
                >
                  <Icon
                    name="lucide:send"
                    class="size-3.5"
                  />
                  ارسال پیام
                </Button>
              </div>
              <p
                v-if="extrasLoading"
                class="text-sm text-muted-foreground"
              >
                در حال بارگذاری پیام‌ها…
              </p>
              <p
                v-else-if="!notes.length"
                class="text-sm text-muted-foreground"
              >
                هنوز پیامی ثبت نشده است.
              </p>
              <ul
                v-else
                class="space-y-2"
              >
                <li
                  v-for="note in notes"
                  :key="note.id"
                  class="rounded-lg border px-3 py-2.5 text-sm"
                  :class="mentionsMe(note) ? 'border-primary/40 bg-primary/5' : 'bg-muted/20'"
                >
                  <div class="mb-1 flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span><span class="font-medium text-foreground">{{ note.author_name }}</span> · {{ formatTehranDateTime(note.created_at) }}</span>
                    <!-- deleting a message is a manager-only action -->
                    <button
                      v-if="canManage"
                      type="button"
                      class="hover:text-destructive"
                      aria-label="حذف پیام"
                      @click="removeNote(note)"
                    >
                      <Icon
                        name="lucide:trash-2"
                        class="size-3.5"
                      />
                    </button>
                  </div>
                  <p
                    class="whitespace-pre-wrap"
                    dir="auto"
                  >
                    <template
                      v-for="(part, i) in noteParts(note)"
                      :key="i"
                    >
                      <span
                        v-if="part.mention"
                        class="rounded bg-primary/10 px-1 font-medium text-primary"
                      >@{{ part.text }}</span>
                      <template v-else>{{ part.text }}</template>
                    </template>
                  </p>
                </li>
              </ul>
            </div>
          </Card>
        </div>

        <aside class="space-y-5">
          <Card class="p-5 shadow-none">
            <h2 class="mb-4 font-semibold">
              مشخصات امور محوله
            </h2>
            <div class="space-y-4">
              <label class="block space-y-2 text-sm"><span class="text-muted-foreground">وضعیت</span>
                <select
                  v-model="form.status"
                  class="field-select"
                >
                  <option
                    v-if="!isAssignee || form.status === 'todo'"
                    value="todo"
                  >در انتظار انجام</option>
                  <option
                    v-if="!isAssignee || form.status === 'in-progress'"
                    value="in-progress"
                  >در حال انجام</option>
                  <option value="review">درخواست تأیید تکمیل</option>
                  <option
                    v-if="!isAssignee || form.status === 'done'"
                    value="done"
                  >انجام‌شده</option>
                </select>
              </label>
              <label class="block space-y-2 text-sm"><span class="text-muted-foreground">اولویت</span>
                <select
                  v-model="form.priority"
                  class="field-select"
                  :disabled="restricted"
                >
                  <option value="low">کم</option>
                  <option value="medium">متوسط</option>
                  <option value="high">زیاد</option>
                  <option value="urgent">فوری</option>
                </select>
              </label>
              <div class="block space-y-2 text-sm">
                <span class="text-muted-foreground">مسئولان (می‌توانید چند نفر انتخاب کنید)</span>
                <TasksAssigneePicker
                  v-model="form.assigneeIds"
                  :users="assignableUsers"
                  :me-id="store.meId"
                  :disabled="!canAssign"
                />
              </div>
            </div>
          </Card>

          <!-- ── Referral ── -->
          <Card
            v-if="isAssignedToMe"
            class="p-5 shadow-none"
          >
            <h2 class="mb-1 font-semibold">
              ارجاع به دیگری
            </h2>
            <p class="mb-3 text-xs text-muted-foreground">
              این امور محوله به شما واگذار شده است؛ می‌توانید آن را به همکار دیگری ارجاع دهید. او هم می‌تواند آن را دوباره ارجاع دهد.
            </p>
            <div class="space-y-3">
              <select
                v-model="referTo"
                class="field-select"
              >
                <option value="">
                  انتخاب همکار...
                </option>
                <option
                  v-for="u in referCandidates"
                  :key="u.id"
                  :value="u.id"
                >
                  {{ u.name }}
                </option>
              </select>
              <Textarea
                v-model="referNote"
                dir="rtl"
                rows="2"
                class="text-right placeholder:text-right"
                placeholder="توضیح ارجاع (اختیاری)"
              />
              <Button
                type="button"
                class="w-full gap-2"
                :disabled="!referTo || referring"
                @click="referTask"
              >
                <Icon
                  name="lucide:corner-up-left"
                  class="size-4"
                />
                {{ referring ? 'در حال ارجاع...' : 'ارجاع بده' }}
              </Button>
            </div>
          </Card>

          <!-- ── Referral chain / assignment history ── -->
          <Card class="p-5 shadow-none">
            <h2 class="mb-3 font-semibold">
              زنجیره‌ی ارجاع
            </h2>
            <p
              v-if="extrasLoading"
              class="text-sm text-muted-foreground"
            >
              در حال بارگذاری…
            </p>
            <p
              v-else-if="!assignments.length"
              class="text-sm text-muted-foreground"
            >
              هنوز به کسی واگذار نشده است.
            </p>
            <ol
              v-else
              class="space-y-3"
            >
              <li
                v-for="a in assignments"
                :key="a.id"
                class="relative border-r-2 pr-3 text-sm"
                :class="a.is_active ? 'border-primary' : 'border-border'"
                :style="{ marginRight: `${depthOf(a) * 0.75}rem` }"
              >
                <p
                  class="font-medium"
                  dir="auto"
                >
                  {{ a.assignee_name }}
                  <Badge
                    v-if="a.is_active"
                    variant="secondary"
                    class="mr-1"
                  >
                    مسئول فعلی
                  </Badge>
                  <Badge
                    v-else-if="a.end_reason === 'REFERRED'"
                    variant="outline"
                    class="mr-1"
                  >
                    ارجاع داد
                  </Badge>
                  <Badge
                    v-else
                    variant="outline"
                    class="mr-1"
                  >
                    حذف شد
                  </Badge>
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ a.parent_assignment_id ? 'ارجاع از' : 'واگذار شده توسط' }} {{ a.assigned_by_name }} · {{ formatTehranDateTime(a.assigned_at) }}
                </p>
                <p
                  v-if="a.referral_note"
                  class="mt-1 text-xs"
                  dir="auto"
                >
                  «{{ a.referral_note }}»
                </p>
              </li>
            </ol>
          </Card>

          <Card class="p-5 shadow-none">
            <h2 class="mb-4 font-semibold">
              سازمان
            </h2>
            <div class="space-y-3 text-sm">
              <div class="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2.5">
                <span class="text-muted-foreground">کارتابل واحد</span><span class="font-medium">{{ project.name }}</span>
              </div>
              <div class="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2.5">
                <span class="text-muted-foreground">ایجادکننده</span><span class="font-medium">{{ store.getUserById(task.creatorId)?.name }}</span>
              </div>
            </div>
          </Card>
        </aside>
      </div>
    </div>

    <Card
      v-else
      class="p-8 text-center shadow-none"
    >
      <p class="text-sm text-muted-foreground">
        این امور محوله پیدا نشد یا به واحد شما مربوط نیست.
      </p>
      <Button
        class="mt-4"
        @click="navigateTo('/tasks/project')"
      >
        بازگشت به کارتابل واحد
      </Button>
    </Card>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import TaskStatusBadge from '~/components/tasks/TaskStatusBadge.vue'
import { ApiError, apiFetch, apiFetchBlob } from '~/services/backendApi'
import { MAX_UPLOAD_MB, checkUploadFile } from '~/utils/supplier-form'
import { useTaskWorkspaceStore, type RecurrenceRule, type TaskPriority, type TaskStatus } from '~/stores/taskWorkspace'

const notify = useNotify()
const route = useRoute()
const store = useTaskWorkspaceStore()
onMounted(() => store.ensureLoaded())
usePageSeoMeta({ title: 'جزئیات امور محوله' })

const projectId = computed(() => String(route.params.projectId))
const taskId = computed(() => String(route.params.taskId))
const project = computed(() => store.getProjectById(projectId.value))
const task = computed(() => store.tasks.find(item => item.id === taskId.value && item.projectId === projectId.value))

const TASK_FILE_ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt,.png,.jpg,.jpeg,.webp,.gif,.zip,.rar,.7z'

interface ChecklistItem { id: number, title: string, is_done: boolean, position: number }
interface MentionRef { id: number, full_name: string }
interface TaskNote { id: number, author_id: number | null, author_name: string, body: string, mentions: MentionRef[], created_at: string | null }
interface TaskFileRow { id: string, name: string, size: number, uploaded_by_user_id: number | null, uploaded_by_name: string | null, created_at: string | null }
interface AssignmentRow {
  id: number, assignee_user_id: number, assignee_name: string, assigned_by_name: string, parent_assignment_id: number | null,
  is_active: boolean, end_reason: string | null, referral_note: string | null, assigned_at: string | null
}

const form = reactive({
  title: '', description: '', dueDate: '', dueTime: '', assigneeIds: [] as string[],
  priority: 'medium' as TaskPriority, status: 'todo' as TaskStatus, recurrence: null as RecurrenceRule | null,
})

// ── who may do what (the server enforces all of it; this only decides what to show) ──
const isAssignee = computed(() => !!task.value && store.isAssignee(task.value))
const isAssignedToMe = computed(() => !!task.value && store.isAssignedToMe(task.value) && task.value.status !== 'done')
/** assignees (who are not admins) may only ask for completion approval */
const restricted = computed(() => isAssignee.value)
const canManage = computed(() => !!task.value && store.canManageTask(task.value)) // «مدیر»
const canRename = computed(() => canManage.value)
const canDelete = computed(() => canManage.value && store.permissions.delete)
const canAssign = computed(() => !restricted.value && (store.permissions.assign || store.isAdmin))
const canTick = computed(() => !!task.value && (store.isAssignedToMe(task.value) || canManage.value))
const canAddItems = computed(() => canTick.value)
const canAttach = computed(() => !!task.value && (store.isAssignedToMe(task.value) || store.canEditTask(task.value)))

const assignableUsers = computed(() => store.usersForAssign(projectId.value).map(u => ({ id: u.id, name: u.name })))

watch(task, (value) => {
  if (!value) return
  Object.assign(form, {
    title: value.title, description: value.description, dueDate: value.dueDate, dueTime: value.dueTime,
    assigneeIds: [...value.assigneeIds], priority: value.priority, status: value.status,
    recurrence: value.recurrence ? { ...value.recurrence } : null,
  })
}, { immediate: true })

// ── checklist / notes / files / referral chain ──
const checklist = ref<ChecklistItem[]>([])
const notes = ref<TaskNote[]>([])
const files = ref<TaskFileRow[]>([])
const assignments = ref<AssignmentRow[]>([])
const newChecklistItem = ref('')
const newNote = ref('')
const notesSaving = ref(false)
const filesUploading = ref(false)
const extrasLoading = ref(false)
const busyItemId = ref<number | null>(null)
const completedChecklist = computed(() => checklist.value.filter(item => item.is_done).length)

const errMsg = (err: unknown, fallback: string) => taskErrorMessage(err, fallback)

async function loadExtras(id: string | undefined) {
  checklist.value = []
  notes.value = []
  files.value = []
  assignments.value = []
  if (!id) return
  extrasLoading.value = true
  try {
    const [items, noteList, fileList, history] = await Promise.all([
      apiFetch<ChecklistItem[]>(`/tasks/${id}/checklist`),
      apiFetch<TaskNote[]>(`/tasks/${id}/notes`),
      apiFetch<TaskFileRow[]>(`/tasks/${id}/files`),
      apiFetch<AssignmentRow[]>(`/tasks/${id}/assignments`),
    ])
    checklist.value = items
    notes.value = noteList
    files.value = fileList
    assignments.value = history
  }
  catch (err) {
    notify.error(errMsg(err, 'بارگذاری چک‌لیست، پیام‌ها و فایل‌ها انجام نشد'))
  }
  finally {
    extrasLoading.value = false
  }
}
watch(() => task.value?.id, id => loadExtras(id), { immediate: true })

const addChecklistItem = async () => {
  const title = newChecklistItem.value.trim()
  if (!title || !task.value) return
  try {
    checklist.value.push(await apiFetch<ChecklistItem>(`/tasks/${task.value.id}/checklist`, { method: 'POST', body: { title } }))
    newChecklistItem.value = ''
  }
  catch (err) {
    notify.error(errMsg(err, 'افزودن به چک‌لیست انجام نشد'))
  }
}
const toggleChecklistItem = async (item: ChecklistItem) => {
  if (!task.value) return
  busyItemId.value = item.id
  try {
    Object.assign(item, await apiFetch<ChecklistItem>(`/tasks/${task.value.id}/checklist/${item.id}`, { method: 'PATCH', body: { is_done: !item.is_done } }))
  }
  catch (err) {
    notify.error(errMsg(err, 'به‌روزرسانی چک‌لیست انجام نشد'))
  }
  finally {
    busyItemId.value = null
  }
}
const removeChecklistItem = async (item: ChecklistItem) => {
  if (!task.value) return
  try {
    await apiFetch(`/tasks/${task.value.id}/checklist/${item.id}`, { method: 'DELETE' })
    checklist.value = checklist.value.filter(i => i.id !== item.id)
  }
  catch (err) {
    notify.error(errMsg(err, 'حذف از چک‌لیست انجام نشد'))
  }
}

// ── files ──
const fileSize = (bytes: number) => bytes >= 1048576
  ? `${toPersianDigits((bytes / 1048576).toFixed(1))} مگابایت`
  : `${toPersianDigits(Math.max(1, Math.round(bytes / 1024)))} کیلوبایت`

async function uploadFiles(picked: File[]) {
  if (!task.value || !picked.length) return
  for (const f of picked) {
    const problem = checkUploadFile(f, TASK_FILE_ACCEPT)
    if (problem) return notify.error(problem)
  }
  filesUploading.value = true
  try {
    const fd = new FormData()
    picked.forEach(f => fd.append('files', f)) // any number of files in one request
    const saved = await apiFetch<TaskFileRow[]>(`/tasks/${task.value.id}/files`, { method: 'POST', body: fd })
    files.value.push(...saved)
    notify.success(`${toPersianDigits(saved.length)} فایل پیوست شد`)
  }
  catch (err) {
    notify.error(errMsg(err, 'بارگذاری فایل انجام نشد'))
  }
  finally {
    filesUploading.value = false
  }
}
async function downloadFile(f: TaskFileRow) {
  if (!task.value) return
  try {
    const blob = await apiFetchBlob(`/tasks/${task.value.id}/files/${f.id}`)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = f.name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }
  catch (err) {
    notify.error(errMsg(err, 'دریافت فایل انجام نشد'))
  }
}
async function removeFile(f: TaskFileRow) {
  if (!task.value || !window.confirm(`فایل «${f.name}» حذف شود؟`)) return
  try {
    await apiFetch(`/tasks/${task.value.id}/files/${f.id}`, { method: 'DELETE' })
    files.value = files.value.filter(x => x.id !== f.id)
  }
  catch (err) {
    notify.error(errMsg(err, 'حذف فایل انجام نشد'))
  }
}

// ── messages with @mentions ──
// The textarea shows readable "@Name". On send, every picked "@Name" becomes the token
// "@[id]", which the server resolves (and validates) -- the client cannot fake a mention.
const noteBox = ref<any>(null)
const candidates = ref<MentionRef[]>([])
const picked = reactive(new Map<string, number>())
const mention = reactive({ open: false, query: '', start: -1 })

async function ensureCandidates() {
  if (candidates.value.length || !task.value) return
  try {
    candidates.value = await apiFetch<MentionRef[]>(`/tasks/${task.value.id}/mention-candidates`)
  }
  catch {
    candidates.value = []
  }
}
const mentionMatches = computed(() => {
  const q = mention.query.trim().toLowerCase()
  return candidates.value.filter(c => !q || c.full_name.toLowerCase().includes(q)).slice(0, 8)
})
function onNoteInput(e: Event) {
  const el = e.target as HTMLTextAreaElement
  const caret = el.selectionStart ?? el.value.length
  const before = el.value.slice(0, caret)
  const at = before.lastIndexOf('@')
  const valid = at >= 0 && (at === 0 || /\s/.test(before[at - 1]!)) && !/\n/.test(before.slice(at)) && before.slice(at).length <= 40
  if (valid) {
    mention.start = at
    mention.query = before.slice(at + 1)
    mention.open = true
    ensureCandidates()
  }
  else {
    mention.open = false
  }
}
function pickMention(c: MentionRef) {
  const text = newNote.value
  const end = mention.start + 1 + mention.query.length
  newNote.value = `${text.slice(0, mention.start)}@${c.full_name} ${text.slice(end)}`
  picked.set(c.full_name, c.id)
  mention.open = false
}
const tokenize = (body: string) => {
  let out = body
  for (const [name, id] of [...picked.entries()].sort((a, b) => b[0].length - a[0].length)) {
    out = out.split(`@${name}`).join(`@[${id}]`)
  }
  return out
}
const noteParts = (note: TaskNote) => {
  const names = new Map(note.mentions.map(m => [m.id, m.full_name]))
  return note.body.split(/(@\[\d+\])/g).filter(Boolean).map((chunk) => {
    const m = /^@\[(\d+)\]$/.exec(chunk)
    return m ? { mention: true, text: names.get(Number(m[1])) ?? 'کاربر حذف‌شده' } : { mention: false, text: chunk }
  })
}
const mentionsMe = (note: TaskNote) => note.mentions.some(m => String(m.id) === store.meId)

const addNote = async () => {
  const body = tokenize(newNote.value.trim())
  if (!body || !task.value) return
  notesSaving.value = true
  try {
    const note = await apiFetch<TaskNote>(`/tasks/${task.value.id}/notes`, { method: 'POST', body: { body } })
    notes.value.unshift(note)
    newNote.value = ''
    picked.clear()
    mention.open = false
  }
  catch (err) {
    notify.error(errMsg(err, 'ارسال پیام انجام نشد'))
  }
  finally {
    notesSaving.value = false
  }
}
const removeNote = async (note: TaskNote) => {
  if (!task.value || !window.confirm('این پیام حذف شود؟')) return
  try {
    await apiFetch(`/tasks/${task.value.id}/notes/${note.id}`, { method: 'DELETE' })
    notes.value = notes.value.filter(n => n.id !== note.id)
  }
  catch (err) {
    notify.error(errMsg(err, 'حذف پیام انجام نشد'))
  }
}

// ── referral (hierarchical chain) ──
const referTo = ref('')
const referNote = ref('')
const referring = ref(false)
const referCandidates = computed(() =>
  store.usersForProject(projectId.value).filter(u => u.id !== store.meId && !(task.value?.assigneeIds ?? []).includes(u.id)))
const depthOf = (a: AssignmentRow) => {
  let depth = 0
  let cur: AssignmentRow | undefined = a
  const byId = new Map(assignments.value.map(x => [x.id, x]))
  while (cur?.parent_assignment_id && depth < 12) {
    cur = byId.get(cur.parent_assignment_id)
    depth += 1
  }
  return depth
}
async function referTask() {
  if (!task.value || !referTo.value) return
  referring.value = true
  try {
    await store.referTask(task.value.id, referTo.value, referNote.value)
    notify.success('امور محوله ارجاع داده شد')
    referTo.value = ''
    referNote.value = ''
    assignments.value = await apiFetch<AssignmentRow[]>(`/tasks/${task.value.id}/assignments`)
  }
  catch (err) {
    notify.error(errMsg(err, 'ارجاع امور محوله انجام نشد'))
  }
  finally {
    referring.value = false
  }
}

// ── save / delete ──
/** send the repeat rule only when it was edited (saving re-anchors a series on the due date) */
const recurrenceChanged = computed(() => {
  if (!task.value || task.value.recurrenceSourceId) return false
  const key = (r: RecurrenceRule | null) => (r ? `${r.unit}|${r.interval}|${r.end_date ?? ''}` : '')
  return key(form.recurrence) !== key(task.value.recurrence)
})
const saveTask = async () => {
  if (!task.value || !form.title.trim()) {
    notify.error('لطفاً عنوان امور محوله را وارد کنید')
    return
  }
  try {
    // A restricted assignee may only request completion approval -- send just the status.
    const payload = isAssignee.value
      ? (form.status === 'review' && task.value.status !== 'review' ? { status: form.status } : {})
      : {
          ...(canRename.value && form.title.trim() !== task.value.title ? { title: form.title.trim() } : {}),
          description: form.description.trim(),
          dueDate: form.dueDate,
          dueTime: form.dueTime,
          priority: form.priority,
          status: form.status,
          ...(recurrenceChanged.value ? { recurrence: form.recurrence } : {}),
          ...(canAssign.value ? { assigneeIds: [...form.assigneeIds] } : {}),
        }
    if (!Object.keys(payload).length) {
      notify.info('تغییری برای ذخیره وجود ندارد')
      return
    }
    await store.updateTask(task.value.id, payload)
    assignments.value = await apiFetch<AssignmentRow[]>(`/tasks/${task.value.id}/assignments`)
    notify.success('جزئیات امور محوله ذخیره شد')
  }
  catch (err) {
    notify.error(errMsg(err, 'ذخیره‌ی امور محوله انجام نشد'))
  }
}

const requesting = ref(false)
/** The assignee's only status action: ask the manager to approve completion. */
const requestCompletion = async () => {
  if (!task.value || requesting.value) return
  if (task.value.status === 'review') {
    notify.info('درخواست تأیید تکمیل قبلاً ثبت شده و در انتظار تأیید است')
    return
  }
  requesting.value = true
  try {
    await store.updateTask(task.value.id, { status: 'review' })
    form.status = 'review'
    notify.success('درخواست تأیید تکمیل ثبت شد')
  }
  catch (err) {
    notify.error(errMsg(err, 'ثبت درخواست تأیید تکمیل انجام نشد'))
  }
  finally {
    requesting.value = false
  }
}

const deleteTask = async () => {
  if (!task.value || !window.confirm(`امور محوله «${task.value.title}» حذف شود؟ این کار قابل بازگشت نیست.`)) return
  try {
    await store.removeTask(task.value.id)
    notify.success('امور محوله حذف شد')
    navigateTo(`/tasks/project/${projectId.value}`)
  }
  catch (err) {
    notify.error(errMsg(err, 'حذف امور محوله انجام نشد'))
  }
}
</script>

<style scoped>
.field-select {
  display: flex;
  height: 2.5rem;
  width: 100%;
  border: 1px solid hsl(var(--input));
  border-radius: 0.375rem;
  background: hsl(var(--background));
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}
</style>
