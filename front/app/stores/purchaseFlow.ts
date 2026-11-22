import { defineStore } from 'pinia'
import { apiDownload, apiFetch, apiFetchPage } from '~/services/backendApi'
import type { FlowMeta, FlowRequest } from '~/utils/purchaseFlow'

export interface FlowRow extends Omit<FlowRequest, 'items' | 'events'> {
  items: { id: number, name: string, status: string, status_label: string, priority: string | null, priority_label: string | null, supply_place_label: string | null, receipt_missing: boolean, has_payment: boolean, quantity: number, unit: string, overdue: boolean }[]
}
export interface FlowKpi {
  overall: Record<string, number | null>
  by_priority: ({ priority: string, label: string } & Record<string, number | string | null>)[]
  sla: { priority: string, label: string, amount: number, unit: string, unit_label: string }[]
  rows: Record<string, any>[]
  rows_total: number
}

const B = '/purchases/flow'

export const usePurchaseFlowStore = defineStore('purchaseFlow', () => {
  const meta = ref<FlowMeta | null>(null)
  async function loadMeta(force = false) {
    if (!meta.value || force) meta.value = await apiFetch<FlowMeta>(`${B}/meta`)
    return meta.value
  }
  const list = (query: Record<string, string | number | undefined>) => apiFetchPage<FlowRow>(`${B}/requests`, query)
  const fetchOne = (id: number) => apiFetch<FlowRequest>(`${B}/requests/${id}`)
  const create = (body: Record<string, unknown>) => apiFetch<FlowRequest>(`${B}/requests`, { method: 'POST', body })
  const update = (id: number, body: Record<string, unknown>) => apiFetch<FlowRequest>(`${B}/requests/${id}`, { method: 'PUT', body })
  const post = (id: number, path: string, body: Record<string, unknown> = {}) => apiFetch<FlowRequest>(`${B}/requests/${id}/${path}`, { method: 'POST', body })
  const setStatus = (id: number, status: string, note?: string) => post(id, 'status', { status, note: note || null })
  const setSupplyPlace = (id: number, item: number, supply_place: string) =>
    apiFetch<FlowRequest>(`${B}/requests/${id}/items/${item}/supply-place`, { method: 'PUT', body: { supply_place } })
  const saveQuote = (id: number, item: number, body: Record<string, unknown>, quoteId?: number) =>
    apiFetch<FlowRequest>(`${B}/requests/${id}/items/${item}/quotes${quoteId ? `/${quoteId}` : ''}`, { method: quoteId ? 'PUT' : 'POST', body })
  const deleteQuote = (id: number, item: number, quoteId: number) =>
    apiFetch<FlowRequest>(`${B}/requests/${id}/items/${item}/quotes/${quoteId}`, { method: 'DELETE' })
  const submitToManager = (id: number, item_ids: number[]) => post(id, 'submit-to-manager', { item_ids })
  const decide = (id: number, item: number, body: Record<string, unknown>) => post(id, `items/${item}/decision`, body)
  const pay = (id: number, item: number, body: Record<string, unknown>) => post(id, `items/${item}/payment`, body)
  const financeReturn = (id: number, item_ids?: number[]) => post(id, 'finance-return', item_ids ? { item_ids } : {})
  const itemStatus = (id: number, item: number, body: Record<string, unknown>) => post(id, `items/${item}/status`, body)
  const receipt = (id: number, item: number, file_id: string) => post(id, `items/${item}/receipt`, { file_id })

  const kpi = (query: Record<string, string | undefined>) => apiFetch<FlowKpi>(`${B}/kpi`, { query })
  const exportKpi = (query: Record<string, string | undefined>) =>
    apiDownload(`${B}/kpi/export`, query, `purchase-timing-${new Date().toISOString().slice(0, 10)}.xlsx`)

  const options = (kind?: string) => apiFetch<{ id: number, kind: string, label: string, sort_order: number, is_active: boolean, used_count: number }[]>(`${B}/options`, { query: { kind } })
  const saveOption = (body: Record<string, unknown>, id?: number) => apiFetch(`${B}/options${id ? `/${id}` : ''}`, { method: id ? 'PATCH' : 'POST', body })
  const deleteOption = (id: number) => apiFetch(`${B}/options/${id}`, { method: 'DELETE' })
  const saveSla = (rows: { priority: string, amount: number, unit: string }[]) => apiFetch(`${B}/sla`, { method: 'PUT', body: { rows } })

  return { meta, loadMeta, list, fetchOne, create, update, setStatus, setSupplyPlace, saveQuote, deleteQuote, submitToManager, decide, pay, financeReturn, itemStatus, receipt, kpi, exportKpi, options, saveOption, deleteOption, saveSla }
})
