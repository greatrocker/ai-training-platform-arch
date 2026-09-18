# AI 訓練 / CCTV 推論平台 — 系統架構設計

## 0. 設計原則

- **低耦合**：每頁對應一個獨立微服務（或至少獨立模組），彼此透過 REST/gRPC + 訊息佇列溝通，禁止直接跨服務讀寫對方資料庫。
- **統一身份**：所有服務透過 API Gateway 驗證 JWT，服務間不重複實作 Auth 邏輯。
- **設定外部化**：所有可變參數（路徑、模型清單、閾值、RTSP 帳密等）一律走 `.env` / ConfigMap / DB 設定表，禁止寫死在程式碼。
- **非同步優先**：影片轉檔、資料集生成、模型訓練都是長時間任務 → 一律丟訊息佇列，前端輪詢或 WebSocket 拿進度。
- **儲存分離**：大檔案（影片/圖片/模型權重）一律進 MinIO，MSSQL 只存 metadata。

---

## 1. 技術選型

| 分類 | 選型 | 理由 |
|---|---|---|
| API Gateway | Kong / Traefik | 統一路由、JWT 驗證、rate limit |
| Auth | Keycloak（OAuth2 + OIDC）| 現成 RBAC、支援 SSO/LDAP 對接工廠 AD |
| 後端框架 | FastAPI（Python）| 與 AI/CV 生態系相容度最高 |
| 前端框架 | Vue3 + Pinia 或 React + Zustand | 元件化，適合多頁籤 SPA |
| 訊息佇列 | Redis + Celery（或 RabbitMQ）| 訓練任務、影片轉檔非同步處理 |
| 物件儲存 | MinIO | S3 相容、地端部署免雲端費用 |
| 關聯式資料庫 | MSSQL | 依需求指定 |
| 即時通訊 | WebSocket（FastAPI + Redis pub/sub）| Dashboard 在線人數、CCTV 告警推播 |
| 影像處理 | OpenCV + FFmpeg | 影片抽幀、RTSP 拉流 |
| 標注引擎 | 自建 Canvas（Konva.js / Fabric.js）或整合 Label Studio | 依標注複雜度決定 |
| 模型訓練 | Ultralytics YOLO11 系列 | 使用者需求指定 |
| 拖拉式邏輯編排 | React Flow / Vue Flow | Page5 節點式邏輯建置 |
| 容器化 | Docker + docker-compose（正式環境可升 K8s）| |
| 監控 | Prometheus + Grafana（選配）| Dashboard 底層數據來源 |

---

## 2. 微服務拆分（對應 8 個頁面）

```
[API Gateway / BFF]
   ├─ auth-service          (Page1 OAuth2)
   ├─ dataset-service        (Page2 影片/圖片 → 資料集)
   ├─ annotation-service     (Page3 標注)
   ├─ training-service       (Page4 模型訓練)
   ├─ pipeline-service       (Page5 邏輯編排 + RTSP設備管理)
   ├─ monitor-service        (Page6 即時監控 + Alarm)
   ├─ rbac-service           (Page7 權限/部門/群組)
   └─ dashboard-service      (Page8 連線監控)

共用基礎設施：
   ├─ MinIO
   ├─ MSSQL
   ├─ Redis (queue + pub/sub + session)
   └─ Celery worker(s)（訓練用需掛 GPU node）
```

各服務各自擁有獨立 DB schema（同一顆 MSSQL 但不同 schema，或不同 database），避免高耦合，服務間資料交換一律走 API。

---

## 3. 各頁面詳細設計

### Page 1｜OAuth2 登入

- 採用 **Authorization Code Flow + PKCE**，由 Keycloak 或自建 auth-service 簽發：
  - `access_token`（短效，15 min）
  - `refresh_token`（長效，存 httpOnly cookie）
- 登入成功後夾帶角色（role）、部門（dept）、群組（group）claim，供後續 Page7 RBAC 判斷。
- ENV 範例：
```env
OAUTH2_ISSUER=https://sso.internal.company.com/realms/ai-platform
OAUTH2_CLIENT_ID=ai-training-frontend
OAUTH2_CLIENT_SECRET=${SECRET_FROM_VAULT}
OAUTH2_REDIRECT_URI=https://ai-platform.local/callback
JWT_ALGO=RS256
```

### Page 2｜資料集匯入

流程：
1. 使用者輸入影片/圖片**資料夾路徑**（本機掛載路徑或 UNC path）。
2. `dataset-service` 建立 `dataset` 記錄（狀態：`pending`），丟一筆任務進 Celery。
3. Worker 執行：
   - 影片 → FFmpeg 依 `frame_interval`（可設定，如每 1 秒/每 N 幀）抽幀。
   - 圖片 → 直接複製 + 格式正規化（統一轉 jpg）。
   - 產出檔案上傳 MinIO：`datasets/{dataset_id}/raw/xxx.jpg`
   - 產生縮圖存 `datasets/{dataset_id}/thumbs/`
4. 狀態更新為 `ready`，前端可跳轉 Page3 標注或列於資料集清單。

MSSQL 核心表：
```sql
CREATE TABLE dataset (
  dataset_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  name NVARCHAR(200),
  source_path NVARCHAR(500),
  source_type VARCHAR(20), -- video / image_folder
  status VARCHAR(20),      -- pending/processing/ready/failed
  created_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

CREATE TABLE dataset_asset (
  asset_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dataset_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES dataset(dataset_id),
  minio_path NVARCHAR(500),
  width INT, height INT,
  frame_index INT NULL
);
```

ENV：
```env
DATASET_FRAME_INTERVAL_SEC=1
DATASET_MAX_UPLOAD_GB=50
MINIO_BUCKET_DATASET=datasets
```

### Page 3｜標注

- 進入方式：從 Page2 完成後跳轉，或頁面下方「資料集清單」直接點選（呼叫 `GET /datasets?status=ready`）。
- 標注工具：Bounding Box / Polygon（依需求可擴充 Segmentation）。
- 標籤類別（class）可於此頁管理，存 `label_schema` 表，一個 dataset 綁一組 schema。
- 儲存：每張圖標注結果即時存 `annotation` 表（JSON 格式，含座標 + class_id）。
- 匯出：支援匯出 **YOLO txt** / **COCO json** 格式，打包成 zip 上傳 MinIO 並提供下載連結。

```sql
CREATE TABLE annotation (
  annotation_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  asset_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES dataset_asset(asset_id),
  class_id INT,
  bbox_x FLOAT, bbox_y FLOAT, bbox_w FLOAT, bbox_h FLOAT,
  shape_type VARCHAR(20), -- bbox/polygon
  polygon_points NVARCHAR(MAX) NULL,
  source VARCHAR(20) DEFAULT 'human',   -- human / ai_suggested
  confidence FLOAT NULL,                -- AI建議時的信心分數
  risk_score FLOAT NULL,                -- 與demo比對後的風險分數，越高越需優先人審
  review_status VARCHAR(20) DEFAULT 'final', -- draft/pending_review/approved/rejected/final
  reviewed_by NVARCHAR(100) NULL,
  reviewed_at DATETIME2 NULL,
  annotated_by NVARCHAR(100),
  updated_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
```

#### 3.1 Demo 範例式 AI 輔助標註（文字說明 + 範例圖 雙重保險）

流程：使用者提供「示範標註」而非只給文字描述，系統依此對整批資料做建議標註，**但一律進入待審狀態，不直接寫入正式資料集**。

**輸入端（使用者提供的兩種保險）**

| 保險機制 | 內容 |
|---|---|
| 範例圖（Demo）| 使用者上傳 1~N 張已標註好的範例圖（圖 + bbox/polygon + class），作為 few-shot 參考 |
| 文字說明 | 針對該類別的文字描述，例如「瑕疵為表面刮痕，白色細長線條，長度通常 > 圖片寬度 5%」 |

兩者一起組成 VLM 的 prompt context：`demo圖 + demo標註座標 + 文字描述 + 待標註圖`，模型輸出建議標註（bbox/polygon + confidence）。

**輸出端（雙重保險降低標錯風險）**

1. **信心分數**：VLM 對每個建議框給 confidence，低於閾值（如 0.6）直接標記 `pending_review` 且排優先審核。
2. **與 Demo 一致性比對（risk_score）**：不只看單張信心，額外計算建議標註跟 demo 範例在「類別分布 / bbox 長寬比 / 面積佔比 / 在畫面中的相對位置」是否落在合理區間內，明顯偏離 demo 特徵的標記為高風險，即使 VLM confidence 高也一樣要人審。
   - `risk_score = f(confidence, demo一致性距離)`，超過閾值強制進 `pending_review`，不可自動 `final`。
3. **人工覆核 UI**：Page3 標註畫面並排顯示「Demo 範例圖＋標註」與「AI 建議標註的待審圖」，方便人眼比對是否符合示範邏輯，審核者可一鍵 `approved`（轉正式標註）或 `rejected`（打回重標）。
4. **審核佇列排序**：預設依 `risk_score` 由高到低排列，讓人工優先看最可能出錯的樣本，而非逐張平均分配注意力。

資料表：

```sql
CREATE TABLE annotation_demo (
  demo_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dataset_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES dataset(dataset_id),
  class_id INT,
  demo_image_path NVARCHAR(500),      -- MinIO 路徑
  demo_annotation_json NVARCHAR(MAX), -- 範例標註座標
  text_description NVARCHAR(1000),    -- 文字說明
  created_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
```

ENV：
```env
ANNOTATION_AI_CONFIDENCE_THRESHOLD=0.6
ANNOTATION_RISK_SCORE_THRESHOLD=0.5
ANNOTATION_VLM_MODEL=qwen2.5-vl-7b   # 或串接雲端 VLM
ANNOTATION_AUTO_APPROVE=false        # 一律 false，強制人工覆核，不開放全自動定案
```

> 這一段跟 Page9 Agent 協同層的關係：Agent 指令中的「幫我標註」只會執行到「產生 `pending_review` 的建議標註」為止，`approved → final` 這一步維持強制人工，呼應先前設計中「標註結果定案」屬於高風險動作、不可由 Agent 自動跳過的原則。



- 表單參數（皆有 default，可被使用者覆蓋）：

| 參數 | Default | 說明 |
|---|---|---|
| epochs | 100 | |
| batch_size | 16 | |
| img_size | 640 | |
| learning_rate | 0.01 | |
| optimizer | SGD | 下拉可選 SGD/Adam/AdamW |
| model_size | yolo11n | 下拉選單見下 |
| pretrained | true | 是否載入預訓練權重 |
| device | auto | GPU 選擇 |

- **模型大小下拉選單**（依大小排序，n→s→m→l→x）：
  `yolo11n / yolo11s / yolo11m / yolo11l / yolo11x`
- 下拉選單支援「新增模型」：後端維護 `model_registry` 表，新增時只要填 `model_key` + `weight_path` + `config_path`，下拉選單即時反映，不需改前端 code（達成低耦合擴充）。

```sql
CREATE TABLE model_registry (
  model_key VARCHAR(50) PRIMARY KEY,   -- e.g. yolo11n
  display_order INT,
  base_weight_path NVARCHAR(500),      -- MinIO path, 預訓練權重
  arch_config_path NVARCHAR(500),
  is_active BIT DEFAULT 1
);

CREATE TABLE training_job (
  job_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dataset_id UNIQUEIDENTIFIER,
  model_key VARCHAR(50),
  params_json NVARCHAR(MAX),
  status VARCHAR(20),   -- queued/running/completed/failed
  output_model_path NVARCHAR(500), -- 輸出 .pt 路徑
  metrics_json NVARCHAR(MAX),
  started_at DATETIME2, finished_at DATETIME2
);
```

- 訓練完成的 `.pt` 統一存放：`models/{job_id}/best.pt`，並回寫 `training_job.output_model_path`，供 Page5 邏輯編排選用。
- ENV：
```env
TRAINING_GPU_DEVICE=0
TRAINING_MAX_CONCURRENT_JOBS=2
MINIO_BUCKET_MODELS=models
MODEL_REGISTRY_DEFAULT=yolo11n
```

#### 4.1 增量學習（Incremental / Continual Learning）

表單新增「訓練模式」下拉：

| 模式 | 說明 |
|---|---|
| `full`（全新訓練）| 從 model_registry 的預訓練權重開始，維持原本流程 |
| `incremental`（增量訓練）| 從**既有已訓練模型**（某次 training_job 的輸出 .pt）繼續訓練，只餵新資料集 |

增量模式下額外參數（皆有 default）：

| 參數 | Default | 說明 |
|---|---|---|
| base_job_id | 無（必選）| 下拉選擇要延續的歷史訓練任務，清單來自 `training_job` 依 model_key 分組 |
| replay_ratio | 0.2 | 從舊資料集中抽樣混入新一輪訓練，避免 catastrophic forgetting（災難性遺忘）|
| freeze_backbone | false | 是否凍結 backbone，只微調 head，加速且降低遺忘風險 |
| lr_incremental | 0.001 | 增量訓練通常用比 full 訓練低的學習率 |

流程差異：
1. Worker 依 `base_job_id` 從 MinIO 抓出對應 `.pt` 當作起始權重（取代預訓練權重）。
2. 若 `replay_ratio > 0`，由 dataset-service 依比例回傳舊資料集抽樣清單，與新資料集合併成訓練清單。
3. 訓練完成後產生**新的** training_job 記錄，並以 `parent_job_id` 指向 base_job_id，形成模型血緣（lineage），方便追溯「這個模型是從哪一版演化來的」。
4. Page4 前端可用時間軸/樹狀圖呈現模型版本演進（同一 model_key 下的多代模型）。

資料表調整：
```sql
ALTER TABLE training_job ADD
  training_mode VARCHAR(20) DEFAULT 'full',   -- full / incremental
  parent_job_id UNIQUEIDENTIFIER NULL,
  replay_ratio FLOAT NULL,
  freeze_backbone BIT NULL;
```

ENV：
```env
INCREMENTAL_DEFAULT_REPLAY_RATIO=0.2
INCREMENTAL_DEFAULT_LR=0.001
```

### Page 5｜CCTV 模型邏輯拖拉編排 + RTSP 設備管理

分兩個 tab，各自獨立元件：

**Tab A：邏輯編排（Node Graph）**
- 使用 React Flow 類元件，節點類型：
  - `輸入節點`：選擇已訓練模型（來自 Page4 model registry）
  - `圖像偵測節點`：物件偵測、分類、變形偵測等
  - `邏輯節點`：AND/OR/計數閾值/區域內偵測(ROI)/時間持續判斷
  - `輸出節點`：觸發 Alarm / Webhook / 寫入資料庫
- 每個節點的參數皆為表單輸入（無需寫 code），存成 JSON DAG：
```sql
CREATE TABLE logic_flow (
  flow_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  name NVARCHAR(200),
  graph_json NVARCHAR(MAX), -- node/edge 定義
  created_by NVARCHAR(100),
  updated_at DATETIME2
);
```

**Tab B：CCTV 設備管理**
- 逐一輸入欄位（皆為 config 化）：
```sql
CREATE TABLE cctv_device (
  device_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  device_name NVARCHAR(100),
  rtsp_url NVARCHAR(500),
  username NVARCHAR(100),
  password_encrypted VARBINARY(MAX),
  bound_flow_id UNIQUEIDENTIFIER NULL,
  status VARCHAR(20) -- active/inactive/error
);
```
- 全部欄位輸入正確後，提供「截圖測試」按鈕 → 後端用 FFmpeg 拉一幀驗證連線並回傳圖片預覽。

### Page 6｜CCTV 即時監控

- Grid 佈局多路監看，串流採 WebRTC 或 HLS（RTSP 直接吃在瀏覽器相容性差，建議後端轉碼）。
- Alarm 畫面：
  - 觸發時該畫格紅框閃爍 + 音效 + 右側 Alarm 列表（時間、設備、觸發邏輯）。
  - Alarm 事件存表，供事後稽核：
```sql
CREATE TABLE alarm_event (
  alarm_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  device_id UNIQUEIDENTIFIER,
  flow_id UNIQUEIDENTIFIER,
  snapshot_path NVARCHAR(500),
  triggered_at DATETIME2 DEFAULT SYSUTCDATETIME(),
  acknowledged BIT DEFAULT 0
);
```
- ENV：
```env
STREAM_PROTOCOL=hls
ALARM_SOUND_ENABLED=true
ALARM_RETENTION_DAYS=90
```

### Page 7｜權限 / 部門 / 群組管理

- 標準 RBAC 三層：`User → Group → Role → Permission`，另掛 `Department` 做資料隔離（例如 A部門看不到B部門的 dataset/CCTV）。
```sql
CREATE TABLE app_user (user_id UNIQUEIDENTIFIER PRIMARY KEY, oauth_sub NVARCHAR(200), dept_id UNIQUEIDENTIFIER, display_name NVARCHAR(100));
CREATE TABLE department (dept_id UNIQUEIDENTIFIER PRIMARY KEY, dept_name NVARCHAR(100));
CREATE TABLE group_table (group_id UNIQUEIDENTIFIER PRIMARY KEY, group_name NVARCHAR(100));
CREATE TABLE role (role_id UNIQUEIDENTIFIER PRIMARY KEY, role_name NVARCHAR(100));
CREATE TABLE permission (perm_id UNIQUEIDENTIFIER PRIMARY KEY, perm_key VARCHAR(100)); -- e.g. dataset:write, training:execute
CREATE TABLE role_permission (role_id UNIQUEIDENTIFIER, perm_id UNIQUEIDENTIFIER);
CREATE TABLE user_group (user_id UNIQUEIDENTIFIER, group_id UNIQUEIDENTIFIER);
CREATE TABLE group_role (group_id UNIQUEIDENTIFIER, role_id UNIQUEIDENTIFIER);
```
- 權限檢查放在 API Gateway 層（middleware），各業務服務不重複寫權限邏輯。

### Page 8｜Dashboard

- 即時連線數：透過 Redis 記錄 active WebSocket session，Dashboard 訂閱 pub/sub 更新。
- 顯示：目前在線人數、各服務健康狀態、GPU 使用率（訓練中任務）、今日 Alarm 數量統計。
- 可選整合 Prometheus + Grafana iframe embed，或自建輕量圖表（ECharts）。

---

## 4. MinIO Bucket 規劃

```
datasets/{dataset_id}/raw/
datasets/{dataset_id}/thumbs/
datasets/{dataset_id}/exports/{export_id}.zip
models/{job_id}/best.pt
models/{job_id}/logs/
cctv_snapshots/{device_id}/{timestamp}.jpg
alarm_snapshots/{alarm_id}.jpg
```

---

## 5. docker-compose 服務骨架

```yaml
version: "3.9"
services:
  gateway:
    image: traefik:v3.0
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
  mssql:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      - ACCEPT_EULA=Y
      - MSSQL_SA_PASSWORD=${MSSQL_SA_PASSWORD}
  redis:
    image: redis:7-alpine
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
  auth-service:
    build: ./services/auth
  dataset-service:
    build: ./services/dataset
  annotation-service:
    build: ./services/annotation
  training-service:
    build: ./services/training
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  pipeline-service:
    build: ./services/pipeline
  monitor-service:
    build: ./services/monitor
  rbac-service:
    build: ./services/rbac
  dashboard-service:
    build: ./services/dashboard
  celery-worker:
    build: ./services/training
    command: celery -A worker worker --loglevel=info
```

---

## 6. 建議專案目錄結構

```
ai-platform/
├─ docker-compose.yml
├─ .env.example
├─ frontend/                # SPA，各頁面對應各自 module
│   ├─ pages/page1-auth/
│   ├─ pages/page2-dataset/
│   ├─ pages/page3-annotation/
│   ├─ pages/page4-training/
│   ├─ pages/page5-pipeline/
│   ├─ pages/page6-monitor/
│   ├─ pages/page7-rbac/
│   └─ pages/page8-dashboard/
└─ services/
    ├─ auth/
    ├─ dataset/
    ├─ annotation/
    ├─ training/
    ├─ pipeline/
    ├─ monitor/
    ├─ rbac/
    └─ dashboard/
```

---

## 7. AI Agent 協同層（Page 9｜自然語言指令 → 自動執行）

這一層跟「LLM+RAG 查詢」不同：不是被動回答問題，是**主動呼叫其他 8 個服務的 API 去執行任務**。本質上是一個具備 Function Calling 能力的 Agent Orchestrator，坐在所有服務之上，但**不繞過** Page7 的 RBAC——Agent 只能用「下指令的那個使用者」的權限去呼叫各服務。

### 7.1 架構

```
使用者輸入中文指令
        │
        ▼
agent-orchestrator-service
  ├─ Intent Parser（LLM）→ 拆解成結構化任務計畫（Task Plan，JSON）
  ├─ Tool Registry       → 各服務暴露的「可被 Agent 呼叫」的 API 清單
  ├─ Plan Preview        → 把計畫轉成人看得懂的中文步驟，交還使用者確認
  ├─ Executor            → 逐步呼叫 dataset/annotation/training/pipeline/monitor service
  └─ Audit Logger        → 每個步驟的輸入輸出、呼叫者、時間全部落地
```

範例指令：
> 「幫我把 A產線資料集標註瑕疵類，訓練一個 yolo11s，訓練好之後在 3 號機台建一個偵測到瑕疵就報警的邏輯，然後部署上去」

Agent 會拆解成任務計畫：

| Step | 動作 | 呼叫服務 |
|---|---|---|
| 1 | 確認資料集是否已存在 / 需要建立 | dataset-service |
| 2 | 執行輔助標註（VLM 粗標 + 標記為待人工覆核）| annotation-service |
| 3 | 提交訓練任務（model_key=yolo11s，套用 default 參數）| training-service |
| 4 | 訓練完成後生成邏輯圖（輸入節點=新模型、偵測節點=瑕疵類、輸出節點=Alarm）| pipeline-service |
| 5 | 綁定 3 號機台（cctv_device）與該 logic_flow | pipeline-service |
| 6 | **部署前停下，等待人工確認** | — |
| 7 | 使用者確認後才真正上線 | monitor-service |

### 7.2 關鍵設計：分階段自主權（Autonomy Level）

不是每個步驟都全自動執行，依風險分級：

| 風險等級 | 範例動作 | 是否需人工確認 |
|---|---|---|
| 低（可逆）| 建立資料集、提交訓練任務、產生邏輯圖草稿 | 不需要，Agent 直接做，事後可撤銷/刪除 |
| 中（消耗資源）| 啟動實際 GPU 訓練 | 顯示預估耗時/資源，使用者一鍵確認即可 |
| 高（影響產線/安全）| **標註結果最終定案**、**部署到正式 CCTV**、**覆蓋既有邏輯流程** | 一律強制人工 review + 明確按下「確認部署」，不可由 Agent 自動跳過 |

VLM 輔助標註只能產生「待覆核」狀態，不能直接視為 ground truth，避免標籤品質問題被靜默帶進訓練資料。

### 7.3 資料表

```sql
CREATE TABLE agent_task (
  task_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  raw_instruction NVARCHAR(MAX),      -- 使用者輸入的原始中文指令
  plan_json NVARCHAR(MAX),            -- LLM 拆解出的任務計畫
  status VARCHAR(20),                 -- planning/awaiting_confirm/running/completed/failed/cancelled
  requested_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

CREATE TABLE agent_task_step (
  step_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  task_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES agent_task(task_id),
  step_order INT,
  target_service VARCHAR(50),
  action VARCHAR(100),
  risk_level VARCHAR(10),             -- low/medium/high
  requires_confirmation BIT,
  confirmed_by NVARCHAR(100) NULL,
  confirmed_at DATETIME2 NULL,
  input_json NVARCHAR(MAX),
  output_json NVARCHAR(MAX),
  status VARCHAR(20)
);

CREATE TABLE agent_tool_registry (
  tool_key VARCHAR(100) PRIMARY KEY,  -- e.g. training.submit_job
  target_service VARCHAR(50),
  endpoint NVARCHAR(200),
  input_schema NVARCHAR(MAX),         -- JSON schema，給 LLM function calling 用
  default_risk_level VARCHAR(10)
);
```

### 7.4 ENV

```env
AGENT_LLM_PROVIDER=local        # local(vLLM/Ollama) or api
AGENT_LLM_MODEL=qwen2.5-14b-instruct
AGENT_REQUIRE_CONFIRM_ABOVE_RISK=medium   # low以上不需確認, medium以上才彈確認
AGENT_MAX_AUTO_STEPS=10
AGENT_AUDIT_RETENTION_DAYS=365
```

### 7.5 業界對照

這種「自然語言 → 自動編排 pipeline」的 Agent 模式，在 MLOps 圈子已有明確趨勢：

- **Weights & Biases、ClearML** 近期都在推「Agent 觸發訓練/評估流程」的功能，概念上跟你這個 Page9 相同：LLM 負責解讀意圖與拆解步驟，實際執行仍呼叫既有的 API/pipeline，而不是讓 LLM 自己生成訓練程式碼。
- 工業視覺領域（如 Landing AI 的 LandingLens）也在做「自然語言描述缺陷 → 自動建立標註任務 → 觸發訓練」的半自動流程，但**目前業界共識是部署到產線前一定保留人工確認節點**，這也是本設計把「部署」列為強制高風險確認的原因。
- 純自動化到「LLM 自己決定何時上線正式產線」的案例目前業界極少見，主要是誤報/漏報在工廠場域代價太高，多數落地案例都是「Agent 做到 90%，最後 10% 人工按確認」。

### 7.6 語音輸入（取代/輔助文字指令）

架構上只是在 Intent Parser **前面**多插一段 ASR（語音轉文字），後面的任務拆解、風險分級、確認機制全部沿用，不用重設計：

```
麥克風錄音
    │
    ▼
voice-service（ASR）
    │  → 轉譯文字（含信心分數）
    ▼
【轉譯結果確認畫面】← 新增的關鍵一步，見下方說明
    │  使用者看過/修正轉譯文字後才送出
    ▼
agent-orchestrator-service（沿用原本 Intent Parser 流程）
```

**為什麼一定要多一道「轉譯結果確認」，不能語音直接執行：**

語音辨識本身就有錯誤率，尤其是機台編號、產品代號、模型名稱（如 `yolo11s`）這類專有名詞最容易聽錯。如果「3號機台」被誤判成「5號機台」，指令又是部署動作，後果比文字打錯字嚴重得多。所以語音指令一律比文字指令多一層防護：**先顯示轉譯出的文字，使用者確認或修正後才進入任務規劃**，之後才走原本 7.2 訂的風險分級確認流程（低風險自動做、部署一律再次人工確認）。等於語音指令會經過兩次確認關卡：轉譯正確性 → 動作風險確認。

**技術選型建議：**

| 項目 | 建議 | 理由 |
|---|---|---|
| ASR 模型 | Faster-Whisper（large-v3）或 FunASR（Paraformer）| 中文辨識準確度高，且可地端部署，不需把工廠語音傳到雲端 |
| 部署方式 | 地端，跟 Agent LLM 共用 GPU 主機 | 語音內容可能涉及機台資訊/產線細節，比文字更敏感，避免外流 |
| 熱詞/自定義詞庫 | 支援 hotword boosting | 把機台代號、產品線名稱、`model_key`（yolo11n/s/m/l/x）等專有名詞加進熱詞表，大幅降低專有名詞誤判率 |
| 錄音方式 | Push-to-talk（按住說話）| 工廠環境噪音大，避免持續監聽誤觸發，也降低隱私疑慮 |
| 噪音處理 | RNNoise 或類似降噪前處理 | 產線環境噪音對辨識準確度影響大 |

**資料表：**

```sql
CREATE TABLE voice_command_log (
  voice_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  task_id UNIQUEIDENTIFIER NULL,          -- 確認後才關聯到 agent_task
  raw_transcript NVARCHAR(MAX),           -- ASR 原始轉譯
  confirmed_transcript NVARCHAR(MAX),     -- 使用者確認/修正後的文字
  asr_confidence FLOAT,
  audio_retained BIT DEFAULT 0,           -- 預設不保留原始錄音，僅留文字
  requested_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
```

**ENV：**

```env
VOICE_ASR_MODEL=faster-whisper-large-v3   # 或 funasr-paraformer
VOICE_ASR_LANGUAGE=zh
VOICE_HOTWORDS_FILE=/config/hotwords_zh.txt
VOICE_PUSH_TO_TALK=true
VOICE_RETAIN_RAW_AUDIO=false     # 預設不留原始錄音，僅留轉譯文字，降低隱私/儲存風險
VOICE_MIN_CONFIRM_CONFIDENCE=0.7 # 低於此信心分數，強制要求使用者逐字檢查而非一鍵確認
```

> 隱私提醒：語音預設**不保留原始錄音檔**，只留轉譯後文字，除非你有稽核需求要保留錄音（例如要事後回聽核對），那就把 `VOICE_RETAIN_RAW_AUDIO` 打開，並比照 alarm snapshot 訂保留天數，避免無限期累積。

---

## 8. LLM+RAG 專業報告生成（AOI 評估報告等）

可行，但**不建議「把生成的報告無條件全部丟回 RAG」**——這樣做長期會有 feedback loop 風險：AI 自己寫的內容如果有錯或用詞不精準，被無篩選地吸收回知識庫，下一次生成會把同樣的錯誤/偏差當「範例」再學一次，越滾越偏。正確做法是延續本文件一路強調的原則：**只有人工核准過的最終版才能進知識庫**，草稿不行。

### 8.1 完整工作流：匯入 → 整理表達 → 人工確認修正 → 學習

這是你現在要的核心流程，比單純「LLM 生成報告」多一個明確的**匯入階段**，四步驟環環相扣：

```
① 匯入
  使用者丟入原始內容：既有文件(docx/pdf/txt)、貼上文字、
  AOI截圖、資料匯出、口頭重點筆記...等，不要求格式統一
        │
        ▼
② 整理表達（LLM）
  LLM 讀取匯入內容 + 即時查詢結構化數據(缺陷率/趨勢等) +
  檢索過去已核准報告當範例 → 產出「整理過、有專業報告口吻」的草稿
  （這一步只做「表達」，不允許自己編數字，數字一律來自查詢結果）
        │
        ▼
③ 人工確認/修正
  使用者逐段檢視草稿，直接編輯（改措辭/調結構/補漏/修正數據對應）
  系統記錄每一處修改的「修改前/修改後」差異，不只存最終結果
        │
        ▼
④ 核准 → 學習
  核准後：
   a) 最終版整篇 → 向量化存入 report_corpus（供未來檢索範例）
   b) 逐處修改差異 → 累積進 style_profile（供未來表達風格調整）
  兩者都只在核准之後才發生，草稿與被打回的版本一律不學
```

### 8.2 架構

```
生成新報告請求（如：本週 AOI 缺陷評估）
        │
        ▼
report-service
  ├─ 資料收集：從 training/monitor/alarm 服務拉當期數據（缺陷率、類別分布、趨勢）
  ├─ Retrieval：向量庫撈「同產品線/同缺陷類型」的過去**已核准**報告當參考範例
  ├─ Draft 生成：LLM 依模板 + 檢索範例 + 當期數據 → 產出報告草稿
  ├─ 人工編輯：使用者修改草稿（此處的修改是最有價值的個人化訊號）
  ├─ 核准 → 存入 report_corpus，向量化，供未來檢索
  └─ Style Profile 更新：定期把「AI草稿 vs 人工修改後版本」的差異，萃取成風格偏好，回饋進 prompt
```

### 8.3 個人化怎麼做到——兩層機制，而非單純狂塞歷史報告

1. **Retrieval 層（RAG 本體）**：檢索「最相似情境」的過去報告當 few-shot 範例，解決的是「這次報告該引用哪些數據、结構長怎樣」，屬於**內容層面**的個人化。
2. **Style Profile 層（風格層）**：不是把整篇報告塞進 prompt，而是持續分析「使用者每次把 AI 草稿改成什麼樣子」，萃取出穩定偏好（例如：偏好條列式而非長段落、習慣先講結論再講數據、慣用特定術語），存成一份精簡的 `style_profile`（幾百字的規則描述），每次生成時當作 system prompt 的一部分帶入。
   - 這一層本質上是持續更新的「使用者偏好摘要」，比直接塞幾十篇舊報告進 context 更省 token、也更不容易被無關細節干擾。
   - 若語料量夠大（例如累積 500+ 篇核准報告），也可以考慮定期用 LoRA 對本地 LLM 做輕量微調，把風格內化進模型權重，而不是每次都靠 prompt 撐——但這是進階選項，初期用 RAG + style profile 就足夠。

### 8.4 資料表

```sql
CREATE TABLE report_source_import (   -- ①匯入階段：使用者丟入的原始內容
  import_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  draft_id UNIQUEIDENTIFIER NULL,     -- 產生草稿後回填關聯
  source_type VARCHAR(20),            -- file/pasted_text/image/dataset_ref
  raw_content_path NVARCHAR(500) NULL,-- 檔案存 MinIO 路徑
  raw_text NVARCHAR(MAX) NULL,        -- 貼上文字或 OCR/文字抽取後結果
  uploaded_by NVARCHAR(100),
  uploaded_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

CREATE TABLE report_template (
  template_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  report_type VARCHAR(50),        -- e.g. AOI_WEEKLY, AOI_INCIDENT
  structure_json NVARCHAR(MAX),   -- 章節結構定義
  is_active BIT DEFAULT 1
);

CREATE TABLE report_draft (
  draft_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  report_type VARCHAR(50),
  source_data_json NVARCHAR(MAX), -- 生成當下引用的結構化數據快照
  ai_draft_content NVARCHAR(MAX),
  final_content NVARCHAR(MAX) NULL,
  status VARCHAR(20) DEFAULT 'draft', -- draft/edited/approved/rejected
  edited_by NVARCHAR(100) NULL,
  approved_by NVARCHAR(100) NULL,
  approved_at DATETIME2 NULL
);

CREATE TABLE report_correction (   -- ③人工確認/修正階段：逐處差異
  correction_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  draft_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES report_draft(draft_id),
  section_key NVARCHAR(100),       -- 對應報告哪一段落/章節
  before_text NVARCHAR(MAX),
  after_text NVARCHAR(MAX),
  correction_type VARCHAR(20),     -- wording/structure/data_fix/omission
  corrected_by NVARCHAR(100),
  corrected_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

CREATE TABLE report_corpus (   -- ④只有 approved 的才會進這張表並向量化
  corpus_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  draft_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES report_draft(draft_id),
  embedding_ref NVARCHAR(200),   -- 對應 Vector DB 的 id
  indexed_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

CREATE TABLE style_profile (
  user_id UNIQUEIDENTIFIER,       -- 或 dept_id，看要個人化到人還是到部門
  profile_text NVARCHAR(2000),    -- 從 report_correction 定期萃取出的風格規則摘要
  sample_count INT,               -- 依據多少筆核准報告/修正紀錄萃取
  updated_at DATETIME2
);
```

### 8.5 ENV

```env
REPORT_LLM_MODEL=qwen2.5-14b-instruct
REPORT_RETRIEVAL_TOP_K=3
REPORT_STYLE_PROFILE_MIN_SAMPLES=10     # 少於此筆數不啟用風格層，避免樣本太少誤判
REPORT_AUTO_INGEST_ON_APPROVE=true      # 僅approved才自動進report_corpus
REPORT_STYLE_REFRESH_INTERVAL_DAYS=14   # 定期重新萃取風格，而非每次即時更新
```

### 8.6 需要留意的風險

- **只吸收 approved 版本**，草稿或被打回的版本不進語料庫，否則錯誤示範會被當正確範例學走。
- **定期而非即時更新 style_profile**：每篇報告改完就即時更新容易被單一個案的特殊修改帶偏，建議累積一定筆數（如兩週或 10 篇）再重新萃取一次。
- **報告中的數據引用必須可追溯**：Draft 生成時引用的 AOI 數據要存 `source_data_json` 快照，避免之後對帳時對不上真實產線數據——報告本身可以個人化，但裡面的數字必須是真的。

---

## 9. 落地建議順序（Roadmap）

1. 基礎設施：Keycloak + MSSQL + MinIO + Redis + Gateway 打通
2. Page1 + Page7（先有 Auth/RBAC 才能保護後面所有頁面）
3. Page2 + Page3（資料集與標注是訓練的前提）
4. Page4（模型訓練，先驗證 GPU 排程與 Celery）
5. Page5 + Page6（CCTV 編排與監控，依賴 Page4 產出的模型）
6. Page8（最後補監控儀表板）
7. Page9 / Agent 協同層（最後導入，前 8 頁的 API 要先穩定，Agent 才有東西可呼叫）
8. LLM+RAG 報告生成模組（需先有一段時間的核准報告語料，建議在系統上線運行 1~2 個月、累積足夠案例後再啟用）
