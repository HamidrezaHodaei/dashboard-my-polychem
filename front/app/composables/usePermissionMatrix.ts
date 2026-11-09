import type { MatrixCellMeta, MatrixDraft, MatrixModule, MatrixResponse } from '~/types/access'
import { ApiError, apiFetch } from '~/services/backendApi'

/** Loads / edits / saves a role or user permission matrix.
 *  `basePath` is e.g. `/core/users/12` or `/core/roles/3`. */
export function usePermissionMatrix(basePath: string, mode: 'role' | 'user') {
  const modules = ref<MatrixModule[]>([])
  const meta = ref<Record<string, Record<string, MatrixCellMeta>>>({})
  const precedence = ref<string[]>([])
  const draft = ref<MatrixDraft>({})
  const original = ref<MatrixDraft>({})
  const loading = ref(false)
  const saving = ref(false)
  /** Last load error (shown by the page instead of failing silently). */
  const error = ref('')

  const cellValue = (c: MatrixCellMeta) => (mode === 'role' ? !!c.granted : !!c.effective)

  function apply(res: MatrixResponse) {
    modules.value = res.modules
    meta.value = res.cells
    precedence.value = res.precedence || []
    const next: MatrixDraft = {}
    for (const m of res.modules) {
      next[m.key] = {}
      for (const a of m.actions) next[m.key]![a] = cellValue(res.cells[m.key]?.[a] || {})
    }
    original.value = JSON.parse(JSON.stringify(next))
    draft.value = next
  }

  async function load() {
    loading.value = true
    error.value = ''
    try {
      apply(await apiFetch<MatrixResponse>(`${basePath}/permission-matrix`))
    }
    catch (err) {
      modules.value = []
      error.value = err instanceof ApiError ? err.message : 'Failed to load permissions.'
    }
    finally {
      loading.value = false
    }
  }

  /** Only the cells that differ from what was loaded. */
  const changedCells = computed(() => {
    const out: MatrixDraft = {}
    for (const [mk, actions] of Object.entries(draft.value)) {
      for (const [a, v] of Object.entries(actions)) {
        if (original.value[mk]?.[a] !== v) (out[mk] ||= {})[a] = v
      }
    }
    return out
  })
  const dirty = computed(() => Object.keys(changedCells.value).length > 0)
  const changedCount = computed(() => Object.values(changedCells.value).reduce((n, a) => n + Object.keys(a).length, 0))

  async function save() {
    saving.value = true
    try {
      apply(await apiFetch<MatrixResponse>(`${basePath}/permission-matrix`, {
        method: 'PUT',
        body: { cells: changedCells.value },
      }))
    }
    finally {
      saving.value = false
    }
  }

  function reset() {
    draft.value = JSON.parse(JSON.stringify(original.value))
  }

  return { modules, meta, precedence, draft, loading, saving, error, dirty, changedCount, load, save, reset }
}
