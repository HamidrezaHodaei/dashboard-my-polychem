<template>
  <ContainerWrapper
    class="space-y-5 py-6 text-right md:py-8"
    dir="rtl"
  >
    <div>
      <h1 class="text-lg font-semibold text-ink text-right">تنظیمات</h1>
      <p class="text-sm text-ink-faint text-right">اطلاعات پایه مورد استفاده در سامانه انبارداری.</p>
    </div>

    <WmsUiTabs v-model="activeTab" :tabs="tabs" />

    <!-- Warehouses -->
    <WmsUiCard v-if="activeTab === 'warehouses'" :padded="false">
      <div class="flex items-center justify-between border-b border-line p-4">
        <p class="text-sm text-ink-faint">{{ masterData.warehouses.length }} انبار</p>
        <WmsUiButton size="sm" variant="primary" @click="warehouseModal = { open: true, item: null }">افزودن انبار</WmsUiButton>
      </div>
      <WmsUiTable :columns="warehouseColumns" :rows="masterData.warehouses" row-key="id">
        <template #cell-code="{ row }"><span class="data-code">{{ row.code }}</span></template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="row.status === 'active' ? 'success' : 'neutral'">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }"><WmsUiButton size="sm" variant="ghost" @click="warehouseModal = { open: true, item: row }">ویرایش</WmsUiButton></template>
      </WmsUiTable>
    </WmsUiCard>

    <!-- Storage Locations -->
    <WmsUiCard v-else-if="activeTab === 'locations'" :padded="false">
      <div class="flex items-center justify-between border-b border-line p-4">
        <p class="text-sm text-ink-faint">{{ masterData.locations.length }} محل نگهداری</p>
        <WmsUiButton size="sm" variant="primary" @click="locationModal = { open: true, item: null }">افزودن محل</WmsUiButton>
      </div>
      <WmsUiTable :columns="locationColumns" :rows="masterData.locations" row-key="id">
        <template #cell-code="{ row }"><span class="data-code">{{ row.code }}</span></template>
        <template #cell-warehouseId="{ row }">{{ masterData.warehouseName(row.warehouseId) }}</template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="row.status === 'active' ? 'success' : 'neutral'">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }"><WmsUiButton size="sm" variant="ghost" @click="locationModal = { open: true, item: row }">ویرایش</WmsUiButton></template>
      </WmsUiTable>
    </WmsUiCard>

    <!-- Items -->
    <WmsUiCard v-else-if="activeTab === 'items'" :padded="false">
      <div class="flex items-center justify-between border-b border-line p-4">
        <p class="text-sm text-ink-faint">{{ masterData.items.length }} کالا</p>
        <WmsUiButton size="sm" variant="primary" @click="itemModal = { open: true, item: null }">افزودن کالا</WmsUiButton>
      </div>
      <WmsUiTable :columns="itemColumns" :rows="masterData.items" row-key="id">
        <template #cell-code="{ row }"><span class="data-code">{{ row.code }}</span></template>
        <template #cell-categoryId="{ row }">{{ masterData.categoryName(row.categoryId) }}</template>
        <template #cell-unitId="{ row }">{{ masterData.units.find(u => u.id === row.unitId)?.code }}</template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="row.status === 'active' ? 'success' : 'neutral'">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }"><WmsUiButton size="sm" variant="ghost" @click="itemModal = { open: true, item: row }">ویرایش</WmsUiButton></template>
      </WmsUiTable>
    </WmsUiCard>

    <!-- Categories -->
    <WmsUiCard v-else-if="activeTab === 'categories'" :padded="false">
      <div class="flex items-center justify-between border-b border-line p-4">
        <p class="text-sm text-ink-faint">{{ masterData.categories.length }} دسته‌بندی</p>
        <WmsUiButton size="sm" variant="primary" @click="categoryModal = { open: true, item: null }">افزودن دسته‌بندی</WmsUiButton>
      </div>
      <WmsUiTable :columns="categoryColumns" :rows="masterData.categories" row-key="id">
        <template #cell-status="{ row }"><WmsUiBadge :tone="row.status === 'active' ? 'success' : 'neutral'">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }"><WmsUiButton size="sm" variant="ghost" @click="categoryModal = { open: true, item: row }">ویرایش</WmsUiButton></template>
      </WmsUiTable>
    </WmsUiCard>

    <!-- Units -->
    <WmsUiCard v-else-if="activeTab === 'units'" :padded="false">
      <div class="flex items-center justify-between border-b border-line p-4">
        <p class="text-sm text-ink-faint">{{ masterData.units.length }} واحد</p>
        <WmsUiButton size="sm" variant="primary" @click="unitModal = { open: true, item: null }">افزودن واحد</WmsUiButton>
      </div>
      <WmsUiTable :columns="unitColumns" :rows="masterData.units" row-key="id">
        <template #cell-code="{ row }"><span class="data-code">{{ row.code }}</span></template>
        <template #actions="{ row }"><WmsUiButton size="sm" variant="ghost" @click="unitModal = { open: true, item: row }">ویرایش</WmsUiButton></template>
      </WmsUiTable>
    </WmsUiCard>

    <!-- Suppliers -->
    <WmsUiCard v-else-if="activeTab === 'suppliers'" :padded="false">
      <div class="flex items-center justify-between border-b border-line p-4">
        <p class="text-sm text-ink-faint">{{ masterData.suppliers.length }} تأمین‌کننده</p>
        <WmsUiButton size="sm" variant="primary" @click="supplierModal = { open: true, item: null }">افزودن تأمین‌کننده</WmsUiButton>
      </div>
      <WmsUiTable :columns="supplierColumns" :rows="masterData.suppliers" row-key="id">
        <template #cell-code="{ row }"><span class="data-code">{{ row.code }}</span></template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="row.status === 'active' ? 'success' : 'neutral'">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }"><WmsUiButton size="sm" variant="ghost" @click="supplierModal = { open: true, item: row }">ویرایش</WmsUiButton></template>
      </WmsUiTable>
    </WmsUiCard>

    <!-- Employees -->
    <WmsUiCard v-else-if="activeTab === 'employees'" :padded="false">
      <div class="flex items-center justify-between border-b border-line p-4">
        <p class="text-sm text-ink-faint">{{ masterData.employees.length }} کارمند</p>
        <WmsUiButton size="sm" variant="primary" @click="employeeModal = { open: true, item: null }">افزودن کارمند</WmsUiButton>
      </div>
      <WmsUiTable :columns="employeeColumns" :rows="masterData.employees" row-key="id">
        <template #cell-role="{ row }"><WmsUiBadge tone="info">{{ titleCase(row.role) }}</WmsUiBadge></template>
        <template #cell-status="{ row }"><WmsUiBadge :tone="row.status === 'active' ? 'success' : 'neutral'">{{ titleCase(row.status) }}</WmsUiBadge></template>
        <template #actions="{ row }"><WmsUiButton size="sm" variant="ghost" @click="employeeModal = { open: true, item: row }">ویرایش</WmsUiButton></template>
      </WmsUiTable>
    </WmsUiCard>

    <!-- Inventory Rules -->
    <WmsUiCard v-else title="قوانین موجودی" subtitle="اعمال خودکار برای هر دسته‌بندی کالا">
      <WmsUiTable :columns="ruleColumns" :rows="masterData.rules" row-key="id">
        <template #cell-categoryId="{ row }">{{ masterData.categoryName(row.categoryId) }}</template>
        <template #cell-requireAdjustmentReason="{ row }">
          <WmsUiBadge :tone="row.requireAdjustmentReason ? 'success' : 'neutral'">{{ row.requireAdjustmentReason ? 'الزامی' : 'اختیاری' }}</WmsUiBadge>
        </template>
      </WmsUiTable>
    </WmsUiCard>

    <WmsModalsWarehouseModal v-model="warehouseModal.open" :warehouse="warehouseModal.item" />
    <WmsModalsItemModal v-model="itemModal.open" :item="itemModal.item" />
    <WmsModalsEmployeeModal v-model="employeeModal.open" :employee="employeeModal.item" />
    <WmsModalsSupplierModal v-model="supplierModal.open" :supplier="supplierModal.item" />
    <WmsModalsCategoryModal v-model="categoryModal.open" :category="categoryModal.item" @saved="masterData.saveCategory" />
    <WmsModalsUnitModal v-model="unitModal.open" :unit="unitModal.item" @saved="masterData.saveUnit" />
    <WmsModalsLocationModal v-model="locationModal.open" :location="locationModal.item" @saved="masterData.saveLocation" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type {
  TableColumn, Warehouse, StorageLocation, Item, ItemCategory, Unit, Supplier, Employee
} from '~/types'

const masterData = useMasterDataStore()
onMounted(() => masterData.loadAll())

const activeTab = ref('warehouses')
const tabs = [
  { label: 'انبارها', value: 'warehouses' },
  { label: 'محل‌های نگهداری', value: 'locations' },
  { label: 'کالاها', value: 'items' },
  { label: 'دسته‌بندی‌ها', value: 'categories' },
  { label: 'واحدها', value: 'units' },
  { label: 'تأمین‌کنندگان', value: 'suppliers' },
  { label: 'کارمندان', value: 'employees' },
  { label: 'قوانین موجودی', value: 'rules' }
]

const warehouseModal = ref<{ open: boolean; item: Warehouse | null }>({ open: false, item: null })
const locationModal = ref<{ open: boolean; item: StorageLocation | null }>({ open: false, item: null })
const itemModal = ref<{ open: boolean; item: Item | null }>({ open: false, item: null })
const categoryModal = ref<{ open: boolean; item: ItemCategory | null }>({ open: false, item: null })
const unitModal = ref<{ open: boolean; item: Unit | null }>({ open: false, item: null })
const supplierModal = ref<{ open: boolean; item: Supplier | null }>({ open: false, item: null })
const employeeModal = ref<{ open: boolean; item: Employee | null }>({ open: false, item: null })

const warehouseColumns: TableColumn<Warehouse>[] = [
  { key: 'code', label: 'کد' }, { key: 'name', label: 'نام' }, { key: 'address', label: 'نشانی' }, { key: 'status', label: 'وضعیت' }
]
const locationColumns: TableColumn<StorageLocation>[] = [
  { key: 'code', label: 'کد' }, { key: 'name', label: 'شرح' }, { key: 'warehouseId', label: 'انبار' }, { key: 'status', label: 'وضعیت' }
]
const itemColumns: TableColumn<Item>[] = [
  { key: 'code', label: 'کد' }, { key: 'name', label: 'نام' }, { key: 'categoryId', label: 'دسته‌بندی' }, { key: 'unitId', label: 'واحد' }, { key: 'status', label: 'وضعیت' }
]
const categoryColumns: TableColumn<ItemCategory>[] = [
  { key: 'name', label: 'نام' }, { key: 'status', label: 'وضعیت' }
]
const unitColumns: TableColumn<Unit>[] = [
  { key: 'code', label: 'کد' }, { key: 'name', label: 'نام' }
]
const supplierColumns: TableColumn<Supplier>[] = [
  { key: 'code', label: 'کد' }, { key: 'name', label: 'شرکت' }, { key: 'contact', label: 'راه ارتباطی' }, { key: 'email', label: 'ایمیل' }, { key: 'status', label: 'وضعیت' }
]
const employeeColumns: TableColumn<Employee>[] = [
  { key: 'name', label: 'نام' }, { key: 'email', label: 'ایمیل' }, { key: 'role', label: 'نقش' }, { key: 'status', label: 'وضعیت' }
]
const ruleColumns: TableColumn[] = [
  { key: 'categoryId', label: 'دسته‌بندی' }, { key: 'minStockDefault', label: 'حداقل موجودی پیش‌فرض', align: 'right' },
  { key: 'reorderPoint', label: 'نقطه سفارش مجدد', align: 'right' }, { key: 'requireAdjustmentReason', label: 'دلیل اصلاح موجودی' }
]
</script>
