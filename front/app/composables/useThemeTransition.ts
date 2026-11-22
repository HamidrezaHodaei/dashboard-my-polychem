/**
 * Circular-reveal animation (View Transitions API) shared by every appearance change
 * (light / dark / system and colour palette). Falls back to an instant change when the
 * API is missing or the user prefers reduced motion.
 */
export type ColorModePreference = 'system' | 'light' | 'dark'
export type TransitionOrigin = { clientX: number, clientY: number }

export function runThemeTransition(apply: () => void | Promise<void>, origin?: TransitionOrigin) {
  const doc = document as Document & { startViewTransition?: (cb: () => void | Promise<void>) => unknown }
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (!doc.startViewTransition || reduceMotion) {
    void apply()
    return
  }

  const root = document.documentElement
  root.style.setProperty('--x', `${origin?.clientX ?? window.innerWidth / 2}px`)
  root.style.setProperty('--y', `${origin?.clientY ?? window.innerHeight / 2}px`)
  doc.startViewTransition(apply)
}

/**
 * The one place that changes the colour mode. Persistence is done by @nuxtjs/color-mode
 * (localStorage), so the choice survives refresh and re-login.
 */
export function useThemeTransition() {
  const colorMode = useColorMode()

  const setColorMode = (value: ColorModePreference, origin?: TransitionOrigin) => {
    if (colorMode.preference === value) return
    runThemeTransition(async () => {
      colorMode.preference = value
      // color-mode toggles the `.dark` class in a watcher; the "new" snapshot must be taken after it ran.
      await nextTick()
    }, origin)
  }

  const toggleColorMode = (origin?: TransitionOrigin) =>
    setColorMode(colorMode.value === 'dark' ? 'light' : 'dark', origin)

  return { colorMode, setColorMode, toggleColorMode }
}
