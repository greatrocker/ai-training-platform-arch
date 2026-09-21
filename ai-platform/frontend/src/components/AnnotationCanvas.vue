<script setup>
import { ref, onMounted, watch, computed, nextTick } from "vue";

const props = defineProps({
  imageUrl: { type: String, required: true },
  imageWidth: { type: Number, required: true },
  imageHeight: { type: Number, required: true },
  annotations: { type: Array, default: () => [] },
  classes: { type: Array, default: () => [] },
  mode: { type: String, default: "bbox" }, // bbox | polygon
  activeClassId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
  predictions: { type: Array, default: () => [] },
});

const emit = defineEmits(["create", "delete"]);

const canvasRef = ref(null);
const viewportRef = ref(null);
const MAX_WIDTH = 760;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 8;
const baseScale = computed(() => Math.min(1, MAX_WIDTH / props.imageWidth));
const zoom = ref(1);
const scale = computed(() => baseScale.value * zoom.value);
const zoomPercent = computed(() => Math.round(zoom.value * 100));
const canvasWidth = computed(() => Math.round(props.imageWidth * scale.value));
const canvasHeight = computed(() => Math.round(props.imageHeight * scale.value));

function clampZoom(z) {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));
}

function setZoomCentered(newZoom, clientX, clientY) {
  const wrapper = viewportRef.value;
  newZoom = clampZoom(newZoom);
  if (!wrapper || clientX == null) {
    zoom.value = newZoom;
    return;
  }
  const rect = wrapper.getBoundingClientRect();
  const anchorX = clientX - rect.left + wrapper.scrollLeft;
  const anchorY = clientY - rect.top + wrapper.scrollTop;
  const ratio = newZoom / zoom.value;
  zoom.value = newZoom;
  nextTick(() => {
    wrapper.scrollLeft = anchorX * ratio - (clientX - rect.left);
    wrapper.scrollTop = anchorY * ratio - (clientY - rect.top);
  });
}

function zoomIn() {
  setZoomCentered(clampZoom(zoom.value * 1.25));
}

function zoomOut() {
  setZoomCentered(clampZoom(zoom.value / 1.25));
}

function zoomReset() {
  setZoomCentered(1);
}

function onWheel(evt) {
  if (!evt.ctrlKey) return;
  evt.preventDefault();
  const factor = evt.deltaY < 0 ? 1.2 : 1 / 1.2;
  setZoomCentered(zoom.value * factor, evt.clientX, evt.clientY);
}

const image = new Image();
let imageLoaded = false;

let drawing = false;
let startX = 0;
let startY = 0;
let currentRect = null;
let polygonPoints = [];

function classColor(classId) {
  const cls = props.classes.find((c) => c.class_id === classId);
  return cls?.color || "#00d4ff";
}

function classLabel(classId) {
  return props.classes.find((c) => c.class_id === classId)?.class_name || `#${classId}`;
}

function redraw() {
  const canvas = canvasRef.value;
  if (!canvas || !imageLoaded) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

  for (const ann of props.annotations) {
    ctx.strokeStyle = classColor(ann.class_id);
    ctx.lineWidth = 2;
    ctx.font = "12px sans-serif";
    ctx.fillStyle = classColor(ann.class_id);

    if (ann.shape_type === "bbox") {
      const x = ann.bbox_x * scale.value;
      const y = ann.bbox_y * scale.value;
      const w = ann.bbox_w * scale.value;
      const h = ann.bbox_h * scale.value;
      ctx.strokeRect(x, y, w, h);
      ctx.fillText(classLabel(ann.class_id), x + 2, y - 4 < 10 ? y + 12 : y - 4);
    } else if (ann.shape_type === "polygon" && ann.polygon_points) {
      const pts = JSON.parse(ann.polygon_points);
      ctx.beginPath();
      pts.forEach(([px, py], i) => {
        const sx = px * scale.value;
        const sy = py * scale.value;
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      });
      ctx.closePath();
      ctx.stroke();
    }
  }

  for (const pred of props.predictions) {
    ctx.strokeStyle = "#ffb020";
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.font = "12px sans-serif";
    ctx.fillStyle = "#ffb020";

    const label = `${classLabel(pred.class_id)} ${Math.round((pred.confidence || 0) * 100)}%`;
    if (pred.shape_type === "bbox") {
      const x = pred.bbox_x * scale.value;
      const y = pred.bbox_y * scale.value;
      const w = pred.bbox_w * scale.value;
      const h = pred.bbox_h * scale.value;
      ctx.strokeRect(x, y, w, h);
      ctx.fillText(label, x + 2, y - 4 < 10 ? y + 12 : y - 4);
    } else if (pred.shape_type === "polygon" && pred.polygon_points) {
      const pts = pred.polygon_points;
      ctx.beginPath();
      pts.forEach(([px, py], i) => {
        const sx = px * scale.value;
        const sy = py * scale.value;
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      });
      ctx.closePath();
      ctx.stroke();
      if (pts.length) ctx.fillText(label, pts[0][0] * scale.value + 2, pts[0][1] * scale.value - 4);
    }
    ctx.setLineDash([]);
  }

  if (currentRect) {
    ctx.strokeStyle = "#ffffff";
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h);
    ctx.setLineDash([]);
  }

  if (polygonPoints.length) {
    ctx.strokeStyle = "#ffffff";
    ctx.beginPath();
    polygonPoints.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
    ctx.stroke();
    polygonPoints.forEach(([x, y]) => {
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
    });
  }
}

function loadImage() {
  imageLoaded = false;
  image.onload = () => {
    imageLoaded = true;
    redraw();
  };
  image.src = props.imageUrl;
}

onMounted(loadImage);
watch(() => props.imageUrl, loadImage);
watch(() => [props.annotations, props.classes, props.predictions], redraw, { deep: true });

function pos(evt) {
  const rect = canvasRef.value.getBoundingClientRect();
  return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
}

function onMouseDown(evt) {
  if (props.readonly || props.mode !== "bbox" || props.activeClassId == null) return;
  const p = pos(evt);
  drawing = true;
  startX = p.x;
  startY = p.y;
  currentRect = { x: p.x, y: p.y, w: 0, h: 0 };
}

function onMouseMove(evt) {
  if (!drawing) return;
  const p = pos(evt);
  currentRect = {
    x: Math.min(startX, p.x),
    y: Math.min(startY, p.y),
    w: Math.abs(p.x - startX),
    h: Math.abs(p.y - startY),
  };
  redraw();
}

function onMouseUp() {
  if (!drawing) return;
  drawing = false;
  if (currentRect && currentRect.w > 4 && currentRect.h > 4) {
    emit("create", {
      shape_type: "bbox",
      class_id: props.activeClassId,
      bbox_x: currentRect.x / scale.value,
      bbox_y: currentRect.y / scale.value,
      bbox_w: currentRect.w / scale.value,
      bbox_h: currentRect.h / scale.value,
    });
  }
  currentRect = null;
  redraw();
}

function onClick(evt) {
  if (props.readonly || props.mode !== "polygon" || props.activeClassId == null) return;
  const p = pos(evt);
  polygonPoints.push([p.x, p.y]);
  redraw();
}

function onDblClick() {
  if (props.readonly || props.mode !== "polygon" || polygonPoints.length < 3) return;
  const imgPoints = polygonPoints.map(([x, y]) => [x / scale.value, y / scale.value]);
  emit("create", {
    shape_type: "polygon",
    class_id: props.activeClassId,
    polygon_points: JSON.stringify(imgPoints),
  });
  polygonPoints = [];
  redraw();
}

function cancelPolygon() {
  polygonPoints = [];
  redraw();
}

defineExpose({ cancelPolygon });
</script>

<template>
  <div>
    <div class="zoom-toolbar">
      <button type="button" @click="zoomOut" title="縮小">－</button>
      <span class="zoom-pct">{{ zoomPercent }}%</span>
      <button type="button" @click="zoomIn" title="放大">＋</button>
      <button type="button" @click="zoomReset" title="回到符合寬度">重置</button>
      <span class="hint zoom-hint">（Ctrl + 滾輪也可以縮放；放大後直接在圖上拖動滾動）</span>
    </div>
    <div ref="viewportRef" class="canvas-viewport" @wheel="onWheel">
      <canvas
        ref="canvasRef"
        :width="canvasWidth"
        :height="canvasHeight"
        class="annotation-canvas"
        :class="{ 'is-readonly': readonly }"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @click="onClick"
        @dblclick="onDblClick"
      />
    </div>
    <p v-if="!readonly && mode === 'polygon'" class="hint">多邊形模式：依序點擊加點，雙擊結束並儲存。</p>
    <p v-if="readonly && predictions.length" class="hint legend">
      <span class="swatch swatch-truth"></span> 人工標註
      <span class="swatch swatch-pred"></span> 模型預測
    </p>
  </div>
</template>

<style scoped>
.zoom-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.zoom-toolbar button {
  padding: 2px 10px;
  line-height: 1.6;
}
.zoom-pct {
  min-width: 3.5em;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 0.85rem;
}
.zoom-hint {
  margin: 0;
  margin-left: 4px;
}
.canvas-viewport {
  max-width: 100%;
  max-height: 70vh;
  overflow: auto;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}
.annotation-canvas {
  cursor: crosshair;
  display: block;
}
.hint {
  margin-top: 8px;
}
.annotation-canvas.is-readonly {
  cursor: default;
}
.legend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85em;
  color: var(--color-text-muted, #888);
}
.swatch {
  display: inline-block;
  width: 14px;
  height: 3px;
  border-radius: 2px;
}
.swatch-truth {
  background: #00d4ff;
}
.swatch-pred {
  background: #ffb020;
  border-top: 1px dashed #ffb020;
}
</style>
