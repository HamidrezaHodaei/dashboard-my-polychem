// Frontend mirror of the backend permission checks (services.py `_require`). The backend is the
// authority; this only hides controls the user could not use anyway. Keys are the SAME
// `crm.<resource>.<action>` keys the role/permission matrix manages -- no CRM-specific rights.
export function useCrmAccess() {
  const auth = useAuthStore()
  const can = (key: string) => computed(() => auth.permissionKeys.has(key))
  return {
    canReadSales: can('crm.sale.read'),
    canCreateSale: can('crm.sale.create'),
    canUpdateSale: can('crm.sale.update'),
    canDeleteSale: can('crm.sale.delete'),
    // Excel / Word download and printing of the sales report are separate, non-CRUD permissions.
    canExportSale: can('crm.sale.export'),
    canPrintSale: can('crm.sale.print'),
    canReadCatalog: can('crm.product.read'),
    canCreateCatalog: can('crm.product.create'),
    canUpdateCatalog: can('crm.product.update'),
    canDeleteCatalog: can('crm.product.delete'),
    canReadCustomers: can('crm.customer.read'),
  }
}
