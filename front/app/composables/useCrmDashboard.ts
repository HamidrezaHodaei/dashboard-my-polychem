export interface CrmSale {
  id: number | string
  customer: string
  product: string
  amount: number
  tons: number
  dateLabel: string
  status: string
  isReturn?: boolean
  saleType?: string
  payment?: string
}

export interface CrmCustomer {
  id: number | string
  name: string
  phone?: string
  province?: string
  industry?: string
  status?: string
}

export interface CrmLookup {
  id: number | string
  name: string
  code?: string
  category?: string
}

export interface CrmStats {
  totalAmount: number
  totalTons: number
  customerCount: number
  invoiceCount: number
  returnCount: number
}

export function useCrmDashboard() {
  const config = useRuntimeConfig()
  const apiBase = (config.public.crmApiBaseUrl as string | undefined) || 'http://127.0.0.1:5050'
  const sales = ref<CrmSale[]>([])
  const customers = ref<CrmCustomer[]>([])
  const products = ref<CrmLookup[]>([])
  const provinces = ref<CrmLookup[]>([])
  const industries = ref<CrmLookup[]>([])
  const paymentMethods = ref<CrmLookup[]>([])
  const loading = ref(false)
  const error = ref('')

  const stats = computed<CrmStats>(() => ({
    totalAmount: sales.value.reduce((sum, sale) => sum + (sale.isReturn ? -sale.amount : sale.amount), 0),
    totalTons: sales.value.reduce((sum, sale) => sum + (sale.isReturn ? -sale.tons : sale.tons), 0),
    customerCount: new Set(sales.value.map(sale => sale.customer)).size,
    invoiceCount: sales.value.length,
    returnCount: sales.value.filter(sale => sale.isReturn).length,
  }))

  async function request<T>(path: string) {
    return await $fetch<{ data?: T }>(`${apiBase}${path}`, { credentials: 'include' })
  }

  async function saveLookup(endpoint: string, payload: Partial<CrmLookup>, id?: number | string) {
    return await $fetch(`${apiBase}/api/${endpoint}${id ? `/${id}` : ''}`, { method: id ? 'PUT' : 'POST', body: payload, credentials: 'include' })
  }

  async function deleteLookup(endpoint: string, id: number | string) {
    return await $fetch(`${apiBase}/api/${endpoint}/${id}`, { method: 'DELETE', credentials: 'include' })
  }

  async function load() {
    loading.value = true
    error.value = ''
    try {
      const [salesResponse, customerResponse, productsResponse, provincesResponse, industriesResponse, paymentsResponse] = await Promise.all([
        request<CrmSale[]>('/api/sales?perPage=200'),
        request<CrmCustomer[]>('/api/customers?perPage=200'),
        request<CrmLookup[]>('/api/products'),
        request<CrmLookup[]>('/api/provinces'),
        request<CrmLookup[]>('/api/industries'),
        request<CrmLookup[]>('/api/payment-methods'),
      ])
      sales.value = salesResponse.data || []
      customers.value = customerResponse.data || []
      products.value = productsResponse.data || []
      provinces.value = provincesResponse.data || []
      industries.value = industriesResponse.data || []
      paymentMethods.value = paymentsResponse.data || []
    }
    catch {
      error.value = 'CRM data could not be loaded. Check the API connection.'
    }
    finally {
      loading.value = false
    }
  }

  return { apiBase, sales, customers, products, provinces, industries, paymentMethods, stats, loading, error, load, saveLookup, deleteLookup }
}
