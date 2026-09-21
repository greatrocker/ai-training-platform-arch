<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";

const departments = ref([]);
const groups = ref([]);
const roles = ref([]);
const permissions = ref([]);

const newDeptName = ref("");
const newGroupName = ref("");
const newRoleName = ref("");
const loading = ref(true);

async function reload() {
  const [d, g, r, p] = await Promise.all([
    axios.get("/api/rbac/departments", { withCredentials: true }),
    axios.get("/api/rbac/groups", { withCredentials: true }),
    axios.get("/api/rbac/roles", { withCredentials: true }),
    axios.get("/api/rbac/permissions", { withCredentials: true }),
  ]);
  departments.value = d.data;
  groups.value = g.data;
  roles.value = r.data;
  permissions.value = p.data;
  loading.value = false;
}

async function addDepartment() {
  if (!newDeptName.value) return;
  await axios.post("/api/rbac/departments", { dept_name: newDeptName.value }, { withCredentials: true });
  newDeptName.value = "";
  await reload();
}

async function addGroup() {
  if (!newGroupName.value) return;
  await axios.post("/api/rbac/groups", { group_name: newGroupName.value }, { withCredentials: true });
  newGroupName.value = "";
  await reload();
}

async function addRole() {
  if (!newRoleName.value) return;
  await axios.post("/api/rbac/roles", { role_name: newRoleName.value }, { withCredentials: true });
  newRoleName.value = "";
  await reload();
}

onMounted(reload);
</script>

<template>
  <div class="page-header">
    <h1>權限 / 部門 / 群組管理</h1>
    <p class="subtitle">管理部門、群組、角色與權限，控制各業務服務的存取範圍</p>
  </div>

  <div class="grid">
    <div class="card">
      <h2>部門</h2>
      <div class="chip-list">
        <span v-for="d in departments" :key="d.dept_id" class="chip">{{ d.dept_name }}</span>
        <span v-if="!loading && !departments.length" class="hint">尚無部門</span>
      </div>
      <div class="toolbar">
        <input v-model="newDeptName" placeholder="新部門名稱" @keyup.enter="addDepartment" />
        <button class="primary" @click="addDepartment">新增</button>
      </div>
    </div>

    <div class="card">
      <h2>群組</h2>
      <div class="chip-list">
        <span v-for="g in groups" :key="g.group_id" class="chip">{{ g.group_name }}</span>
        <span v-if="!loading && !groups.length" class="hint">尚無群組</span>
      </div>
      <div class="toolbar">
        <input v-model="newGroupName" placeholder="新群組名稱" @keyup.enter="addGroup" />
        <button class="primary" @click="addGroup">新增</button>
      </div>
    </div>

    <div class="card">
      <h2>角色</h2>
      <div class="chip-list">
        <span v-for="r in roles" :key="r.role_id" class="chip">{{ r.role_name }}</span>
        <span v-if="!loading && !roles.length" class="hint">尚無角色</span>
      </div>
      <div class="toolbar">
        <input v-model="newRoleName" placeholder="新角色名稱" @keyup.enter="addRole" />
        <button class="primary" @click="addRole">新增</button>
      </div>
    </div>

    <div class="card span-full">
      <h2>權限清單</h2>
      <p class="hint">由各服務程式碼註冊，唯讀。</p>
      <div class="chip-list">
        <span v-for="p in permissions" :key="p.perm_id" class="chip chip-mono">{{ p.perm_key }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}
.span-full {
  grid-column: 1 / -1;
}
.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
  margin-bottom: 14px;
}
.chip {
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.8rem;
}
.chip-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
}
.toolbar input {
  flex: 1;
}
</style>
