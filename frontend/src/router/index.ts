import { createRouter, createWebHistory } from 'vue-router'

import Overview from '@/views/Overview.vue'
const EventTrack = () => import('@/views/event_track/index.vue')
const TagDefine = () => import('@/views/tag_define/index.vue')
const TagCompute = () => import('@/views/tag_compute/index.vue')
const CrowdSelect = () => import('@/views/crowd_select/index.vue')
const CrowdDelivery = () => import('@/views/crowd_delivery/index.vue')
const BehaviorPath = () => import('@/views/behavior_path/index.vue')
const RetentionCalc = () => import('@/views/retention_calc/index.vue')
const UserSegment = () => import('@/views/user_segment/index.vue')
const LifetimeValue = () => import('@/views/lifetime_value/index.vue')
const FunnelAnalyze = () => import('@/views/funnel_analyze/index.vue')
const EventCleanse = () => import('@/views/event_cleanse/index.vue')
const SessionSplit = () => import('@/views/session_split/index.vue')
const ProfileCard = () => import('@/views/profile_card/index.vue')
const AttrDict = () => import('@/views/attr_dict/index.vue')
const OverlapAnalysis = () => import('@/views/overlap_analysis/index.vue')
const TagDrill = () => import('@/views/tag_drill/index.vue')
const EventAggregate = () => import('@/views/event_aggregate/index.vue')
const TagSnapshot = () => import('@/views/tag_snapshot/index.vue')
const BehaviorHeatmap = () => import('@/views/behavior_heatmap/index.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: Overview },
    { path: '/event_track', name: 'event_track', component: EventTrack },
    { path: '/tag_define', name: 'tag_define', component: TagDefine },
    { path: '/tag_compute', name: 'tag_compute', component: TagCompute },
    { path: '/crowd_select', name: 'crowd_select', component: CrowdSelect },
    { path: '/crowd_delivery', name: 'crowd_delivery', component: CrowdDelivery },
    { path: '/behavior_path', name: 'behavior_path', component: BehaviorPath },
    { path: '/retention_calc', name: 'retention_calc', component: RetentionCalc },
    { path: '/user_segment', name: 'user_segment', component: UserSegment },
    { path: '/lifetime_value', name: 'lifetime_value', component: LifetimeValue },
    { path: '/funnel_analyze', name: 'funnel_analyze', component: FunnelAnalyze },
    { path: '/event_cleanse', name: 'event_cleanse', component: EventCleanse },
    { path: '/session_split', name: 'session_split', component: SessionSplit },
    { path: '/profile_card', name: 'profile_card', component: ProfileCard },
    { path: '/attr_dict', name: 'attr_dict', component: AttrDict },
    { path: '/overlap_analysis', name: 'overlap_analysis', component: OverlapAnalysis },
    { path: '/tag_drill', name: 'tag_drill', component: TagDrill },
    { path: '/event_aggregate', name: 'event_aggregate', component: EventAggregate },
    { path: '/tag_snapshot', name: 'tag_snapshot', component: TagSnapshot },
    { path: '/behavior_heatmap', name: 'behavior_heatmap', component: BehaviorHeatmap },
  ],
})

export default router
