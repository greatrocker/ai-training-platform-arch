USE ai_training;
GO

CREATE TABLE model_registry (
  model_key VARCHAR(50) PRIMARY KEY,
  task_type VARCHAR(20) NOT NULL DEFAULT 'detect', -- detect / segment (others added later)
  display_order INT,
  base_weight_path NVARCHAR(500), -- Ultralytics auto-downloads by this name if not a real path
  arch_config_path NVARCHAR(500),
  is_active BIT DEFAULT 1
);
GO

CREATE TABLE training_job (
  job_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dataset_id UNIQUEIDENTIFIER,
  model_key VARCHAR(50) FOREIGN KEY REFERENCES model_registry(model_key),
  params_json NVARCHAR(MAX),
  status VARCHAR(20),   -- queued/running/completed/failed
  output_model_path NVARCHAR(500),
  metrics_json NVARCHAR(MAX),
  training_mode VARCHAR(20) DEFAULT 'full',   -- full / incremental
  parent_job_id UNIQUEIDENTIFIER NULL,
  replay_ratio FLOAT NULL,
  freeze_backbone BIT NULL,
  progress_current_epoch INT NULL,
  progress_total_epochs INT NULL,
  started_at DATETIME2, finished_at DATETIME2
);
GO

-- YOLO26 detect + YOLO26-seg are the primary supported families for now
-- (per product decision); other architectures/tasks can be registered
-- later through this same table without touching frontend code.
INSERT INTO model_registry (model_key, task_type, display_order, base_weight_path, arch_config_path) VALUES
  ('yolo26n', 'detect', 1, 'yolo26n.pt', NULL),
  ('yolo26s', 'detect', 2, 'yolo26s.pt', NULL),
  ('yolo26m', 'detect', 3, 'yolo26m.pt', NULL),
  ('yolo26l', 'detect', 4, 'yolo26l.pt', NULL),
  ('yolo26x', 'detect', 5, 'yolo26x.pt', NULL),
  ('yolo26n-seg', 'segment', 6, 'yolo26n-seg.pt', NULL),
  ('yolo26s-seg', 'segment', 7, 'yolo26s-seg.pt', NULL),
  ('yolo26m-seg', 'segment', 8, 'yolo26m-seg.pt', NULL),
  ('yolo26l-seg', 'segment', 9, 'yolo26l-seg.pt', NULL),
  ('yolo26x-seg', 'segment', 10, 'yolo26x-seg.pt', NULL);
GO
