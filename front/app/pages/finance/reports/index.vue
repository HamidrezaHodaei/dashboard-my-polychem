<script setup lang="ts"></script>
<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Financial reports</h1>
      <p class="mt-1 text-sm text-ink-700/60">Business profit, loss, and liquidity reports</p>
    </div>
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <NuxtLink to="/finance/reports/profit-loss" class="rounded-xl border border-paper-200 bg-white p-5 shadow-card hover:border-gain-400">
        <p class="text-sm font-semibold text-ink-900">Profit and loss</p>
        <p class="mt-1 text-sm text-ink-700/60">Compare revenue, purchases, and expenses for a selected period</p>
      </NuxtLink>
      <NuxtLink to="/finance/reports/cash-flow" class="rounded-xl border border-paper-200 bg-white p-5 shadow-card hover:border-gain-400">
        <p class="text-sm font-semibold text-ink-900">Cash flow</p>
        <p class="mt-1 text-sm text-ink-700/60">Cash, bank, and total liquidity position</p>
      </NuxtLink>
    </div>
  </div>
</template>
