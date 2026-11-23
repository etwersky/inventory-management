<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

const STEP = 1000
const DEBOUNCE_MS = 300

const budget = ref(0)
const maxBudget = ref(0)
const items = ref([])
const totalCost = ref(0)
const remainingBudget = ref(0)

const initialized = ref(false)
const loading = ref(false)
const error = ref(null)
const pending = ref(false) // budget changed, recommendations not yet refreshed

const submitting = ref(false)
const submitError = ref(null)
const createdOrder = ref(null)

let debounceTimer = null
let requestId = 0

const money = (v) => formatCurrency(Number(v) || 0, currentCurrency.value)
const money2 = (v) => formatCurrencyWithDecimals(Number(v) || 0, currentCurrency.value, 2)

const formatDate = (value) => {
  const d = new Date(value)
  if (isNaN(d.getTime())) return '-'
  return d.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric', month: 'short', day: 'numeric'
  })
}

const trendClass = (trend) => (['increasing', 'decreasing', 'stable'].includes(trend) ? trend : 'stable')
const trendLabel = (trend) => (['increasing', 'decreasing', 'stable'].includes(trend) ? t(`trends.${trend}`) : trend)

const sliderMax = computed(() => Math.max(STEP, Math.ceil(maxBudget.value / STEP) * STEP))
const canSubmit = computed(() =>
  items.value.length > 0 && !submitting.value && !loading.value && !pending.value && !error.value
)

const loadRecommendations = async () => {
  const value = Number(budget.value)
  if (!Number.isFinite(value) || value < 0) {
    error.value = t('restocking.invalidBudget')
    pending.value = false
    return
  }
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    const data = await api.getRestockRecommendations(value)
    if (id !== requestId) return
    items.value = Array.isArray(data.items) ? data.items : []
    totalCost.value = Number(data.total_cost) || 0
    remainingBudget.value = Number(data.remaining_budget) || 0
    const max = Number(data.max_budget)
    if (Number.isFinite(max)) maxBudget.value = max
  } catch (err) {
    if (id !== requestId) return
    error.value = t('restocking.loadError')
    console.error(err)
  } finally {
    if (id === requestId) {
      loading.value = false
      pending.value = false
    }
  }
}

watch(budget, () => {
  if (!initialized.value) return
  pending.value = true
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
})

const placeOrder = async () => {
  if (!canSubmit.value) return
  const value = Number(budget.value)
  if (!Number.isFinite(value)) {
    submitError.value = t('restocking.invalidBudget')
    return
  }
  submitting.value = true
  submitError.value = null
  createdOrder.value = null
  try {
    createdOrder.value = await api.createRestockOrder({
      budget: value,
      items: items.value.map(i => ({ sku: i.sku, quantity: i.quantity }))
    })
  } catch (err) {
    const detail = err?.response?.data?.detail
    submitError.value = `${t('restocking.submitError')}${typeof detail === 'string' ? ': ' + detail : ''}`
    console.error(err)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  // Initial call determines the slider maximum
  await loadRecommendations()
  if (!error.value) {
    const initial = Math.round((maxBudget.value * 0.25) / STEP) * STEP
    budget.value = Math.min(initial, sliderMax.value)
  }
  initialized.value = true
  if (budget.value > 0 && !error.value) {
    pending.value = false
    await loadRecommendations()
  }
})

onBeforeUnmount(() => clearTimeout(debounceTimer))
</script>

<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <div class="budget-row">
        <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
        <div class="budget-value">{{ money(budget) }}</div>
      </div>
      <input
        id="budget-slider"
        v-model.number="budget"
        type="range"
        min="0"
        :max="sliderMax"
        :step="STEP"
        :disabled="!initialized && !error"
        class="budget-slider"
      />
      <div class="budget-hint">{{ t('restocking.budgetMax', { amount: money(maxBudget) }) }}</div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="stats-grid">
      <div class="stat-card info">
        <div class="stat-label">{{ t('restocking.totalCost') }}</div>
        <div class="stat-value">{{ money(totalCost) }}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">{{ t('restocking.remaining') }}</div>
        <div class="stat-value">{{ money(remainingBudget) }}</div>
      </div>
    </div>

    <div v-if="createdOrder" class="success-message" role="status">
      <strong>{{ t('restocking.successTitle') }}</strong>
      {{ t('restocking.successMessage', {
        orderNumber: createdOrder.order_number,
        date: formatDate(createdOrder.expected_delivery)
      }) }}
    </div>
    <div v-if="submitError" class="error" role="alert">{{ submitError }}</div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ items.length }})</h3>
        <button
          type="button"
          class="place-order-btn"
          :disabled="!canSubmit"
          @click="placeOrder"
        >
          {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
        </button>
      </div>

      <div v-if="loading && !items.length" class="loading">{{ t('restocking.loading') }}</div>
      <div v-else-if="!items.length && !error" class="empty-state">{{ t('restocking.empty') }}</div>
      <div v-else-if="items.length" :class="['table-wrapper', { refreshing: loading || pending }]">
        <table>
          <thead>
            <tr>
              <th>{{ t('restocking.sku') }}</th>
              <th>{{ t('restocking.itemName') }}</th>
              <th>{{ t('restocking.trend') }}</th>
              <th class="num">{{ t('restocking.forecastedDemand') }}</th>
              <th class="num">{{ t('restocking.onHand') }}</th>
              <th class="num">{{ t('restocking.quantity') }}</th>
              <th class="num">{{ t('restocking.unitCost') }}</th>
              <th class="num">{{ t('restocking.lineTotal') }}</th>
              <th class="num">{{ t('restocking.leadTime') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.sku">
              <td><strong>{{ item.sku }}</strong></td>
              <td>{{ translateProductName(item.item_name) }}</td>
              <td><span :class="['badge', trendClass(item.trend)]">{{ trendLabel(item.trend) }}</span></td>
              <td class="num">{{ item.forecasted_demand.toLocaleString() }}</td>
              <td class="num">{{ item.on_hand.toLocaleString() }}</td>
              <td class="num"><strong>{{ item.quantity.toLocaleString() }}</strong></td>
              <td class="num">{{ money2(item.unit_cost) }}</td>
              <td class="num"><strong>{{ money2(item.line_total) }}</strong></td>
              <td class="num">{{ item.lead_time_days }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.restocking {
  min-width: 0;
}

.card {
  min-width: 0;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-weight: 600;
  color: #0f172a;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
}

.budget-hint {
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.stats-grid > * {
  min-width: 0;
}

.card-header {
  gap: 1rem;
  flex-wrap: wrap;
}

.card-title {
  min-width: 0;
}

.place-order-btn {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  color: #64748b;
  cursor: not-allowed;
}

.table-wrapper {
  overflow-x: auto;
  max-width: 100%;
  transition: opacity 0.15s;
}

.table-wrapper.refreshing {
  opacity: 0.6;
}

.table-wrapper table {
  min-width: 760px;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #64748b;
}

.success-message {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}
</style>
