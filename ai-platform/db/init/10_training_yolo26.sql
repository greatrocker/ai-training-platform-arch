-- Migration for an already-bootstrapped ai_training DB: add task_type and
-- swap the placeholder yolo11 seed rows for YOLO26 detect + YOLO26-seg,
-- the two families this platform actually trains for now.
USE ai_training;
GO

IF COL_LENGTH('model_registry', 'task_type') IS NULL
BEGIN
    ALTER TABLE model_registry ADD task_type VARCHAR(20) NOT NULL DEFAULT 'detect';
END
GO

DELETE FROM training_job WHERE model_key LIKE 'yolo11%';
DELETE FROM model_registry WHERE model_key LIKE 'yolo11%';
GO

MERGE model_registry AS target
USING (VALUES
  ('yolo26n', 'detect', 1, 'yolo26n.pt', NULL),
  ('yolo26s', 'detect', 2, 'yolo26s.pt', NULL),
  ('yolo26m', 'detect', 3, 'yolo26m.pt', NULL),
  ('yolo26l', 'detect', 4, 'yolo26l.pt', NULL),
  ('yolo26x', 'detect', 5, 'yolo26x.pt', NULL),
  ('yolo26n-seg', 'segment', 6, 'yolo26n-seg.pt', NULL),
  ('yolo26s-seg', 'segment', 7, 'yolo26s-seg.pt', NULL),
  ('yolo26m-seg', 'segment', 8, 'yolo26m-seg.pt', NULL),
  ('yolo26l-seg', 'segment', 9, 'yolo26l-seg.pt', NULL),
  ('yolo26x-seg', 'segment', 10, 'yolo26x-seg.pt', NULL)
) AS source (model_key, task_type, display_order, base_weight_path, arch_config_path)
ON target.model_key = source.model_key
WHEN NOT MATCHED THEN
  INSERT (model_key, task_type, display_order, base_weight_path, arch_config_path)
  VALUES (source.model_key, source.task_type, source.display_order, source.base_weight_path, source.arch_config_path);
GO
