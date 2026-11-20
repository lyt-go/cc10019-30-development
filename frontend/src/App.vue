<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">用户标签画像与行为分析平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向用户行为埋点采集、标签体系构建、人群圈选与行为特征分析的数据应用平台。</span>
        <span class="head-user">当前值班：{{ store.operator }} · {{ store.shiftLabel }}</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

const store = useSessionStore()

const navItems = [{ label: "运营概览", path: "/" }, { label: "事件埋点", path: "/event_track" }, { label: "标签定义", path: "/tag_define" }, { label: "标签计算", path: "/tag_compute" }, { label: "人群圈选", path: "/crowd_select" }, { label: "人群交付", path: "/crowd_delivery" }, { label: "行为路径", path: "/behavior_path" }, { label: "留存计算", path: "/retention_calc" }, { label: "用户分群", path: "/user_segment" }, { label: "生命周期价值", path: "/lifetime_value" }, { label: "漏斗分析", path: "/funnel_analyze" }, { label: "事件清洗", path: "/event_cleanse" }, { label: "会话切割", path: "/session_split" }, { label: "画像卡片", path: "/profile_card" }, { label: "属性字典", path: "/attr_dict" }, { label: "交集分析", path: "/overlap_analysis" }, { label: "标签下钻", path: "/tag_drill" }, { label: "事件聚合", path: "/event_aggregate" }, { label: "标签快照", path: "/tag_snapshot" }, { label: "行为热力", path: "/behavior_heatmap" }]
</script>
