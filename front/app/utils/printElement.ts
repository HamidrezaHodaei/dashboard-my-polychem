// Prints ONE element of the page (a chart card, a report) -- the browser's print dialog also offers
// «Save as PDF», so the same call serves "Print" and "Export PDF". The rest of the page is hidden by
// the `printing-one` rules in assets/css/main.css only while the dialog is open.
export function printElement(el: HTMLElement | null | undefined, title?: string) {
  if (!el || typeof window === 'undefined') return
  const previousTitle = document.title
  el.classList.add('print-target')
  document.body.classList.add('printing-one')
  if (title) document.title = title // becomes the default PDF file name
  const cleanup = () => {
    el.classList.remove('print-target')
    document.body.classList.remove('printing-one')
    document.title = previousTitle
    window.removeEventListener('afterprint', cleanup)
  }
  window.addEventListener('afterprint', cleanup)
  // let the class change paint before the dialog opens
  requestAnimationFrame(() => setTimeout(() => window.print(), 50))
}
