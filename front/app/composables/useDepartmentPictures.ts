// Shared pictures of the department worklists (کارتابل واحدها): a round logo and a banner behind
// the card. They are stored on the SERVER -- only an admin can change them, and everybody who can
// open a unit's worklist sees the same ones (they used to be a per-browser localStorage preference).
//
// The picture endpoints need the Authorization header, so a plain <img src> would 401: the bytes
// are fetched as a Blob and shown through an object URL. They are cached by
// `<department>:<kind>:<version>`; the server bumps the version on every change, so a new picture
// shows up (after the next meta load) without ever serving a stale one.
import { ApiError, apiFetch, apiFetchBlob } from '~/services/backendApi'
import type { ProjectEntity } from '~/stores/taskWorkspace'

export type PictureKind = 'logo' | 'header'

interface BrandingResponse { has_logo: boolean, has_header: boolean, branding_version: number }

const MAX_EDGE: Record<PictureKind, number> = { logo: 256, header: 1280 }

/** Shrinks a picked image in the browser so an upload stays small (logo: PNG, banner: JPEG). */
async function shrink(file: File, kind: PictureKind): Promise<Blob> {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, MAX_EDGE[kind] / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(bitmap.width * scale))
  canvas.height = Math.max(1, Math.round(bitmap.height * scale))
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  const type = kind === 'logo' ? 'image/png' : 'image/jpeg'
  return await new Promise<Blob>((resolve, reject) =>
    canvas.toBlob(b => (b ? resolve(b) : reject(new Error('encode failed'))), type, 0.85))
}

export function useDepartmentPictures() {
  const store = useTaskWorkspaceStore()
  // key -> object URL ('' = the download failed; do not retry in a loop)
  const urls = useState<Record<string, string>>('department-picture-urls', () => ({}))
  const inflight = new Set<string>()

  const keyOf = (p: Pick<ProjectEntity, 'id' | 'brandingVersion'>, kind: PictureKind) => `${p.id}:${kind}:${p.brandingVersion}`

  async function ensure(p: ProjectEntity, kind: PictureKind) {
    const has = kind === 'logo' ? p.hasLogo : p.hasHeader
    const key = keyOf(p, kind)
    if (!has || key in urls.value || inflight.has(key)) return
    inflight.add(key)
    try {
      const blob = await apiFetchBlob(`/tasks/departments/${p.id}/branding/${kind}`)
      // forget older versions of the same picture
      for (const [k, u] of Object.entries(urls.value)) {
        if (k.startsWith(`${p.id}:${kind}:`) && u) URL.revokeObjectURL(u)
      }
      const fresh = Object.fromEntries(Object.entries(urls.value).filter(([k]) => !k.startsWith(`${p.id}:${kind}:`)))
      urls.value = { ...fresh, [key]: URL.createObjectURL(blob) }
    }
    catch {
      urls.value = { ...urls.value, [key]: '' }
    }
    finally {
      inflight.delete(key)
    }
  }

  // fetch whatever the unit list says exists, now and whenever a version changes
  if (import.meta.client) {
    watch(
      () => store.projects.map(p => `${p.id}:${p.hasLogo}:${p.hasHeader}:${p.brandingVersion}`).join('|'),
      () => { for (const p of store.projects) { void ensure(p, 'logo'); void ensure(p, 'header') } },
      { immediate: true },
    )
  }

  /** Object URL of a unit's picture, or '' when it has none (or it is still loading). */
  function pictureUrl(p: ProjectEntity | undefined, kind: PictureKind): string {
    if (!p) return ''
    return urls.value[keyOf(p, kind)] ?? ''
  }

  /** Admin only (the server enforces it too). */
  async function setPicture(projectId: string, kind: PictureKind, file: File) {
    const body = new FormData()
    body.append('file', await shrink(file, kind), kind === 'logo' ? 'logo.png' : 'header.jpg')
    const res = await apiFetch<BrandingResponse>(`/tasks/departments/${projectId}/branding/${kind}`, { method: 'PUT', body })
    store.applyProjectBranding(projectId, res)
  }

  async function removePicture(projectId: string, kind: PictureKind) {
    const res = await apiFetch<BrandingResponse>(`/tasks/departments/${projectId}/branding/${kind}`, { method: 'DELETE' })
    store.applyProjectBranding(projectId, res)
  }

  const errorMessage = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback)

  return { pictureUrl, setPicture, removePicture, errorMessage }
}
