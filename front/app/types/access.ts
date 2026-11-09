export interface MatrixModule { key: string, label: string, actions: string[] }
export type MatrixDraft = Record<string, Record<string, boolean>>
export interface MatrixCellMeta {
  // role mode
  granted?: boolean
  scoped?: boolean
  // user mode
  effective?: boolean
  from_role?: boolean
  role_names?: string[]
  direct?: 'ALLOW' | 'DENY' | null
}
export interface MatrixResponse {
  modules: MatrixModule[]
  cells: Record<string, Record<string, MatrixCellMeta>>
  precedence?: string[]
}
