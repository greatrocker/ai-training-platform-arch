<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import axios from "axios";
import AnnotationCanvas from "../../components/AnnotationCanvas.vue";

const datasets = ref([]);
const selectedDatasetId = ref("");

const taskType = ref("detect");
const models = ref([]);

const form = ref({
  model_key: "",
  epochs: 100,
  batch_size: 16,
  img_size: 640,
  learning_rate: 0.01,
  optimizer: "SGD",
  pretrained: true,
  device: "auto",
  patience: 30,
  training_mode: "full",
  base_job_id: null,
  freeze_backbone: false,
});

const jobs = ref([]);
const creating = ref(false);
const createError = ref("");
let pollTimer = null;

async function loadDatasets() {
  const { data } = await axios.get("/api/dataset", { params: { status: "ready" }, withCredentials: true });
  datasets.value = data;
  if (!selectedDatasetId.value && data.length) selectedDatasetId.value = data[0].dataset_id;
}

async function loadModels() {
  const { data } = await axios.get("/api/training/models", { params: { task_type: taskType.value }, withCredentials: true });
  models.value = data;
  if (data.length) form.value.model_key = data[0].model_key;
}

async function loadJobs() {
  if (!selectedDatasetId.value) return;
  const { data } = await axios.get("/api/training/jobs", {
    params: { dataset_id: selectedDatasetId.value },
    withCredentials: true,
  });
  jobs.value = data;
  schedulePoll();
}

function schedulePoll() {
  const hasActive = jobs.value.some((j) => j.status === "queued" || j.status === "running");
  if (pollTimer) clearTimeout(pollTimer);
  if (hasActive) {
    pollTimer = setTimeout(loadJobs, 5000);
  }
}

const completedJobsForModel = computed(() =>
  jobs.value.filter((j) => j.status === "completed" && j.model_key === form.value.model_key)
);

async function createJob() {
  createError.value = "";
  creating.value = true;
  try {
    const payload = { dataset_id: selectedDatasetId.value, ...form.value };
    if (form.value.training_mode !== "incremental") payload.base_job_id = null;
    await axios.post("/api/training/jobs", payload, { withCredentials: true });
    await loadJobs();
  } catch (err) {
    createError.value = err.response?.data?.detail || "建立失敗";
  } finally {
    creating.value = false;
  }
}

async function downloadWeights(jobId) {
  const { data } = await axios.get(`/api/training/jobs/${jobId}/download`, { withCredentials: true });
  window.open(data.download_url, "_blank");
}

function metricsSummary(job) {
  if (!job.metrics_json) return "";
  try {
    const m = JSON.parse(job.metrics_json);
    const map50 = m["metrics/mAP50(B)"] ?? m["metrics/mAP50(M)"];
    if (map50 !== undefined) return `mAP50=${Number(map50).toFixed(3)}`;
    if (m.error) return `錯誤: ${m.error}`;
  } catch {
    // ignore
  }
  return "";
}

const statusLabel = { queued: "等待中", running: "訓練中", completed: "已完成", failed: "失敗" };
const statusBadge = { queued: "badge-neutral", running: "badge-info", completed: "badge-success", failed: "badge-danger" };

function progressPercent(job) {
  if (!job.progress_total_epochs) return null;
  return Math.min(100, Math.round((job.progress_current_epoch / job.progress_total_epochs) * 100));
}

// --- 推論測試（丟圖比對標註 vs 模型預測） ---
const testJob = ref(null);
const testSchema = ref({ classes: [] });
const testAssets = ref([]);
const testSelectedAsset = ref(null);
const testResult = ref(null);
const testLoading = ref(false);
const testError = ref("");
const uploadInput = ref(null);
const uploadPreview = ref(null);
const testConfThreshold = ref(0.25);
const lastUploadFile = ref(null);

async function openInferenceTest(job) {
  testJob.value = job;
  testSelectedAsset.value = null;
  testResult.value = null;
  uploadPreview.value = null;
  testError.value = "";
  const [schemaRes, assetsRes] = await Promise.all([
    axios.get(`/api/annotation/schema/${job.dataset_id}`, { withCredentials: true }),
    axios.get(`/api/dataset/${job.dataset_id}/assets`, { withCredentials: true }),
  ]);
  testSchema.value = schemaRes.data;
  testAssets.value = assetsRes.data;
}

function closeInferenceTest() {
  testJob.value = null;
}

async function runPredictOnAsset(asset) {
  testSelectedAsset.value = asset;
  uploadPreview.value = null;
  testResult.value = null;
  testError.value = "";
  testLoading.value = true;
  try {
    const { data } = await axios.post(
      `/api/training/jobs/${testJob.value.job_id}/predict-asset`,
      null,
      { params: { asset_id: asset.asset_id, conf: testConfThreshold.value }, withCredentials: true }
    );
    testResult.value = data;
  } catch (err) {
    testError.value = err.response?.data?.detail || "推論失敗";
  } finally {
    testLoading.value = false;
  }
}

function triggerUpload() {
  uploadInput.value?.click();
}

async function runPredictOnUpload(evt) {
  const file = evt.target.files?.[0];
  if (!file) return;
  lastUploadFile.value = file;
  await predictUpload(file);
  evt.target.value = "";
}

async function predictUpload(file) {
  testSelectedAsset.value = null;
  testResult.value = null;
  testError.value = "";
  testLoading.value = true;
  try {
    const formData = new FormData();
    formData.append("image", file);
    const { data } = await axios.post(
      `/api/training/jobs/${testJob.value.job_id}/predict-upload`,
      formData,
      { params: { conf: testConfThreshold.value }, withCredentials: true }
    );
    testResult.value = data;
    uploadPreview.value = `data:image/*;base64,${data.image_base64}`;
  } catch (err) {
    testError.value = err.response?.data?.detail || "推論失敗";
  } finally {
    testLoading.value = false;
  }
}

function rerunWithNewConf() {
  if (testSelectedAsset.value) runPredictOnAsset(testSelectedAsset.value);
  else if (lastUploadFile.value) predictUpload(lastUploadFile.value);
}

watch(taskType, loadModels);
watch(selectedDatasetId, loadJobs);

onMounted(async () => {
  await Promise.all([loadDatasets(), loadModels()]);
  await loadJobs();
});

onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer);
});
</script>

<template>
  <div class="page-header">
    <h1>模型訓練</h1>
    <p class="subtitle">目前只支援 YOLO26 一般標註（Detect）與 YOLO26-SEG（Segment），其他模型家族之後再加</p>
  </div>

  <div class="card">
    <div class="field" style="max-width: 320px">
      <label>資料集</label>
      <select v-model="selectedDatasetId">
        <option v-for="d in datasets" :key="d.dataset_id" :value="d.dataset_id">{{ d.name }}</option>
      </select>
    </div>
  </div>

  <div class="card">
    <h2>新增訓練任務</h2>

    <div class="segmented">
      <button type="button" :class="{ active: taskType === 'detect' }" @click="taskType = 'detect'">一般標註（Detect）</button>
      <button type="button" :class="{ active: taskType === 'segment' }" @click="taskType = 'segment'">分割標註（YOLO-SEG）</button>
    </div>

    <div class="row">
      <div class="field">
        <label>模型</label>
        <select v-model="form.model_key">
          <option v-for="m in models" :key="m.model_key" :value="m.model_key">{{ m.model_key }}</option>
        </select>
      </div>
      <div class="field"><label>Epochs</label><input v-model.number="form.epochs" type="number" min="1" style="width: 6em" /></div>
      <div class="field"><label>Batch</label><input v-model.number="form.batch_size" type="number" min="1" style="width: 5em" /></div>
      <div class="field"><label>Img Size</label><input v-model.number="form.img_size" type="number" step="32" style="width: 6em" /></div>
    </div>

    <div class="row">
      <div class="field"><label>Learning Rate</label><input v-model.number="form.learning_rate" type="number" step="0.001" style="width: 7em" /></div>
      <div class="field">
        <label>Optimizer</label>
        <select v-model="form.optimizer">
          <option value="SGD">SGD</option>
          <option value="Adam">Adam</option>
          <option value="AdamW">AdamW</option>
        </select>
      </div>
      <div class="field">
        <label>Device</label>
        <select v-model="form.device">
          <option value="auto">auto (GPU)</option>
          <option value="cpu">cpu</option>
        </select>
      </div>
      <div class="field">
        <label>Patience（連續N個epoch無進步就停止，0=不啟用）</label>
        <input v-model.number="form.patience" type="number" min="0" style="width: 6em" />
      </div>
      <label class="field-inline" style="align-self: flex-end; padding-bottom: 7px">
        <input type="checkbox" v-model="form.pretrained" /> 使用預訓練權重
      </label>
    </div>

    <div class="segmented" style="margin-top: 4px">
      <button type="button" :class="{ active: form.training_mode === 'full' }" @click="form.training_mode = 'full'">全新訓練</button>
      <button type="button" :class="{ active: form.training_mode === 'incremental' }" @click="form.training_mode = 'incremental'">增量訓練</button>
    </div>

    <div class="row" v-if="form.training_mode === 'incremental'">
      <div class="field" style="min-width: 260px">
        <label>延續自</label>
        <select v-model="form.base_job_id">
          <option :value="null" disabled>選擇歷史任務</option>
          <option v-for="j in completedJobsForModel" :key="j.job_id" :value="j.job_id">
            {{ j.job_id.slice(0, 8) }}（{{ metricsSummary(j) }}）
          </option>
        </select>
      </div>
      <label class="field-inline" style="align-self: flex-end; padding-bottom: 7px">
        <input type="checkbox" v-model="form.freeze_backbone" /> 凍結 backbone
      </label>
    </div>

    <div class="toolbar" style="margin-top: 14px">
      <button class="primary" :disabled="creating || !form.model_key || !selectedDatasetId" @click="createJob">
        {{ creating ? "建立中..." : "開始訓練" }}
      </button>
      <p v-if="createError" class="error-text" style="margin: 0">{{ createError }}</p>
    </div>
  </div>

  <div class="card">
    <h2>訓練任務</h2>
    <table v-if="jobs.length">
      <thead>
        <tr>
          <th>模型</th>
          <th>模式</th>
          <th>狀態</th>
          <th>指標</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="j in jobs" :key="j.job_id">
          <td>{{ j.model_key }}</td>
          <td>
            {{ j.training_mode === "incremental" ? "增量" : "全新" }}
            <span v-if="j.parent_job_id" class="tag">← {{ j.parent_job_id.slice(0, 8) }}</span>
          </td>
          <td>
            <span class="badge" :class="statusBadge[j.status]">{{ statusLabel[j.status] || j.status }}</span>
            <div v-if="j.status === 'running'" class="progress-cell">
              <div class="progress-track">
                <div
                  class="progress-fill"
                  :style="{ width: (progressPercent(j) ?? 0) + '%' }"
                  :class="{ indeterminate: progressPercent(j) === null }"
                ></div>
              </div>
              <span class="progress-label">
                {{ progressPercent(j) !== null ? `${progressPercent(j)}%（epoch ${j.progress_current_epoch}/${j.progress_total_epochs}）` : "準備中..." }}
              </span>
            </div>
          </td>
          <td>{{ metricsSummary(j) }}</td>
          <td>
            <button v-if="j.status === 'completed'" @click="downloadWeights(j.job_id)">下載權重</button>
            <button v-if="j.status === 'completed'" @click="openInferenceTest(j)">測試推論</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty-state">這個資料集還沒有訓練任務。</div>
  </div>

  <div class="card" v-if="testJob">
    <div class="toolbar" style="justify-content: space-between">
      <h2 style="margin: 0">推論測試 — {{ testJob.model_key }}（{{ testJob.job_id.slice(0, 8) }}）</h2>
      <button @click="closeInferenceTest">關閉</button>
    </div>
    <p class="subtitle">丟一張圖，看模型推論結果；若挑選資料集內的圖片，會同時顯示人工標註做比對。</p>

    <div class="test-layout">
      <div class="test-picker">
        <div class="field-inline" style="margin-bottom: 10px">
          信心門檻
          <input v-model.number="testConfThreshold" type="number" step="0.01" min="0" max="1" style="width: 5em" />
          <button @click="rerunWithNewConf" :disabled="!testSelectedAsset && !lastUploadFile">重新推論</button>
        </div>
        <div class="toolbar">
          <button class="primary" @click="triggerUpload">上傳圖片測試</button>
          <input ref="uploadInput" type="file" accept="image/*" style="display: none" @change="runPredictOnUpload" />
        </div>
        <p class="hint">或從資料集圖片挑選：</p>
        <div class="thumb-grid">
          <img
            v-for="a in testAssets"
            :key="a.asset_id"
            :src="a.thumb_url"
            :class="{ active: testSelectedAsset?.asset_id === a.asset_id }"
            @click="runPredictOnAsset(a)"
          />
        </div>
      </div>

      <div class="test-preview">
        <p v-if="testLoading">推論中...</p>
        <p v-else-if="testError" class="error-text">{{ testError }}</p>
        <AnnotationCanvas
          v-else-if="testResult && testSelectedAsset"
          :image-url="testSelectedAsset.raw_url"
          :image-width="testResult.width"
          :image-height="testResult.height"
          :annotations="testResult.ground_truth"
          :predictions="testResult.predictions"
          :classes="testSchema.classes"
          readonly
        />
        <AnnotationCanvas
          v-else-if="testResult && uploadPreview"
          :image-url="uploadPreview"
          :image-width="testResult.width"
          :image-height="testResult.height"
          :annotations="[]"
          :predictions="testResult.predictions"
          :classes="testSchema.classes"
          readonly
        />
        <div v-else class="empty-state">上傳圖片或挑選左側縮圖以查看推論結果。</div>
        <p v-if="testResult" class="hint">
          本次推論用的信心門檻 {{ testResult.conf_used }}、輸入尺寸 {{ testResult.imgsz_used }}（跟訓練時一致）
        </p>
        <p v-if="testResult && !testResult.predictions.length" class="hint">模型未偵測到任何物件（可以調低左側信心門檻再試，或代表訓練不足）。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row { display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-end; margin-bottom: 14px; }
.segmented { margin-bottom: 16px; }
.test-layout { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 12px; }
.progress-cell { margin-top: 6px; min-width: 180px; }
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
.test-picker { flex: 0 0 220px; }
.test-preview { flex: 1; min-width: 320px; }
.thumb-grid { display: flex; flex-wrap: wrap; gap: 8px; max-height: 480px; overflow-y: auto; }
.thumb-grid img {
  width: 96px;
  height: 72px;
  object-fit: cover;
  border-radius: var(--radius-sm, 4px);
  border: 2px solid transparent;
  cursor: pointer;
}
.thumb-grid img.active {
  border-color: var(--color-accent, #00d4ff);
}
</style>
