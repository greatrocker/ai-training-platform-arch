<script setup>
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

const links = [
  { to: "/dataset", label: "資料集匯入", icon: "folder" },
  { to: "/annotation", label: "標注", icon: "tag" },
  { to: "/training", label: "模型訓練", icon: "cpu" },
  { to: "/pipeline", label: "邏輯編排 / RTSP", icon: "flow" },
  { to: "/monitor", label: "即時監控", icon: "monitor" },
  { to: "/rbac", label: "權限管理", icon: "shield" },
  { to: "/dashboard", label: "Dashboard", icon: "grid" },
];

const icons = {
  folder: "M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z",
  tag: "m3 11 8-8h7a1 1 0 0 1 1 1v7l-8 8a1.5 1.5 0 0 1-2 0l-6-6a1.5 1.5 0 0 1 0-2Z M16 8h.01",
  cpu: "M8 3v3M12 3v3M16 3v3M8 18v3M12 18v3M16 18v3M3 8h3M3 12h3M3 16h3M18 8h3M18 12h3M18 16h3M7 7h10v10H7z",
  flow: "M5 5h4v4H5zM15 15h4v4h-4zM7 9v4a2 2 0 0 0 2 2h2m4-6V7a2 2 0 0 0-2-2h-2",
  monitor: "M3 5a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5ZM8 21h8M12 16v5",
  shield: "M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z",
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
};
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <span class="brand-mark">AI</span>
      <span class="brand-text">訓練平台</span>
    </div>

    <nav>
      <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="nav-link" active-class="active">
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path :d="icons[link.icon]" />
        </svg>
        <span>{{ link.label }}</span>
      </RouterLink>
    </nav>

    <div class="user" v-if="auth.isAuthenticated">
      <div class="avatar">{{ (auth.displayName || "?").slice(0, 1).toUpperCase() }}</div>
      <div class="user-info">
        <div class="user-name">{{ auth.displayName }}</div>
        <div class="user-role" v-if="auth.roles?.length">{{ auth.roles.join(", ") }}</div>
      </div>
      <button class="ghost logout-btn" @click="auth.logout" title="登出">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
        </svg>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  padding: 20px 14px;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100vh;
  position: sticky;
  top: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 10px 20px;
}

.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.8rem;
}

.brand-text {
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: -0.01em;
}

nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.86rem;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}

.nav-link:hover {
  background: var(--color-surface-alt);
  color: var(--color-text);
}

.nav-link.active {
  background: var(--color-primary-soft);
  color: var(--color-primary-soft-text);
}

.nav-icon {
  width: 17px;
  height: 17px;
  flex-shrink: 0;
}

.user {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-top: 1px solid var(--color-border);
  padding-top: 16px;
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary-soft-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 0.82rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 0.72rem;
  color: var(--color-text-faint);
  text-transform: capitalize;
}

.logout-btn {
  padding: 6px;
  border: none;
  color: var(--color-text-faint);
}

.logout-btn:hover {
  color: var(--color-danger);
  background: var(--color-danger-soft);
}
</style>
