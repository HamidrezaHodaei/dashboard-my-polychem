export type AccessStatus = 'active' | 'inactive'
export type PermissionAction = 'view' | 'create' | 'edit' | 'delete' | 'approve' | 'export' | 'publish'

export interface AccessUser {
  id: number
  name: string
  email: string
  phone: string
  role: string
  team: string
  organization: string
  lastLogin: string
  createdAt: string
  status: AccessStatus
  permissionsByModule: Record<string, PermissionAction[]>
}

export interface AccessRole {
  id: number
  name: string
  description: string
  users: number
  permissions: number
  status: AccessStatus
  createdAt: string
  updatedAt: string
  permissionsByModule: Record<string, PermissionAction[]>
}

export interface PermissionItem {
  key: string
  label: string
  action: PermissionAction
}

export interface PermissionModule {
  key: string
  label: string
  items: PermissionItem[]
}

export interface Organization {
  id: number
  name: string
  code: string
  manager: string
  teams: number
  users: number
  status: AccessStatus
}

export interface AccessTeam {
  id: number
  name: string
  manager: string
  members: number
  organization: string
  status: AccessStatus
  createdAt: string
}

const actions: PermissionAction[] = ['view', 'create', 'edit', 'delete', 'approve', 'export', 'publish']

export const permissionLabels: Record<PermissionAction, string> = {
  view: 'View',
  create: 'Create',
  edit: 'Edit',
  delete: 'Delete',
  approve: 'Approve',
  export: 'Export',
  publish: 'Publish',
}

export const permissionModules: PermissionModule[] = [
  ['users', 'Users', ['view', 'create', 'edit', 'delete', 'export']],
  ['roles', 'Roles', ['view', 'create', 'edit', 'delete']],
  ['finance', 'Finance', actions.slice(0, 6)],
  ['sales', 'Sales', actions.slice(0, 6)],
  ['warehouse', 'Warehouse', ['view', 'create', 'edit', 'delete', 'export']],
  ['production', 'Production', actions.slice(0, 6)],
  ['purchasing', 'Purchasing', actions.slice(0, 6)],
  ['website', 'Website', ['view', 'create', 'edit', 'delete', 'publish']],
  ['reports', 'Reports', ['view', 'export']],
  ['settings', 'Settings', ['view', 'create', 'edit', 'delete']],
].map(([key, label, moduleActions]) => ({
  key: key as string,
  label: label as string,
  items: (moduleActions as PermissionAction[]).map(action => ({ key: `${key}.${action}`, label: permissionLabels[action], action })),
}))

const fullAccess = Object.fromEntries(permissionModules.map(module => [module.key, module.items.map(item => item.action)]))
const scoped = (modules: Record<string, PermissionAction[]>) => Object.fromEntries(permissionModules.map(module => [module.key, modules[module.key] || []]))

const roleNames = ['admin', 'CEO', 'Finance Manager', 'Sales Manager', 'Finance Specialist', 'Sales Specialist', 'Plant Manager', 'Storekeeper', 'Warehouse Manager', 'Records Officer', 'Quality & Development Manager', 'Technical Control', 'Inventory Officer', 'Transport Officer', 'Website Manager', 'Procurement Manager']

const rolePermissionSets: Record<string, Record<string, PermissionAction[]>> = {
  'CEO': scoped({ finance: ['view', 'approve', 'export'], sales: ['view', 'approve', 'export'], warehouse: ['view', 'approve', 'export'], production: ['view', 'approve', 'export'], purchasing: ['view', 'approve', 'export'], reports: ['view', 'export'], users: ['view'] }),
  'Finance Manager': scoped({ finance: actions.slice(0, 6), reports: ['view', 'export'], users: ['view'] }),
  'Finance Specialist': scoped({ finance: ['view', 'create', 'edit'], reports: ['view', 'export'] }),
  'Sales Manager': scoped({ sales: actions.slice(0, 6), reports: ['view', 'export'] }),
  'Sales Specialist': scoped({ sales: ['view', 'create', 'edit'], reports: ['view'] }),
  'Storekeeper': scoped({ warehouse: ['view', 'create', 'edit'] }),
  'Warehouse Manager': scoped({ warehouse: actions.slice(0, 6) }),
  'Plant Manager': scoped({ production: actions.slice(0, 6), warehouse: ['view', 'create', 'edit'], reports: ['view', 'export'] }),
  'Website Manager': scoped({ website: ['view', 'create', 'edit', 'delete', 'publish'] }),
  'Procurement Manager': scoped({ purchasing: actions.slice(0, 6), reports: ['view', 'export'] }),
}

const makeRole = (name: string, id: number): AccessRole => {
  const permissionsByModule = rolePermissionSets[name] || fullAccess
  return { id, name, description: name === 'admin' ? 'Full access to every module' : `${name} organizational role`, users: id === 1 ? 1 : Math.max(2, 18 - id), permissions: Object.values(permissionsByModule).flat().length, status: 'active', createdAt: '2023/10/04', updatedAt: '2024/05/08', permissionsByModule }
}

export const accessUsers: AccessUser[] = [
  { id: 1, name: 'Mohammad Rezaei', email: 'm.rezaei@polychem.ir', phone: '+98 912 456 7890', role: 'admin', team: 'Executive', organization: 'Head Office', lastLogin: 'Today, 09:42', createdAt: '2023/10/04', status: 'active', permissionsByModule: fullAccess },
  { id: 2, name: 'Sara Ahmadi', email: 's.ahmadi@polychem.ir', phone: '+98 910 321 6547', role: 'Finance Manager', team: 'Finance', organization: 'Head Office', lastLogin: 'Today, 08:15', createdAt: '2023/10/27', status: 'active', permissionsByModule: rolePermissionSets['Finance Manager'] },
  { id: 3, name: 'Ali Karimi', email: 'a.karimi@polychem.ir', phone: '+98 911 123 4567', role: 'Sales Manager', team: 'Sales', organization: 'Head Office', lastLogin: 'Yesterday, 16:30', createdAt: '2023/11/12', status: 'active', permissionsByModule: rolePermissionSets['Sales Manager'] },
  { id: 4, name: 'Negar Mousavi', email: 'n.mousavi@polychem.ir', phone: '+98 935 789 1234', role: 'Finance Specialist', team: 'Finance', organization: 'Head Office', lastLogin: 'Yesterday, 14:02', createdAt: '2024/01/23', status: 'inactive', permissionsByModule: rolePermissionSets['Finance Specialist'] },
  { id: 5, name: 'Reza Akbari', email: 'r.akbari@polychem.ir', phone: '+98 913 567 8901', role: 'Plant Manager', team: 'Plant', organization: 'Alborz Plant', lastLogin: 'Saturday, 11:24', createdAt: '2024/04/03', status: 'active', permissionsByModule: rolePermissionSets['Plant Manager'] },
]

export const accessRoles = roleNames.map(makeRole)
export const accessOrganizations: Organization[] = [
  { id: 1, name: 'Head Office', code: 'HQ-01', manager: 'Mohammad Rezaei', teams: 5, users: 28, status: 'active' },
  { id: 2, name: 'Alborz Plant', code: 'PL-01', manager: 'Reza Akbari', teams: 3, users: 46, status: 'active' },
  { id: 3, name: 'East Warehouse', code: 'WH-02', manager: 'Mehdi Naderi', teams: 1, users: 12, status: 'inactive' },
]
export const accessTeams: AccessTeam[] = [
  { id: 1, name: 'Finance', manager: 'Sara Ahmadi', members: 8, organization: 'Head Office', status: 'active', createdAt: '2023/10/04' },
  { id: 2, name: 'Sales', manager: 'Ali Karimi', members: 12, organization: 'Head Office', status: 'active', createdAt: '2023/10/04' },
  { id: 3, name: 'Plant', manager: 'Reza Akbari', members: 24, organization: 'Alborz Plant', status: 'active', createdAt: '2023/10/23' },
  { id: 4, name: 'Quality Control', manager: 'Maryam Sadeghi', members: 7, organization: 'Alborz Plant', status: 'active', createdAt: '2023/10/23' },
  { id: 5, name: 'Procurement', manager: 'Hossein Moradi', members: 5, organization: 'Head Office', status: 'inactive', createdAt: '2024/03/28' },
]

export function useAccessManagement() {
  const statusLabel = (status: AccessStatus) => status === 'active' ? 'فعال' : 'غیرفعال'
  return { actions, permissionLabels, permissionModules, accessUsers, accessRoles, accessOrganizations, accessTeams, statusLabel }
}