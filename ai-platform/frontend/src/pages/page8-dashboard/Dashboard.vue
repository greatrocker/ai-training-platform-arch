<script setup>
import { ref, onMounted, onUnmounted } from "vue";

const connected = ref(false);
let socket;

onMounted(() => {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${window.location.host}/api/dashboard/ws`);
  socket.onopen = () => (connected.value = true);
  socket.onclose = () => (connected.value = false);
});

onUnmounted(() => socket?.close());
</script>

<template>
  <div class="page-header">
    <h1>Dashboard</h1>
    <p class="subtitle">系統連線與服務健康狀態</p>
  </div>

  <div class="card status-card">
    <div class="status-row">
      <span class="dot" :class="{ on: connected }"></span>
      <div>
        <div class="status-title">WebSocket 連線狀態</div>
        <div class="hint">{{ connected ? "已連線至 dashboard-service" : "未連線" }}</div>
      </div>
      <span class="badge" :class="connected ? 'badge-success' : 'badge-neutral'">
        {{ connected ? "ONLINE" : "OFFLINE" }}
      </span>
    </div>
  </div>

  <div class="card">
    <div class="empty-state">
      <p>在線人數 / 各服務健康狀態 / GPU 使用率 / 今日 Alarm 統計尚未實作，僅有連線骨架。</p>
    </div>
  </div>
</template>

<style scoped>
.status-card { padding: 20px 22px; }
.status-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.status-title {
  font-weight: 600;
  font-size: 0.9rem;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-text-faint);
  flex-shrink: 0;
}
.dot.on {
  background: var(--color-success);
  box-shadow: 0 0 0 4px var(--color-success-soft);
}
.status-row .badge {
  margin-left: auto;
}
</style>
