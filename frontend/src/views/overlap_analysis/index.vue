<template>
  <section class="page" data-module="overlap_analysis">
    <header class="page-head">
      <div>
        <h2>交集分析</h2>
        <p class="page-desc">按交付编号读取人群交付文件的成员集合比较两个活动范围；交付文件不可变，重算圈选不会改变可核对的人数。</p>
      </div>
      <div class="page-actions">
        <button class="btn" data-testid="reload" type="button" @click="reload">刷新列表</button>
      </div>
    </header>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)" :data-testid="`row-${row.id}`" :data-status="String(row.status)">
          <td v-for="column in columns" :key="column.key">{{ row[column.key] || '—' }}</td>
          <td class="row-actions">
            <button class="link" type="button" :data-testid="`run-${row.id}`" @click="runTask(row)">运行分析</button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无交集分析任务</td>
        </tr>
      </tbody>
    </table>

    <div v-if="result" class="analysis-result" data-testid="overlap-result">
      <h3>分析结果 {{ result.task_id }}（{{ result.intersect_mode }}）</h3>
      <div class="stat-row">
        <article class="stat-card">
          <span class="stat-label">人群A人数</span>
          <strong class="stat-value">{{ result.users_a_count }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">人群B人数</span>
          <strong class="stat-value">{{ result.users_b_count }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">结果人数</span>
          <strong class="stat-value">{{ result.result_count }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">覆盖率</span>
          <strong class="stat-value">{{ (result.intersection_rate * 100).toFixed(1) }}%</strong>
        </article>
      </div>
      <p v-if="result.source === 'delivery_file'" class="result-source">
        数据来源：人群交付文件 {{ result.delivery_a }}（{{ result.crowd_a }} 计算版本 v{{ result.compute_version_a }}）
        × {{ result.delivery_b }}（{{ result.crowd_b }} 计算版本 v{{ result.compute_version_b }}），名单以交付快照为准。
      </p>
      <p v-else class="result-source">数据来源：圈选实时结果（任务未指定交付编号，人数可能随重算变化）。</p>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条交集任务</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, any>

const ENDPOINT = '/api/overlap-analysis'
const columns = [
  { key: 'task_id', label: '任务编号' },
  { key: 'delivery_a', label: '人群A交付' },
  { key: 'delivery_b', label: '人群B交付' },
  { key: 'intersect_mode', label: '交集方式' },
  { key: 'result_table', label: '结果表名' },
  { key: 'status', label: '状态' },
]

const rows = ref<Row[]>([])
const total = ref(0)
const result = ref<Row | null>(null)
const errorMessage = ref('')

async function runTask(row: Row) {
  errorMessage.value = ''
  result.value = null
  try {
    const response = await request(`${ENDPOINT}/${row.task_id}/run`, { method: 'POST' })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail || '交集分析运行失败，请稍后重试')
    result.value = payload.entry ?? null
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '交集分析运行失败'
  }
}

async function reload() {
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT)
    if (!response.ok) {
      throw new Error('交集任务列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '交集任务列表读取失败'
  }
}

onMounted(reload)
</script>
