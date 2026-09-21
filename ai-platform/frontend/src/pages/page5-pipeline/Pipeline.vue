<script setup>
import { ref, computed, onMounted, watch } from "vue";
import axios from "axios";
import { VueFlow, useVueFlow, MarkerType } from "@vue-flow/core";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";

const activeTab = ref("flow");

// ---------- Tab A: logic flow editor ----------
const flows = ref([]);
const selectedFlowId = ref("");
const flowName = ref("新流程");
const saving = ref(false);
const saveMessage = ref("");

const nodes = ref([]);
const edges = ref([]);
const selectedNode = ref(null);
const completedJobs = ref([]);

const { onConnect, onNodeClick, onPaneClick } = useVueFlow();

let nodeSeq = 0;
function nextId(prefix) {
  nodeSeq += 1;
  return `${prefix}-${Date.now()}-${nodeSeq}`;
}

const NODE_DEFAULTS = {
  input: { vueFlowType: "input", label: "輸入節點", data: () => ({ kind: "input", job_id: "", model_key: "" }) },
  detect: { vueFlowType: "default", label: "圖像偵測節點", data: () => ({ kind: "detect", target_class: "", confidence_threshold: 0.5 }) },
  logic: { vueFlowType: "default", label: "邏輯節點", data: () => ({ kind: "logic", logic_type: "and", threshold: 1, roi_x: 0, roi_y: 0, roi_w: 0, roi_h: 0, duration_sec: 0 }) },
  output: { vueFlowType: "output", label: "輸出節點", data: () => ({ kind: "output", output_type: "alarm", webhook_url: "" }) },
};

function nodeLabel(kind, data) {
  if (kind === "input") return `輸入\n${data.model_key || "(未選模型)"}`;
  if (kind === "detect") return `偵測\n${data.target_class || "(未設類別)"} @ ${data.confidence_threshold}`;
  if (kind === "logic") return `邏輯\n${data.logic_type}`;
  if (kind === "output") return `輸出\n${data.output_type}`;
  return kind;
}

function addNode(kind) {
  const def = NODE_DEFAULTS[kind];
  const data = def.data();
  const id = nextId(kind);
  nodes.value.push({
    id,
    type: def.vueFlowType,
    position: { x: 80 + ((nodes.value.length * 40) % 400), y: 60 + ((nodes.value.length * 70) % 320) },
    label: nodeLabel(kind, data),
    data,
  });
}

onConnect((connection) => {
  edges.value.push({
    id: nextId("e"),
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle,
    targetHandle: connection.targetHandle,
    markerEnd: MarkerType.ArrowClosed,
  });
});

onNodeClick(({ node }) => {
  selectedNode.value = node;
});

onPaneClick(() => {
  selectedNode.value = null;
});

watch(
  selectedNode,
  (node) => {
    if (node) node.label = nodeLabel(node.data.kind, node.data);
  },
  { deep: true }
);

function deleteSelectedNode() {
  if (!selectedNode.value) return;
  const id = selectedNode.value.id;
  nodes.value = nodes.value.filter((n) => n.id !== id);
  edges.value = edges.value.filter((e) => e.source !== id && e.target !== id);
  selectedNode.value = null;
}

async function loadFlows() {
  const { data } = await axios.get("/api/pipeline/flows", { withCredentials: true });
  flows.value = data;
}

async function loadCompletedJobs() {
  const { data } = await axios.get("/api/training/jobs", { withCredentials: true });
  completedJobs.value = data.filter((j) => j.status === "completed");
}

function loadFlowIntoEditor(flow) {
  flowName.value = flow.name;
  selectedFlowId.value = flow.flow_id;
  try {
    const graph = JSON.parse(flow.graph_json);
    nodes.value = graph.nodes || [];
    edges.value = graph.edges || [];
  } catch {
    nodes.value = [];
    edges.value = [];
  }
  selectedNode.value = null;
}

function newFlow() {
  selectedFlowId.value = "";
  flowName.value = "新流程";
  nodes.value = [];
  edges.value = [];
  selectedNode.value = null;
}

async function saveFlow() {
  saving.value = true;
  saveMessage.value = "";
  try {
    const graph_json = JSON.stringify({
      nodes: nodes.value.map((n) => ({ id: n.id, type: n.type, position: n.position, label: n.label, data: n.data })),
      edges: edges.value.map((e) => ({ id: e.id, source: e.source, target: e.target })),
    });
    if (selectedFlowId.value) {
      await axios.put(`/api/pipeline/flows/${selectedFlowId.value}`, { name: flowName.value, graph_json }, { withCredentials: true });
    } else {
      const { data } = await axios.post("/api/pipeline/flows", { name: flowName.value, graph_json }, { withCredentials: true });
      selectedFlowId.value = data.flow_id;
    }
    saveMessage.value = "已儲存";
    await loadFlows();
  } catch (err) {
    saveMessage.value = err.response?.data?.detail || "儲存失敗";
  } finally {
    saving.value = false;
  }
}

async function deleteFlow(flowId) {
  await axios.delete(`/api/pipeline/flows/${flowId}`, { withCredentials: true });
  if (selectedFlowId.value === flowId) newFlow();
  await loadFlows();
}

function onModelPick(jobId) {
  const job = completedJobs.value.find((j) => j.job_id === jobId);
  if (!job || !selectedNode.value) return;
  selectedNode.value.data.job_id = job.job_id;
  selectedNode.value.data.model_key = job.model_key;
}

// ---------- Tab B: CCTV devices ----------
const devices = ref([]);
const deviceForm = ref({ device_name: "", rtsp_url: "", username: "", password: "", bound_flow_id: null });
const testingId = ref(null);
const testResults = ref({});

async function loadDevices() {
  const { data } = await axios.get("/api/pipeline/devices", { withCredentials: true });
  devices.value = data;
}

async function addDevice() {
  const payload = { ...deviceForm.value };
  if (!payload.bound_flow_id) payload.bound_flow_id = null;
  await axios.post("/api/pipeline/devices", payload, { withCredentials: true });
  deviceForm.value = { device_name: "", rtsp_url: "", username: "", password: "", bound_flow_id: null };
  await loadDevices();
}

async function removeDevice(deviceId) {
  await axios.delete(`/api/pipeline/devices/${deviceId}`, { withCredentials: true });
  await loadDevices();
}

async function testSnapshot(deviceId) {
  testingId.value = deviceId;
  try {
    const { data } = await axios.post(`/api/pipeline/devices/${deviceId}/snapshot-test`, null, { withCredentials: true });
    testResults.value = { ...testResults.value, [deviceId]: data };
  } finally {
    testingId.value = null;
    await loadDevices();
  }
}

function flowName_(flowId) {
  return flows.value.find((f) => f.flow_id === flowId)?.name || "—";
}

const statusBadge = { active: "badge-success", inactive: "badge-neutral", error: "badge-danger" };
const statusLabel = { active: "正常", inactive: "未測試", error: "連線失敗" };

onMounted(async () => {
  await Promise.all([loadFlows(), loadCompletedJobs(), loadDevices()]);
});
</script>

<template>
  <div class="page-header">
    <h1>邏輯編排 / RTSP 設備管理</h1>
    <p class="subtitle">拖拉節點組出偵測邏輯，並管理攝影機連線</p>
  </div>

  <div class="segmented tabs-lg">
    <button type="button" :class="{ active: activeTab === 'flow' }" @click="activeTab = 'flow'">邏輯編排</button>
    <button type="button" :class="{ active: activeTab === 'device' }" @click="activeTab = 'device'">CCTV 設備管理</button>
  </div>

  <template v-if="activeTab === 'flow'">
    <div class="card" style="padding: 14px 20px">
      <div class="toolbar">
        <div class="field" style="min-width: 200px">
          <label>目前編輯的流程</label>
          <select :value="selectedFlowId" @change="(e) => { const f = flows.find(x => x.flow_id === e.target.value); if (f) loadFlowIntoEditor(f); else newFlow(); }">
            <option value="">(新流程，尚未儲存)</option>
            <option v-for="f in flows" :key="f.flow_id" :value="f.flow_id">{{ f.name }}</option>
          </select>
        </div>
        <div class="field" style="min-width: 160px">
          <label>流程名稱</label>
          <input v-model="flowName" placeholder="流程名稱" />
        </div>
        <button @click="newFlow">新增流程</button>
        <button class="primary" :disabled="saving" @click="saveFlow">{{ saving ? "儲存中..." : "儲存流程" }}</button>
        <button v-if="selectedFlowId" class="danger" @click="deleteFlow(selectedFlowId)">刪除此流程</button>
        <span v-if="saveMessage" class="hint">{{ saveMessage }}</span>
      </div>
    </div>

    <div class="card" style="padding: 14px 20px">
      <div class="toolbar">
        <span class="hint" style="margin-right: 4px">新增節點：</span>
        <button @click="addNode('input')">+ 輸入節點</button>
        <button @click="addNode('detect')">+ 圖像偵測節點</button>
        <button @click="addNode('logic')">+ 邏輯節點</button>
        <button @click="addNode('output')">+ 輸出節點</button>
      </div>
    </div>

    <div class="flow-layout">
      <div class="card flow-canvas-card">
        <VueFlow v-model:nodes="nodes" v-model:edges="edges" fit-view-on-init :default-viewport="{ zoom: 1 }">
        </VueFlow>
      </div>

      <div class="card node-editor">
        <h3>節點設定</h3>
        <div v-if="!selectedNode" class="empty-state">點一個節點來編輯參數</div>
        <div v-else>
          <template v-if="selectedNode.data.kind === 'input'">
            <div class="field">
              <label>模型（來自 Page4 已完成的訓練任務）</label>
              <select :value="selectedNode.data.job_id" @change="(e) => onModelPick(e.target.value)">
                <option value="" disabled>選擇模型</option>
                <option v-for="j in completedJobs" :key="j.job_id" :value="j.job_id">
                  {{ j.model_key }} ({{ j.job_id.slice(0, 8) }})
                </option>
              </select>
            </div>
          </template>

          <template v-else-if="selectedNode.data.kind === 'detect'">
            <div class="field">
              <label>目標類別名稱</label>
              <input v-model="selectedNode.data.target_class" placeholder="例如 wire" />
            </div>
            <div class="field">
              <label>信心門檻</label>
              <input v-model.number="selectedNode.data.confidence_threshold" type="number" step="0.05" min="0" max="1" />
            </div>
          </template>

          <template v-else-if="selectedNode.data.kind === 'logic'">
            <div class="field">
              <label>邏輯類型</label>
              <select v-model="selectedNode.data.logic_type">
                <option value="and">AND</option>
                <option value="or">OR</option>
                <option value="count_threshold">計數閾值</option>
                <option value="roi">區域內偵測 (ROI)</option>
                <option value="duration">時間持續判斷</option>
              </select>
            </div>
            <div class="field" v-if="selectedNode.data.logic_type === 'count_threshold'">
              <label>數量閾值</label>
              <input v-model.number="selectedNode.data.threshold" type="number" min="1" />
            </div>
            <template v-if="selectedNode.data.logic_type === 'roi'">
              <div class="field"><label>ROI X</label><input v-model.number="selectedNode.data.roi_x" type="number" /></div>
              <div class="field"><label>ROI Y</label><input v-model.number="selectedNode.data.roi_y" type="number" /></div>
              <div class="field"><label>ROI 寬</label><input v-model.number="selectedNode.data.roi_w" type="number" /></div>
              <div class="field"><label>ROI 高</label><input v-model.number="selectedNode.data.roi_h" type="number" /></div>
            </template>
            <div class="field" v-if="selectedNode.data.logic_type === 'duration'">
              <label>持續秒數</label>
              <input v-model.number="selectedNode.data.duration_sec" type="number" min="0" />
            </div>
          </template>

          <template v-else-if="selectedNode.data.kind === 'output'">
            <div class="field">
              <label>輸出類型</label>
              <select v-model="selectedNode.data.output_type">
                <option value="alarm">觸發 Alarm</option>
                <option value="webhook">Webhook</option>
                <option value="db">寫入資料庫</option>
              </select>
            </div>
            <div class="field" v-if="selectedNode.data.output_type === 'webhook'">
              <label>Webhook URL</label>
              <input v-model="selectedNode.data.webhook_url" placeholder="https://..." />
            </div>
          </template>

          <button class="danger" style="margin-top: 10px" @click="deleteSelectedNode">刪除此節點</button>
        </div>
      </div>
    </div>
  </template>

  <template v-else>
    <div class="card">
      <h2>新增設備</h2>
      <div class="toolbar">
        <input v-model="deviceForm.device_name" placeholder="設備名稱" style="width: 140px" />
        <input v-model="deviceForm.rtsp_url" placeholder="rtsp://host:554/stream" style="flex: 1; min-width: 220px" />
        <input v-model="deviceForm.username" placeholder="帳號(選填)" style="width: 120px" />
        <input v-model="deviceForm.password" type="password" placeholder="密碼(選填)" style="width: 120px" />
        <select v-model="deviceForm.bound_flow_id">
          <option :value="null">不綁定流程</option>
          <option v-for="f in flows" :key="f.flow_id" :value="f.flow_id">{{ f.name }}</option>
        </select>
        <button class="primary" :disabled="!deviceForm.device_name || !deviceForm.rtsp_url" @click="addDevice">新增</button>
      </div>
    </div>

    <div class="card">
      <h2>設備清單</h2>
      <table v-if="devices.length">
        <thead>
          <tr><th>名稱</th><th>RTSP</th><th>綁定流程</th><th>狀態</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="d in devices" :key="d.device_id">
            <td>{{ d.device_name }}</td>
            <td class="mono">{{ d.rtsp_url }}</td>
            <td>{{ flowName_(d.bound_flow_id) }}</td>
            <td><span class="badge" :class="statusBadge[d.status]">{{ statusLabel[d.status] || d.status }}</span></td>
            <td class="row-actions">
              <button :disabled="testingId === d.device_id" @click="testSnapshot(d.device_id)">
                {{ testingId === d.device_id ? "測試中..." : "截圖測試" }}
              </button>
              <button class="danger" @click="removeDevice(d.device_id)">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">尚未新增任何設備。</div>

      <div v-for="(result, deviceId) in testResults" :key="deviceId" class="snapshot-result">
        <template v-if="result.ok">
          <p class="hint">{{ devices.find((d) => d.device_id === deviceId)?.device_name }} 截圖成功：</p>
          <img :src="result.snapshot_url" class="snapshot-img" />
        </template>
        <template v-else>
          <p class="error-text">{{ devices.find((d) => d.device_id === deviceId)?.device_name }} 截圖失敗：{{ result.error }}</p>
        </template>
      </div>
    </div>
  </template>
</template>

<style>
/* Vue Flow requires its own styles unscoped */
.vue-flow__node {
  white-space: pre-line;
  font-size: 0.78rem;
  text-align: center;
}
</style>

<style scoped>
.tabs-lg { margin-bottom: 20px; }
.flow-layout { display: flex; gap: 16px; }
.flow-canvas-card { flex: 1; padding: 0; overflow: hidden; height: 560px; }
.flow-canvas-card :deep(.vue-flow) { height: 100%; }
.node-editor { width: 280px; flex-shrink: 0; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.8rem; }
.row-actions { display: flex; gap: 6px; }
.snapshot-result { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--color-border); }
.snapshot-img { max-width: 320px; border-radius: var(--radius-sm); border: 1px solid var(--color-border); }
</style>
