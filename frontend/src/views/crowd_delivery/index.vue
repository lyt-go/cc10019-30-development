<template>
  <section class="page" data-module="crowd_delivery">
    <header class="page-head">
      <div>
        <h2>人群交付管理</h2>
        <p class="page-desc">从已计算的圈选成员导出版本化交付文件，写明计算版本与实际成员编号；交付后名单不可变，支持下载核对与签收流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn" data-testid="reload" type="button" @click="reload">刷新列表</button>
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
          <th>版本状态</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)" :data-testid="`row-${row.id}`" :data-status="String(row.status)">
          <td v-for="column in columns" :key="column.key">{{ row[column.key] ?? '—' }}</td>
          <td>
            <span v-if="row.is_latest_version">当前最新 v{{ row.compute_version }}</span>
            <span v-else class="error-text">
              交付 v{{ row.compute_version }}，已有 v{{ row.latest_compute_version }}
              <template v-if="row.pending_change">（未生效变动 {{ row.pending_change.matched_delta > 0 ? '+' : '' }}{{ row.pending_change.matched_delta }} 人）</template>
            </span>
          </td>
          <td class="row-actions">
            <button class="link" type="button" :data-testid="`download-${row.id}`" @click="downloadFile(row)">下载交付文件</button>
            <button class="link" type="button" :data-testid="`verify-${row.id}`" @click="verifyRow(row)">核对</button>
            <button v-if="row.status === '待签收'" class="link" type="button" :data-testid="`confirm-${row.id}`" @click="runAction('确认签收', row)">确认签收</button>
            <button v-if="row.status === '待签收'" class="link" type="button" :data-testid="`void-${row.id}`" @click="runAction('作废', row)">作废</button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无人群交付记录，可先在人群圈选页执行圈选并导出交付文件</td>
        </tr>
      </tbody>
    </table>

    <div v-if="verifyResult" class="modal-backdrop" data-testid="verify-modal" @click.self="verifyResult = null">
      <div class="modal">
        <h3>交付核对 {{ verifyResult.delivery_id }}</h3>
        <p>圈选范围：{{ verifyResult.output_set }}（{{ verifyResult.logic_expr }}）</p>
        <p>交付版本：v{{ verifyResult.compute_version }}　最新计算版本：v{{ verifyResult.latest_compute_version }}</p>
        <p>名单数量：{{ verifyResult.member_count }}（文件实列 {{ verifyResult.listed_members }} 人，{{ verifyResult.count_matches ? '数量一致' : '数量不一致' }}）</p>
        <p>校验和：{{ verifyResult.checksum }}（{{ verifyResult.checksum_verified ? '校验通过' : '校验失败' }}）</p>
        <p>状态：{{ verifyResult.status }}</p>
        <div class="page-actions">
          <button class="btn" type="button" @click="verifyResult = null">关闭</button>
        </div>
      </div>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条人群交付记录</span>
      <span v-if="infoMessage" class="info-text">{{ infoMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, any>

const ENDPOINT = '/api/crowd-delivery'
const columns = [
  { key: 'delivery_id', label: '交付编号' },
  { key: 'condition_id', label: '圈选条件' },
  { key: 'condition_name', label: '条件名称' },
  { key: 'compute_version', label: '计算版本' },
  { key: 'member_count', label: '名单数量' },
  { key: 'checksum', label: '校验和' },
  { key: 'status', label: '状态' },
  { key: 'exported_at', label: '导出时间' },
  { key: 'confirmed_at', label: '签收时间' },
]
const filterFields = columns.slice(0, 2).concat([{ key: 'status', label: '状态' }])

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const infoMessage = ref('')
const filters = ref<Record<string, string>>({})
const verifyResult = ref<Row | null>(null)
const stats = computed(() => [
  { label: '交付记录总数', value: total.value },
  { label: '待签收', value: rows.value.filter((row) => row.status === '待签收').length },
  { label: '已签收', value: rows.value.filter((row) => row.status === '已签收').length },
])

function resetFilters() {
  filters.value = {}
  void reload()
}

async function downloadFile(row: Row) {
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.delivery_id}/download`)
    if (!response.ok) throw new Error('交付文件下载失败，请稍后重试')
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = `crowd_delivery_${row.delivery_id}.json`
    link.click()
    URL.revokeObjectURL(url)
    infoMessage.value = `已下载 ${row.delivery_id}（计算版本 v${row.compute_version}，${row.member_count} 人）`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '交付文件下载失败'
  }
}

async function verifyRow(row: Row) {
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.delivery_id}/verify`)
    if (!response.ok) throw new Error('交付核对失败，请稍后重试')
    verifyResult.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '交付核对失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.delivery_id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail || '交付动作未生效，请稍后重试')
    infoMessage.value = `${row.delivery_id} ${action}成功`
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '人群交付操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('交付记录列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '交付记录列表读取失败'
  }
}

onMounted(reload)
</script>
