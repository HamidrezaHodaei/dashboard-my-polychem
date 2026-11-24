import type { RouteLocationRaw } from 'vue-router'

/** One entry of a record's action menu (see components/RowActions.vue). */
export interface RowAction {
  key: string
  label: string
  /** Deprecated and ignored: action menus are text-only. Kept optional so existing call sites still type-check. */
  icon?: string
  /** Click handler. Ignored when `to` is set. */
  onSelect?: () => void
  /** Navigate instead of running a handler (rendered as a real link: middle-click / copy link work). */
  to?: RouteLocationRaw
  /** false hides the entry (permission / status rules). Default: true */
  show?: boolean
  disabled?: boolean
  /** Warning style (delete, remove...). Destructive items are always placed last, after a separator. */
  destructive?: boolean
  /** Entries with different groups are separated by a line. Default: 0 */
  group?: number
}
