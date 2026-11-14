import type { NuxtLinkProps } from '#app'
import type { BadgeVariants } from '@/components/ui/badge'

export interface SidebarProps {
  nav: SidebarNavGroup[]
  secondaryNav?: SidebarNavGroup[]
  color?: 'background' | 'accent' | 'dark'
  variant?: 'sidebar' | 'floating' | 'inset'
  side?: 'left' | 'right'
}

export interface SidebarNavGroup {
  heading?: string
  items: (SidebarItem | SidebarItemGroup)[]
}

export interface SidebarItemGroup {
  title: string
  children: SidebarItem[]
  activeRoute?: string | string[]
  icon?: string
  /** Shown only to admins -- for sections no permission can be granted for (no backend module yet). */
  adminOnly?: boolean
}

export interface SidebarItem {
  title: string
  link: NuxtLinkProps
  activeRoute?: string | string[]
  icon?: string
  /** Hidden unless the user's /api/me/navigation contains this key (any one of them, when an array). */
  navKey?: string | string[]
  /** Shown only to admins. */
  adminOnly?: boolean
  badge?: {
    label: string
    variant?: BadgeVariants['variant']
  }
}
