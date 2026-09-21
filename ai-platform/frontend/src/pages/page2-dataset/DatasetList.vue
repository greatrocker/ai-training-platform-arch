<script setup>
import { ref, onMounted, onUnmounted, computed } from "vue";
import axios from "axios";

const datasets = ref([]);
const form = ref({ name: "", source_type: "image_folder", source_path: "", frame_interval_sec: 1, filename_pattern: "" });
const creating = ref(false);
const createError = ref("");
const loadingDatasets = ref(true);

const selectedDatasetId = ref(null);
const assets = ref([]);
const assetsLoading = ref(false);

let pollTimer = null;

async function loadDatasets() {
  const { data } = await axios.get("/api/dataset", { withCredentials: true });
  datasets.value = data;
  loadingDatasets.value = false;
}

function schedulePoll() {
  const hasActive = datasets.value.some((d) => d.status === "pending" || d.status === "processing");
  if (pollTimer) clearTimeout(pollTimer);
  if (hasActive) {
    pollTimer = setTimeout(async () => {
      await loadDatasets();
      schedulePoll();
    }, 3000);
  }
}

async function createDataset() {
  createError.value = "";
  creating.value = true;
  try {
    const payload = { name: form.value.name, source_type: form.value.source_type, source_path: form.value.source_path };
    if (form.value.source_type === "video") {
      payload.frame_interval_sec = Number(form.value.frame_interval_sec) || 1;
    } else if (form.value.filename_pattern) {
      payload.filename_pattern = form.value.filename_pattern;
    }
    await axios.post("/api/dataset", payload, { withCredentials: true });
    form.value.name = "";
    form.value.source_path = "";
    await loadDatasets();
    schedulePoll();
  } catch (err) {
    createError.value = err.response?.data?.detail || "建立失敗";
  } finally {
    creating.value = false;
  }
}

async function viewAssets(datasetId) {
  selectedDatasetId.value = datasetId;
  assetsLoading.value = true;
  try {
    const { data } = await axios.get(`/api/dataset/${datasetId}/assets`, { withCredentials: true });
    assets.value = data;
  } finally {
    assetsLoading.value = false;
  }
}

async function removeDataset(datasetId) {
  await axios.delete(`/api/dataset/${datasetId}`, { withCredentials: true });
  if (selectedDatasetId.value === datasetId) {
    selectedDatasetId.value = null;
    assets.value = [];
  }
  await loadDatasets();
}

const statusLabel = { pending: "等待中", processing: "處理中", ready: "已完成", failed: "失敗" };
const statusBadge = { pending: "badge-neutral", processing: "badge-info", ready: "badge-success", failed: "badge-danger" };
const sourceTypeLabel = { image_folder: "圖片資料夾", video: "影片" };

const selectedDataset = computed(() => datasets.value.find((d) => d.dataset_id === selectedDatasetId.value));

onMounted(async () => {
  await loadDatasets();
  schedulePoll();
});

onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer);
});
</script>

<template>
  <div class="page-header">
    <h1>資料集匯入</h1>
    <p class="subtitle">匯入影片或圖片資料夾，自動抽幀 / 正規化並產生縮圖</p>
  </div>

  <div class="card">
    <h2>新增資料集</h2>
    <div class="toolbar">
      <input v-model="form.name" placeholder="資料集名稱" style="min-width: 160px" />
      <select v-model="form.source_type">
        <option value="image_folder">圖片資料夾</option>
        <option value="video">影片</option>
      </select>
      <input v-model="form.source_path" placeholder="Windows 路徑，例如 D:\Videos\lineA" style="flex: 1; min-width: 220px" />
      <input
        v-if="form.source_type === 'video'"
        v-model="form.frame_interval_sec"
        type="number"
        min="1"
        placeholder="抽幀間隔(秒)"
        style="width: 8em"
      />
      <input
        v-else
        v-model="form.filename_pattern"
        placeholder="檔名篩選(選填)，例如 *Stitch_Img*"
        style="width: 16em"
      />
      <button class="primary" :disabled="creating || !form.name || !form.source_path" @click="createDataset">
        {{ creating ? "建立中..." : "建立" }}
      </button>
    </div>
    <p class="hint">
      直接輸入 Windows 路徑即可，例如 <code>C:\Users\servi\Videos\lineA</code> 或 <code>D:\dataset\lineA</code>。
      會遞迴掃描所有子資料夾；圖片資料夾類型可選填「檔名篩選」（萬用字元，例如 <code>*Stitch_Img*</code>）只匯入符合的檔名。
      目前只掛載了 <code>C:</code> 槽（見 <code>.env</code> 的 <code>WINDOWS_DRIVE_MOUNTS</code>），其他槽要先加進
      <code>docker-compose.yml</code> 才能使用。
    </p>
    <p v-if="createError" class="error-text">{{ createError }}</p>
  </div>

  <div class="card">
    <h2>資料集清單</h2>
    <table v-if="datasets.length">
      <thead>
        <tr>
          <th>名稱</th>
          <th>類型</th>
          <th>狀態</th>
          <th>檔案數</th>
          <th>建立者</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in datasets" :key="d.dataset_id" :class="{ 'row-selected': d.dataset_id === selectedDatasetId }">
          <td>{{ d.name }}</td>
          <td>{{ sourceTypeLabel[d.source_type] || d.source_type }}</td>
          <td><span class="badge" :class="statusBadge[d.status]">{{ statusLabel[d.status] || d.status }}</span></td>
          <td>{{ d.asset_count }}</td>
          <td>{{ d.created_by }}</td>
          <td class="row-actions">
            <button :disabled="d.status !== 'ready'" @click="viewAssets(d.dataset_id)">預覽</button>
            <button class="danger" @click="removeDataset(d.dataset_id)">刪除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else-if="!loadingDatasets" class="empty-state">尚未建立任何資料集，用上面的表單新增一個吧。</div>
  </div>

  <div class="card" v-if="selectedDatasetId">
    <h2>縮圖預覽{{ selectedDataset ? ` — ${selectedDataset.name}` : "" }}</h2>
    <p v-if="assetsLoading" class="hint">載入中...</p>
    <div v-else-if="!assets.length" class="empty-state">這個資料集沒有檔案。</div>
    <div v-else class="thumb-grid">
      <div v-for="a in assets" :key="a.asset_id" class="thumb">
        <img :src="a.thumb_url" :title="`${a.width}x${a.height}`" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.row-selected { background: var(--color-primary-soft); }
.row-actions { display: flex; gap: 6px; }
.thumb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.thumb {
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface-alt);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.2s;
}
.thumb:hover img {
  transform: scale(1.06);
}
</style>
