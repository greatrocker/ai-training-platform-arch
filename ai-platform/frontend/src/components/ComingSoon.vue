<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
  serviceName: { type: String, default: "" },
});
</script>

<template>
  <div class="page-header">
    <h1>{{ title }}</h1>
    <p class="subtitle" v-if="description">{{ description }}</p>
  </div>
  <div class="card">
    <div class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40" style="margin: 0 auto 12px; opacity: 0.5">
        <path d="M12 8v5M12 16h.01" stroke-linecap="round" />
        <circle cx="12" cy="12" r="9" />
      </svg>
      <p>此頁面尚未實作業務邏輯，僅有健康檢查端點<span v-if="serviceName">（<code>{{ serviceName }}</code>）</span>。</p>
      <p class="hint">依架構文件的落地順序，將在後續階段補上。</p>
    </div>
  </div>
</template>
