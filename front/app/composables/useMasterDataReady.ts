// Ensures master data (warehouses, items, categories, etc.) is loaded once
// before a page renders lookups that depend on it.
export async function useMasterDataReady() {
  const store = useMasterDataStore()
  if (!store.loaded) await store.loadAll()
  return store
}
