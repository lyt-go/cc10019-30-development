<template>
  <section class="page" data-module="crowd_select">
    <header class="page-head">
      <div>
        <h2>人群圈选管理</h2>
        <p class="page-desc">维护基于标签组合的人群圈选规则与动态刷新管理，为人群圈选提供可验证的数据工程流程。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" data-testid="open-create" type="button" @click="openCreate">登记圈选条件</button>
        <button class="btn" data-testid="export" type="button" @click="exportRows">导出人群圈选清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field.key" class="filter-item">
        <span>{{ field.label }}</span>
        <input v-model="filters[field.key]" :data-testid="`filter-${field.key}`" :placeholder="`按${field.label}检索`" />
      </label>
      <button class="btn" data-testid="query" type="submit">查询</button>
      <button class="btn ghost" data-testid="reset" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)" :data-testid="`row-${row.id}`" :data-status="String(row.status)">
          <td v-for="column in columns" :key="column.key">{{ row[column.key] ?? '—' }}</td>
          <td class="row-actions">
            <button
              class="link"
              type="button"
              :data-testid="`rerun-${row.id}`"
              @click="rerunCrowd(row)"
            >
              重算圈选
            </button>
            <button
              class="link"
              type="button"
              :data-testid="`deliver-${row.id}`"
              @click="exportDelivery(row)"
            >
              导出交付文件
            </button>
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              :data-testid="`action-${row.id}-${action}`"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无人群圈选数据，可先登记圈选条件</td>
        </tr>
      </tbody>
    </table>

    <div v-if="showCreate" class="modal-backdrop" data-testid="create-modal">
      <form class="modal" @submit.prevent="submitCreate">
        <h3>登记圈选条件</h3>
        <label v-for="field in columns" :key="field.key" class="create-field">
          <span>{{ field.label }}</span>
          <input v-model="createValues[field.key]" :data-testid="`create-${field.key}`" required />
        </label>
        <div class="page-actions">
          <button class="btn" type="button" @click="showCreate = false">取消</button>
          <button class="btn primary" data-testid="submit-create" type="submit" :disabled="creating">
            {{ creating ? '提交中…' : '确认登记' }}
          </button>
        </div>
      </form>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条人群圈选记录</span>
      <span v-if="infoMessage" class="info-text">{{ infoMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, any>

const ENDPOINT = '/api/crowd-select'
const columns = [
  { key: 'condition_id', label: '条件编号' },
  { key: 'condition_name', label: '条件名称' },
  { key: 'logic_expr', label: '逻辑表达式' },
  { key: 'size_estimate', label: '预计规模' },
  { key: 'refresh_freq', label: '刷新频率' },
  { key: 'output_set', label: '输出集合' },
  { key: 'compute_version', label: '计算版本' },
  { key: 'status', label: '状态' },
]
const actions = ["预估规模", "标记生效", "标记过期"]
const statuses = ["草稿", "预估中", "已生效", "已过期"]
const metricNames = ["圈选条件总数", "预估中条件", "已生效条件"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const infoMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 2)
const showCreate = ref(false)
const creating = ref(false)
const createValues = ref<Record<string, string>>({})
const stats = computed(() => [
  { label: metricNames[0], value: total.value },
  { label: metricNames[1], value: rows.value.filter((row) => row.status === statuses[1]).length },
  { label: metricNames[2], value: rows.value.filter((row) => row.status === statuses[2]).length },
])

function resetFilters() {
  filters.value = {}
  void reload()
}

async function exportRows() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value).toString()
  try {
    const response = await request(`${ENDPOINT}/export?${query}`)
    if (!response.ok) throw new Error('导出失败，请稍后重试')
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = 'crowd_select.csv'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '导出失败'
  }
}

function openCreate() {
  createValues.value = Object.fromEntries(columns.map((field) => [field.key, '']))
  errorMessage.value = ''
  showCreate.value = true
}

async function submitCreate() {
  creating.value = true
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST', body: JSON.stringify(createValues.value),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) throw new Error(payload.message || '登记失败')
    showCreate.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登记失败'
  } finally {
    creating.value = false
  }
}

async function rerunCrowd(row: Row) {
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.condition_id}/run`, { method: 'POST' })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail || '圈选重算失败，请稍后重试')
    const result = payload.entry ?? {}
    infoMessage.value = `${row.condition_id} 已重算至 v${result.compute_version}，命中 ${result.matched_count} 人`
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '圈选重算失败'
  }
}

async function exportDelivery(row: Row) {
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    const response = await request(`/api/crowd-delivery/export/${row.condition_id}`, { method: 'POST' })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail || '交付文件导出失败，请先执行圈选')
    const entry = payload.entry ?? {}
    infoMessage.value = `已导出交付 ${entry.delivery_id}（计算版本 v${entry.compute_version}，${entry.member_count} 人），可到人群交付页下载核对`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '交付文件导出失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('人群圈选动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '人群圈选操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('圈选条件列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '人群圈选列表读取失败'
  }
}

onMounted(reload)
</script>
