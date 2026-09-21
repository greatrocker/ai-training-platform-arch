<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import axios from "axios";
import AnnotationCanvas from "../../components/AnnotationCanvas.vue";

const datasets = ref([]);
const selectedDatasetId = ref("");
const activeTab = ref("annotate");

const schema = ref({ classes: [] });
const newClassName = ref("");
const newClassColor = ref("#ff3366");

const assets = ref([]);
const selectedAsset = ref(null);
const annotations = ref([]);
const activeClassId = ref(null);
const shapeMode = ref("bbox");

const reviewQueue = ref([]);

const demos = ref([]);
const demoForm = ref({ class_id: null, bbox_x: 0, bbox_y: 0, bbox_w: 50, bbox_h: 50, text_description: "", file: null });

const exportResult = ref(null);
const exporting = ref(false);

const bootstrapRunning = ref(false);
const bootstrapResult = ref(null);
const bootstrapProgress = ref(null);
const bootstrapConfThreshold = ref(0.15);
let bootstrapPollTimer = null;

async function loadDatasets() {
  const { data } = await axios.get("/api/dataset", { params: { status: "ready" }, withCredentials: true });
  datasets.value = data;
  if (!selectedDatasetId.value && data.length) selectedDatasetId.value = data[0].dataset_id;
}

async function loadSchema() {
  if (!selectedDatasetId.value) return;
  const { data } = await axios.get(`/api/annotation/schema/${selectedDatasetId.value}`, { withCredentials: true });
  schema.value = data;
  if (!activeClassId.value && data.classes.length) activeClassId.value = data.classes[0].class_id;
}

async function loadAssets() {
  if (!selectedDatasetId.value) return;
  const { data } = await axios.get(`/api/dataset/${selectedDatasetId.value}/assets`, { withCredentials: true });
  assets.value = data;
}

async function addClass() {
  if (!newClassName.value) return;
  await axios.post(
    `/api/annotation/schema/${selectedDatasetId.value}/classes`,
    { class_name: newClassName.value, color: newClassColor.value, display_order: schema.value.classes.length },
    { withCredentials: true }
  );
  newClassName.value = "";
  await loadSchema();
}

async function selectAsset(asset) {
  selectedAsset.value = asset;
  const { data } = await axios.get(`/api/annotation/assets/${asset.asset_id}`, { withCredentials: true });
  annotations.value = data;
}

const currentAssetIndex = computed(() =>
  assets.value.findIndex((a) => a.asset_id === selectedAsset.value?.asset_id)
);
const hasPrevAsset = computed(() => currentAssetIndex.value > 0);
const hasNextAsset = computed(
  () => currentAssetIndex.value >= 0 && currentAssetIndex.value < assets.value.length - 1
);

function goToPrevAsset() {
  if (hasPrevAsset.value) selectAsset(assets.value[currentAssetIndex.value - 1]);
}

function goToNextAsset() {
  if (hasNextAsset.value) selectAsset(assets.value[currentAssetIndex.value + 1]);
}

function onKeydownNav(evt) {
  if (activeTab.value !== "annotate" || !selectedAsset.value) return;
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  if (evt.key === "ArrowLeft") goToPrevAsset();
  else if (evt.key === "ArrowRight") goToNextAsset();
}

async function createAnnotation(shape) {
  const { data } = await axios.post(`/api/annotation/assets/${selectedAsset.value.asset_id}`, shape, {
    withCredentials: true,
  });
  annotations.value.push(data);
}

async function deleteAnnotation(id) {
  await axios.delete(`/api/annotation/${id}`, { withCredentials: true });
  annotations.value = annotations.value.filter((a) => a.annotation_id !== id);
}

function classById(id) {
  return schema.value.classes.find((c) => c.class_id === id);
}

async function loadReviewQueue() {
  if (!assets.value.length) await loadAssets();
  const ids = assets.value.map((a) => a.asset_id).join(",");
  if (!ids) {
    reviewQueue.value = [];
    return;
  }
  const { data } = await axios.get("/api/annotation/review-queue", {
    params: { dataset_asset_ids: ids },
    withCredentials: true,
  });
  reviewQueue.value = data;
}

function assetThumb(assetId) {
  return assets.value.find((a) => a.asset_id === assetId)?.thumb_url;
}

async function reviewDecision(annotationId, decision) {
  await axios.post(
    `/api/annotation/${annotationId}/review`,
    { decision },
    { withCredentials: true }
  );
  reviewQueue.value = reviewQueue.value.filter((a) => a.annotation_id !== annotationId);
}

async function loadDemos() {
  if (!selectedDatasetId.value) return;
  const { data } = await axios.get("/api/annotation/demos", {
    params: { dataset_id: selectedDatasetId.value },
    withCredentials: true,
  });
  demos.value = data;
}

function onDemoFileChange(evt) {
  demoForm.value.file = evt.target.files[0] || null;
}

async function submitDemo() {
  if (!demoForm.value.file || !demoForm.value.class_id) return;
  const fd = new FormData();
  fd.append("dataset_id", selectedDatasetId.value);
  fd.append("class_id", demoForm.value.class_id);
  fd.append("bbox_x", demoForm.value.bbox_x);
  fd.append("bbox_y", demoForm.value.bbox_y);
  fd.append("bbox_w", demoForm.value.bbox_w);
  fd.append("bbox_h", demoForm.value.bbox_h);
  fd.append("text_description", demoForm.value.text_description);
  fd.append("image", demoForm.value.file);
  await axios.post("/api/annotation/demos", fd, { withCredentials: true });
  demoForm.value = { class_id: null, bbox_x: 0, bbox_y: 0, bbox_w: 50, bbox_h: 50, text_description: "", file: null };
  await loadDemos();
}

async function removeDemo(demoId) {
  await axios.delete(`/api/annotation/demos/${demoId}`, { withCredentials: true });
  await loadDemos();
}

async function runExport(format) {
  exporting.value = true;
  exportResult.value = null;
  try {
    const { data } = await axios.post(`/api/annotation/export/${selectedDatasetId.value}`, null, {
      params: { format },
      withCredentials: true,
    });
    exportResult.value = data;
  } finally {
    exporting.value = false;
  }
}

async function runBootstrapLabel() {
  bootstrapRunning.value = true;
  bootstrapResult.value = null;
  bootstrapProgress.value = null;
  const { data } = await axios.post(`/api/training/bootstrap-label/${selectedDatasetId.value}`, null, {
    params: { conf_threshold: bootstrapConfThreshold.value },
    withCredentials: true,
  });
  pollBootstrapTask(data.task_id);
}

function bootstrapProgressPercent() {
  const p = bootstrapProgress.value;
  if (!p) return null;
  if (p.phase === "training" && p.total_epochs) {
    return Math.min(100, Math.round((p.current_epoch / p.total_epochs) * 100));
  }
  if (p.phase === "scanning" && p.total_images) {
    return Math.min(100, Math.round((p.current_image / p.total_images) * 100));
  }
  return null;
}

function bootstrapProgressLabel() {
  const p = bootstrapProgress.value;
  if (!p) return "排隊中...";
  if (p.phase === "training") return `訓練中 epoch ${p.current_epoch}/${p.total_epochs ?? "?"}`;
  if (p.phase === "scanning") return `掃描未標註圖片 ${p.current_image}/${p.total_images}`;
  return "處理中...";
}

function pollBootstrapTask(taskId) {
  if (bootstrapPollTimer) clearTimeout(bootstrapPollTimer);
  bootstrapPollTimer = setTimeout(async () => {
    const { data } = await axios.get(`/api/training/bootstrap-label/tasks/${taskId}`, { withCredentials: true });
    if (data.state === "PENDING" || data.state === "STARTED" || data.state === "PROGRESS") {
      bootstrapProgress.value = data.progress || null;
      pollBootstrapTask(taskId);
      return;
    }
    bootstrapRunning.value = false;
    bootstrapProgress.value = null;
    bootstrapResult.value = data.result;
    if (data.result?.suggestions_created) {
      await loadReviewQueue();
    }
  }, 3000);
}

watch(selectedDatasetId, async () => {
  selectedAsset.value = null;
  annotations.value = [];
  await Promise.all([loadSchema(), loadAssets()]);
});

watch(activeTab, (tab) => {
  if (tab === "review") loadReviewQueue();
  if (tab === "demos") loadDemos();
});

onMounted(async () => {
  await loadDatasets();
  await Promise.all([loadSchema(), loadAssets()]);
  window.addEventListener("keydown", onKeydownNav);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeydownNav);
});
</script>

<template>
  <div class="page-header">
    <h1>標注</h1>
    <p class="subtitle">畫框 / 多邊形標註、AI 輔助建議審核、Demo 範例、資料集匯出</p>
  </div>

  <div class="card" style="padding: 14px 20px">
    <div class="field" style="max-width: 320px">
      <label>資料集</label>
      <select v-model="selectedDatasetId">
        <option v-for="d in datasets" :key="d.dataset_id" :value="d.dataset_id">{{ d.name }}</option>
      </select>
    </div>
  </div>

  <div class="segmented tabs-lg">
    <button type="button" :class="{ active: activeTab === 'annotate' }" @click="activeTab = 'annotate'">標注</button>
    <button type="button" :class="{ active: activeTab === 'review' }" @click="activeTab = 'review'">
      審核佇列 <span v-if="reviewQueue.length" class="count-pill">{{ reviewQueue.length }}</span>
    </button>
    <button type="button" :class="{ active: activeTab === 'demos' }" @click="activeTab = 'demos'">Demo 範例</button>
    <button type="button" :class="{ active: activeTab === 'export' }" @click="activeTab = 'export'">匯出</button>
  </div>

  <template v-if="activeTab === 'annotate'">
    <div class="card">
      <h3>標籤類別</h3>
      <div class="class-list">
        <label
          v-for="c in schema.classes"
          :key="c.class_id"
          class="class-chip"
          :class="{ active: activeClassId === c.class_id }"
          :style="{ '--chip-color': c.color }"
        >
          <input type="radio" :value="c.class_id" v-model="activeClassId" />
          <span class="dot" :style="{ background: c.color }"></span>
          {{ c.class_name }}
        </label>
        <span v-if="!schema.classes.length" class="hint">尚未建立類別，請在下方新增。</span>
      </div>
      <div class="toolbar">
        <input v-model="newClassName" placeholder="新類別名稱" style="width: 160px" @keyup.enter="addClass" />
        <input v-model="newClassColor" type="color" />
        <button class="primary" @click="addClass">新增類別</button>
        <span class="divider"></span>
        <div class="segmented">
          <button type="button" :class="{ active: shapeMode === 'bbox' }" @click="shapeMode = 'bbox'">Bounding Box</button>
          <button type="button" :class="{ active: shapeMode === 'polygon' }" @click="shapeMode = 'polygon'">Polygon</button>
        </div>
      </div>
    </div>

    <div class="card bootstrap-box">
      <div class="toolbar">
        <button class="primary" :disabled="bootstrapRunning" @click="runBootstrapLabel">
          <span v-if="bootstrapRunning" class="spinner"></span>
          {{ bootstrapRunning ? "訓練/標註中..." : "✨ 半自動標註：用目前標註訓練小模型，自動標剩下的圖" }}
        </button>
        <div class="field-inline">
          信心門檻
          <input v-model.number="bootstrapConfThreshold" type="number" step="0.01" min="0" max="1" style="width: 5em" />
        </div>
      </div>
      <div v-if="bootstrapRunning" class="progress-cell">
        <div class="progress-track">
          <div
            class="progress-fill"
            :style="{ width: (bootstrapProgressPercent() ?? 0) + '%' }"
            :class="{ indeterminate: bootstrapProgressPercent() === null }"
          ></div>
        </div>
        <span class="progress-label">
          {{ bootstrapProgressPercent() !== null ? `${bootstrapProgressPercent()}% — ${bootstrapProgressLabel()}` : bootstrapProgressLabel() }}
        </span>
      </div>
      <p class="hint">
        每次執行都會用「目前所有已核准的標註」重新訓練一個小模型，只標還沒有任何標註的圖，結果會進「審核佇列」讓你核准/打回——審核越多、下次自動標註越準，可以重複執行做增量標註。
        標註範例很少時模型信心分數天生偏低，如果完成後「產生 0 筆建議」，先試著調低信心門檻（例如 0.05）重跑，或多手動標幾張圖再重跑。
      </p>
      <p v-if="bootstrapResult" class="bootstrap-result">
        <span v-if="bootstrapResult.status === 'completed'" class="badge badge-success">
          完成：用 {{ bootstrapResult.trained_on_images }} 張已標註圖片訓練，掃描 {{ bootstrapResult.unlabeled_images_scanned }} 張未標註圖片，用信心門檻 {{ bootstrapResult.conf_threshold_used }} 產生 {{ bootstrapResult.suggestions_created }} 筆待審核建議
        </span>
        <span v-else-if="bootstrapResult.status === 'skipped'" class="badge badge-neutral">
          略過：{{ bootstrapResult.reason }}（請先手動標註至少一張圖）
        </span>
        <span v-else class="badge badge-danger">失敗：{{ bootstrapResult.reason }}</span>
      </p>
    </div>

    <div class="card workspace-card">
      <div class="workspace">
        <div class="asset-grid">
          <div
            v-for="a in assets"
            :key="a.asset_id"
            class="asset-thumb"
            :class="{ selected: selectedAsset?.asset_id === a.asset_id }"
            @click="selectAsset(a)"
          >
            <img :src="a.thumb_url" />
          </div>
          <div v-if="!assets.length" class="empty-state">尚無圖片</div>
        </div>

        <div v-if="selectedAsset" class="canvas-area">
          <div class="nav-bar">
            <button :disabled="!hasPrevAsset" @click="goToPrevAsset">◀ 上一張</button>
            <span class="nav-counter">{{ currentAssetIndex + 1 }} / {{ assets.length }}</span>
            <button :disabled="!hasNextAsset" @click="goToNextAsset">下一張 ▶</button>
            <span class="hint nav-key-hint">（可用鍵盤 ← → 切換）</span>
          </div>
          <AnnotationCanvas
            :image-url="selectedAsset.raw_url"
            :image-width="selectedAsset.width"
            :image-height="selectedAsset.height"
            :annotations="annotations"
            :classes="schema.classes"
            :mode="shapeMode"
            :active-class-id="activeClassId"
            @create="createAnnotation"
          />
          <ul class="ann-list">
            <li v-for="a in annotations" :key="a.annotation_id">
              <span class="dot" :style="{ background: classById(a.class_id)?.color }"></span>
              <span>{{ classById(a.class_id)?.class_name || a.class_id }}</span>
              <span class="badge badge-info" v-if="a.source === 'ai_suggested'">AI 建議 · {{ a.review_status }}</span>
              <button class="ghost danger-hover" @click="deleteAnnotation(a.annotation_id)">刪除</button>
            </li>
            <li v-if="!annotations.length"><span class="hint">這張圖還沒有標註</span></li>
          </ul>
        </div>
        <div v-else class="empty-state canvas-placeholder">從左側選一張圖開始標注</div>
      </div>
    </div>
  </template>

  <div class="card" v-else-if="activeTab === 'review'">
    <h3>AI 建議待審核（依風險分數由高到低）</h3>
    <table v-if="reviewQueue.length">
      <thead>
        <tr><th>縮圖</th><th>類別</th><th>信心分數</th><th>風險分數</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="a in reviewQueue" :key="a.annotation_id">
          <td><img :src="assetThumb(a.asset_id)" class="mini-thumb" /></td>
          <td>
            <span class="dot" :style="{ background: classById(a.class_id)?.color }"></span>
            {{ classById(a.class_id)?.class_name || a.class_id }}
          </td>
          <td>{{ a.confidence?.toFixed(2) }}</td>
          <td>{{ a.risk_score?.toFixed(2) }}</td>
          <td class="row-actions">
            <button class="primary" @click="reviewDecision(a.annotation_id, 'approved')">核准</button>
            <button class="danger" @click="reviewDecision(a.annotation_id, 'rejected')">打回</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty-state">目前沒有待審核的 AI 建議標註。</div>
  </div>

  <template v-else-if="activeTab === 'demos'">
    <div class="card">
      <h3>Demo 範例（Few-shot 輔助標註用）</h3>
      <div class="demo-grid" v-if="demos.length">
        <div v-for="d in demos" :key="d.demo_id" class="demo-card">
          <img :src="d.demo_image_url" />
          <div class="demo-card-body">
            <div class="demo-class">
              <span class="dot" :style="{ background: classById(d.class_id)?.color }"></span>
              {{ classById(d.class_id)?.class_name || d.class_id }}
            </div>
            <p class="hint">{{ d.text_description }}</p>
            <button class="ghost danger-hover" @click="removeDemo(d.demo_id)">刪除</button>
          </div>
        </div>
      </div>
      <div v-else class="empty-state" style="margin-bottom: 8px">尚未上傳任何 Demo 範例。</div>
    </div>

    <div class="card">
      <h3>新增 Demo</h3>
      <div class="toolbar">
        <select v-model="demoForm.class_id">
          <option disabled value="">選擇類別</option>
          <option v-for="c in schema.classes" :key="c.class_id" :value="c.class_id">{{ c.class_name }}</option>
        </select>
        <input type="file" accept="image/*" @change="onDemoFileChange" />
      </div>
      <div class="toolbar">
        <div class="field-inline">x <input v-model.number="demoForm.bbox_x" type="number" style="width: 5em" /></div>
        <div class="field-inline">y <input v-model.number="demoForm.bbox_y" type="number" style="width: 5em" /></div>
        <div class="field-inline">w <input v-model.number="demoForm.bbox_w" type="number" style="width: 5em" /></div>
        <div class="field-inline">h <input v-model.number="demoForm.bbox_h" type="number" style="width: 5em" /></div>
      </div>
      <div class="toolbar">
        <input v-model="demoForm.text_description" placeholder="文字說明，例如：表面刮痕，白色細長線條" style="flex: 1; min-width: 220px" />
        <button class="primary" @click="submitDemo">上傳 Demo</button>
      </div>
      <p class="hint">Demo 建立後，可在「審核佇列」看到之後 AI 輔助標註（需設定 ANNOTATION_VLM_ENDPOINT 才會實際產生建議）。</p>
    </div>
  </template>

  <div class="card" v-else-if="activeTab === 'export'">
    <h3>匯出資料集</h3>
    <div class="toolbar">
      <button class="primary" :disabled="exporting" @click="runExport('yolo')">匯出 YOLO txt</button>
      <button class="primary" :disabled="exporting" @click="runExport('coco')">匯出 COCO json</button>
      <span v-if="exporting" class="spinner"></span>
    </div>
    <p v-if="exportResult" style="margin-top: 12px">
      <span class="badge badge-success">完成</span>
      <a :href="exportResult.download_url" target="_blank" style="margin-left: 8px">下載 zip</a>
      <span class="hint">（1 小時內有效）</span>
    </p>
  </div>
</template>

<style scoped>
.tabs-lg { margin-bottom: 20px; }
.count-pill {
  background: var(--color-danger);
  color: #fff;
  border-radius: 999px;
  font-size: 0.68rem;
  padding: 1px 6px;
  margin-left: 4px;
}

.class-list { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.class-chip {
  --chip-color: var(--color-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1.5px solid var(--color-border);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.class-chip input { display: none; }
.class-chip .dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.class-chip.active { border-color: var(--chip-color); background: var(--color-surface-alt); font-weight: 600; }

.divider { width: 1px; align-self: stretch; background: var(--color-border); margin: 0 4px; }

.bootstrap-box { border-style: dashed; border-color: var(--color-border-strong); background: var(--color-surface-alt); }
.bootstrap-result { margin-top: 10px; margin-bottom: 0; }
.progress-cell { margin-top: 10px; max-width: 360px; }
.progress-track {
  height: 6px;
  border-radius: 999px;
  background: var(--color-border, #333);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--color-primary, #00d4ff);
  transition: width 0.4s ease;
}
.progress-fill.indeterminate {
  width: 30% !important;
  animation: progress-slide 1.2s ease-in-out infinite;
}
.progress-label {
  display: block;
  font-size: 0.75rem;
  color: var(--color-text-secondary, #999);
  margin-top: 3px;
}
@keyframes progress-slide {
  0% { margin-left: -30%; }
  100% { margin-left: 100%; }
}

.workspace-card { padding-bottom: 12px; }
.workspace { display: flex; gap: 18px; }
.asset-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 640px;
  overflow-y: auto;
  width: 128px;
  flex-shrink: 0;
  padding-right: 4px;
}
.asset-thumb {
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-sm);
  border: 2px solid transparent;
  overflow: hidden;
  cursor: pointer;
  background: var(--color-surface-alt);
}
.asset-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.asset-thumb.selected { border-color: var(--color-primary); }
.asset-thumb:hover { border-color: var(--color-border-strong); }
.asset-thumb.selected:hover { border-color: var(--color-primary); }

.canvas-area { flex: 1; min-width: 0; }
.nav-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.nav-counter { font-weight: 600; font-variant-numeric: tabular-nums; }
.nav-key-hint { margin-left: auto; }
.canvas-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; }
.ann-list { list-style: none; padding: 0; margin-top: 12px; display: flex; flex-direction: column; gap: 6px; }
.ann-list li { display: flex; gap: 8px; align-items: center; padding: 4px 0; font-size: 0.85rem; }
.ann-list li .dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.ann-list li button { margin-left: auto; }

.row-actions { display: flex; gap: 6px; }
.mini-thumb { width: 60px; height: 45px; object-fit: cover; border-radius: 4px; }
td .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }

.demo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; }
.demo-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface-alt);
}
.demo-card img { width: 100%; aspect-ratio: 4/3; object-fit: cover; display: block; }
.demo-card-body { padding: 10px; }
.demo-class { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 0.85rem; margin-bottom: 4px; }
.demo-class .dot { width: 8px; height: 8px; border-radius: 50%; }

.danger-hover:hover { color: var(--color-danger); background: var(--color-danger-soft); }

.spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  vertical-align: -2px;
}
.bootstrap-box .spinner {
  border-color: var(--color-border-strong);
  border-top-color: var(--color-text-secondary);
}
.export-card .spinner {
  border-color: var(--color-border-strong);
  border-top-color: var(--color-text-secondary);
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
