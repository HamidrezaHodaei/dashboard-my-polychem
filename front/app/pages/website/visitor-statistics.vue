<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8" dir="ltr">
    <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        <div class="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <NuxtLink to="/" class="hover:text-foreground">Dashboard</NuxtLink>
          <Icon name="lucide:chevron-left" class="size-3" />
          <span>Website Management</span>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight md:text-3xl">Visitor Statistics</h1>
        <p class="mt-1 text-sm text-muted-foreground">Monitor website visitor activity and traffic paths</p>
      </div>
      <Button variant="outline" class="gap-2" :disabled="loading" @click="refresh">
        <Icon name="lucide:refresh-cw" class="size-4" :class="loading && 'animate-spin'" />
        Refresh
      </Button>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card v-for="stat in statCards" :key="stat.label" class="gap-2 p-5 shadow-none">
        <div class="flex items-center justify-between text-sm text-muted-foreground">
          <span>{{ stat.label }}</span>
          <Icon :name="stat.icon" class="size-4 text-primary" />
        </div>
        <p class="text-2xl font-semibold">{{ stats[stat.key] }}</p>
      </Card>
    </div>

    <Card class="gap-4 p-4 shadow-none md:p-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div class="relative min-w-0 flex-1">
          <Icon name="lucide:search" class="absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <Input v-model="filters.search" class="pl-9" placeholder="Search by IP or path..." @input="debouncedSearch" />
        </div>
        <select v-model="filters.country" class="h-9 rounded-md border bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/50" @change="applyFilters">
          <option value="">All countries</option>
          <option v-for="country in countryList" :key="country" :value="country">{{ country }}</option>
        </select>
        <select v-model="filters.days" class="h-9 rounded-md border bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/50" @change="applyFilters">
          <option value="1">Last 24 hours</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="">All time</option>
        </select>
        <Button variant="ghost" class="shrink-0 gap-2" @click="resetFilters">
          <Icon name="lucide:rotate-ccw" class="size-4" />
          Reset
        </Button>
      </div>
    </Card>

    <Card class="overflow-hidden py-0 shadow-none">
      <div v-if="loading" class="flex min-h-64 flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
        <Icon name="lucide:loader-circle" class="size-7 animate-spin text-primary" />
        <span>Loading visitors...</span>
      </div>
      <div v-else-if="error" class="flex min-h-64 flex-col items-center justify-center gap-3 text-center">
        <Icon name="lucide:circle-alert" class="size-8 text-destructive" />
        <p class="font-medium">Unable to load visitor data</p>
        <p class="text-sm text-muted-foreground">Check the API connection and try again.</p>
        <Button variant="outline" size="sm" @click="refresh">Try again</Button>
      </div>
      <div v-else-if="visitors.length === 0" class="flex min-h-64 flex-col items-center justify-center gap-2 text-center">
        <Icon name="lucide:search-x" class="size-8 text-muted-foreground" />
        <p class="font-medium">No visitors found</p>
        <p class="text-sm text-muted-foreground">Try changing your filters or search term.</p>
      </div>
      <div v-else class="overflow-x-auto">
        <Table>
          <TableHeader><TableRow><TableHead>Device</TableHead><TableHead>Location & IP</TableHead><TableHead>OS & browser</TableHead><TableHead>Visited path</TableHead><TableHead>Last visit</TableHead></TableRow></TableHeader>
          <TableBody><TableRow v-for="visitor in visitors" :key="visitor.id">
            <TableCell><Icon :name="deviceIcon(visitor.user_agent)" class="size-5 text-muted-foreground" /></TableCell>
            <TableCell><p class="font-medium">{{ visitor.country || 'Unknown' }}</p><p class="text-xs text-muted-foreground">{{ visitor.ip_address }}</p></TableCell>
            <TableCell><p class="font-medium">{{ parseOS(visitor.user_agent) }}</p><p class="text-xs text-muted-foreground">{{ parseBrowser(visitor.user_agent) }}</p></TableCell>
            <TableCell><Badge variant="outline" dir="ltr">{{ visitor.path }}</Badge></TableCell>
            <TableCell><p class="font-medium">{{ formatRelative(visitor.visited_at) }}</p><p class="text-xs text-muted-foreground">{{ formatDate(visitor.visited_at) }}</p></TableCell>
          </TableRow></TableBody>
        </Table>
      </div>
      <div v-if="pagination.total > 0 && !loading" class="flex flex-col gap-3 border-t p-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <span>Page {{ currentPage }} of {{ totalPages }} · {{ pagination.total }} total visits</span>
        <div class="flex gap-2"><Button variant="outline" size="sm" :disabled="pagination.offset === 0" @click="previousPage">Previous</Button><Button variant="outline" size="sm" :disabled="!pagination.has_more" @click="nextPage">Next</Button></div>
      </div>
    </Card>
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()

interface VisitorLog { id: number | string; country?: string; ip_address: string; user_agent?: string; path: string; visited_at: string }
interface VisitorStats { today: number; week: number; uniqueIps: number; total: number }
interface VisitorPagination { total: number; limit: number; offset: number; has_more: boolean }
interface VisitorResponse { logs?: VisitorLog[]; pagination?: VisitorPagination; countries?: string[] }

const config = useRuntimeConfig()
const apiBaseUrl = (config.public.visitorApiBaseUrl as string | undefined) || 'https://polychemmb.com/api'
const loading = ref(false)
const error = ref(false)
const visitors = ref<VisitorLog[]>([])
const countryList = ref<string[]>([])
const stats = ref<VisitorStats>({ today: 0, week: 0, uniqueIps: 0, total: 0 })
const filters = reactive({ search: '', country: '', days: '7' })
const pagination = reactive<VisitorPagination>({ total: 0, limit: 20, offset: 0, has_more: false })
let searchTimeout: ReturnType<typeof setTimeout> | undefined

const statCards = [{ key: 'today', label: 'Today\'s visits', icon: 'lucide:calendar-days' }, { key: 'week', label: 'This week\'s visits', icon: 'lucide:bar-chart-3' }, { key: 'uniqueIps', label: 'Unique IPs', icon: 'lucide:fingerprint' }, { key: 'total', label: 'Total visits', icon: 'lucide:globe-2' }] as const
const currentPage = computed(() => Math.floor(pagination.offset / pagination.limit) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.total / pagination.limit)))

function getToken() { if (!import.meta.client) return null; return localStorage.getItem('admin_token') || localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('auth_token') }
async function apiCall<T>(endpoint: string) { const token = getToken(); if (!token) { notify.error('Please sign in first'); await navigateTo('/auth/signin'); return null } try { return await $fetch<T>(`${apiBaseUrl}${endpoint}`, { headers: { Authorization: `Bearer ${token}` } }) } catch { error.value = true; notify.error('Unable to connect to the server'); return null } }
async function loadStats() { const data = await apiCall<{ stats?: VisitorStats }>('/admin/logs/visitors/stats'); if (data?.stats) stats.value = data.stats }
async function loadVisitors() { loading.value = true; error.value = false; const params = new URLSearchParams({ limit: String(pagination.limit), offset: String(pagination.offset) }); if (filters.country) params.set('country', filters.country); if (filters.days) params.set('days', filters.days); if (filters.search) params.set('search', filters.search); const data = await apiCall<VisitorResponse>(`/admin/logs/visitors?${params.toString()}`); if (data) { visitors.value = data.logs || []; countryList.value = data.countries || countryList.value; Object.assign(pagination, data.pagination || {}) } loading.value = false }
async function refresh() { await Promise.all([loadStats(), loadVisitors()]) }
function applyFilters() { pagination.offset = 0; loadVisitors() }
function debouncedSearch() { if (searchTimeout) clearTimeout(searchTimeout); searchTimeout = setTimeout(applyFilters, 500) }
function resetFilters() { filters.search = ''; filters.country = ''; filters.days = '7'; applyFilters() }
function nextPage() { pagination.offset += pagination.limit; loadVisitors() }
function previousPage() { pagination.offset = Math.max(0, pagination.offset - pagination.limit); loadVisitors() }
function parseOS(ua = '') { if (/windows/i.test(ua)) return 'Windows'; if (/macintosh|mac os/i.test(ua)) return 'macOS'; if (/android/i.test(ua)) return 'Android'; if (/iphone|ipad|ios/i.test(ua)) return 'iOS'; if (/linux/i.test(ua)) return 'Linux'; return 'Unknown' }
function parseBrowser(ua = '') { if (/edg/i.test(ua)) return 'Edge'; if (/chrome/i.test(ua)) return 'Chrome'; if (/firefox/i.test(ua)) return 'Firefox'; if (/safari/i.test(ua)) return 'Safari'; return 'Unknown' }
function deviceIcon(ua = '') { return /android|iphone|ipad/i.test(ua) ? 'lucide:smartphone' : 'lucide:monitor' }
function formatRelative(value: string) { const diff = Math.max(0, Date.now() - new Date(value).getTime()); const minutes = Math.floor(diff / 60000); if (minutes < 1) return 'Just now'; if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`; const hours = Math.floor(minutes / 60); if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`; const days = Math.floor(hours / 24); return `${days} day${days === 1 ? '' : 's'} ago` }
function formatDate(value: string) { if (!value) return '-'; return new Date(value).toLocaleString('en-US') }
onBeforeMount(refresh)
usePageSeoMeta({ title: 'Visitor Statistics' })
</script>
