// Per-user preferences of the department worklists (کارتابل واحدها): which departments are starred
// (favourites / pinned). Stored in the browser, keyed by the signed-in user, so each person keeps
// their own pins. (The unit pictures are NOT a preference: see useDepartmentPictures.)
const read = <T>(key: string, fallback: T): T => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) as T : fallback
  }
  catch { return fallback }
}
const write = (key: string, value: unknown) => {
  try { localStorage.setItem(key, JSON.stringify(value)) }
  catch { /* private mode / quota: the preference just won't persist */ }
}

export function useProjectPrefs() {
  const auth = useAuthStore()
  const uid = computed(() => auth.user?.id ?? 'anon')
  const favKey = computed(() => `tasks:fav-projects:${uid.value}`)

  const favorites = useState<string[]>('project-favorites', () => [])

  onMounted(() => {
    favorites.value = read<string[]>(favKey.value, [])
  })

  const isFavorite = (id: string) => favorites.value.includes(id)
  function toggleFavorite(id: string) {
    favorites.value = isFavorite(id) ? favorites.value.filter(x => x !== id) : [...favorites.value, id]
    write(favKey.value, favorites.value)
  }

  return { favorites, isFavorite, toggleFavorite }
}
