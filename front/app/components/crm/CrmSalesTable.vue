<template>
  <div class="overflow-x-auto">
    <Table v-if="rows.length">
      <TableHeader>
        <TableRow>
          <TableHead>تاریخ</TableHead><TableHead>مشتری</TableHead><TableHead>کالا</TableHead><TableHead>مقدار</TableHead><TableHead>مبلغ</TableHead><TableHead>وضعیت</TableHead><TableHead
            v-if="showActions"
            class="text-right"
          >
            عملیات
          </TableHead>
        </TableRow>
      </TableHeader><TableBody>
        <TableRow
          v-for="row in rows"
          :key="row.id"
        >
          <TableCell class="text-muted-foreground">
            {{ row.dateLabel || '-' }}
          </TableCell><TableCell class="font-medium">
            {{ row.customer }}
          </TableCell><TableCell>{{ row.product }}</TableCell><TableCell>{{ row.tons.toLocaleString('fa-IR') }} کیلوگرم</TableCell><TableCell :class="row.isReturn && 'text-destructive'">
            {{ formatMoney(row.amount) }}
          </TableCell><TableCell>
            <Badge :variant="row.isReturn ? 'destructive' : 'success'">
              {{ row.isReturn ? 'مرجوع‌شده' : statusLabel(row.status) }}
            </Badge>
          </TableCell><TableCell
            v-if="showActions"
            class="text-right"
          >
            <Button
              variant="ghost"
              size="icon"
              title="ویرایش"
            >
              <Icon
                name="lucide:more-horizontal"
                class="size-4"
              />
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table><AccessEmptyState v-else />
  </div>
</template>

<script setup lang="ts">
import type { CrmSale } from '~/composables/useCrmDashboard'

defineProps<{ rows: CrmSale[], showActions?: boolean }>()

const formatMoney = (value: number) =>
  `${Math.round(value || 0).toLocaleString('fa-IR')} ریال`
const statusNames: Record<string, string> = { completed: 'تکمیل‌شده', complete: 'تکمیل‌شده', paid: 'پرداخت‌شده', pending: 'در انتظار', processing: 'در حال پردازش', draft: 'پیش‌نویس', cancelled: 'لغوشده', canceled: 'لغوشده', returned: 'مرجوع‌شده' }
function statusLabel(status?: string) { return status ? statusNames[status.toLowerCase()] || status : 'تکمیل‌شده' }</script>
