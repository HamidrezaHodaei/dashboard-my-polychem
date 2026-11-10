// Per-user preferences of the department worklists (کارتابل واحدها): which departments are starred
// (favourites / pinned) and an optional logo picture per department. Stored in the browser, keyed by
// the signed-in user, so each person keeps their own pins.
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
  const logoKey = computed(() => `tasks:project-logos:${uid.value}`)

  const favorites = useState<string[]>('project-favorites', () => [])
  const logos = useState<Record<string, string>>('project-logos', () => ({}))

  onMounted(() => {
    favorites.value = read<string[]>(favKey.value, [])
    logos.value = read<Record<string, string>>(logoKey.value, {})
  })

  const isFavorite = (id: string) => favorites.value.includes(id)
  function toggleFavorite(id: string) {
    favorites.value = isFavorite(id) ? favorites.value.filter(x => x !== id) : [...favorites.value, id]
    write(favKey.value, favorites.value)
  }

  /** Resizes the picked image to <= 160px and keeps it as a small data URL. */
  async function setLogo(id: string, file: File) {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, 160 / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    logos.value = { ...logos.value, [id]: canvas.toDataURL('image/png') }
    write(logoKey.value, logos.value)
  }
  function removeLogo(id: string) {
    const { [id]: _drop, ...rest } = logos.value
    logos.value = rest
    write(logoKey.value, logos.value)
  }

  return { favorites, logos, isFavorite, toggleFavorite, setLogo, removeLogo }
}
