import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

/**
 * The one button system of the panel. Rules shared by every variant:
 *  - radius `rounded-md`, no shadows or gradients, 150 ms colour transitions only
 *  - states: hover (tone shift), active (one step deeper), focus-visible (2px brand ring), disabled (50% + not-allowed)
 *  - touch: on coarse pointers every size grows to the 44px minimum target (see `pointer-coarse:` below)
 *  - destructive keeps its own red identity in both themes so a delete never looks like a normal action
 */
export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors duration-150 select-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*=\'size-\'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80',
        destructive:
          'bg-destructive text-white hover:bg-destructive/90 active:bg-destructive/80 focus-visible:ring-destructive/40 dark:bg-destructive/70 dark:hover:bg-destructive/80 dark:active:bg-destructive/60',
        outline:
          'border border-input bg-background hover:bg-accent hover:text-accent-foreground active:bg-accent/70 dark:bg-transparent dark:hover:bg-accent',
        secondary:
          'bg-secondary text-secondary-foreground hover:bg-secondary/80 active:bg-secondary/60',
        ghost:
          'hover:bg-accent hover:text-accent-foreground active:bg-accent/70 data-[state=open]:bg-accent',
        link: 'text-primary-content underline-offset-4 hover:underline focus-visible:ring-offset-0',
      },
      size: {
        'default': 'h-9 px-4 py-2 has-[>svg]:px-3 pointer-coarse:h-11',
        'xs': 'h-6 gap-1 px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*=\'size-\'])]:size-3 pointer-coarse:h-8',
        'sm': 'h-8 gap-1.5 px-3 has-[>svg]:px-2.5 pointer-coarse:h-10',
        'lg': 'h-10 px-6 has-[>svg]:px-4 pointer-coarse:h-12',
        'icon': 'size-9 pointer-coarse:size-11',
        'icon-xs': 'size-6 [&_svg:not([class*=\'size-\'])]:size-3 pointer-coarse:size-8',
        'icon-sm': 'size-8 pointer-coarse:size-10',
        'icon-lg': 'size-10 pointer-coarse:size-12',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)
export type ButtonVariants = VariantProps<typeof buttonVariants>
