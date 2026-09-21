USE ai_annotation;
GO

CREATE TABLE annotation (
  annotation_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  asset_id UNIQUEIDENTIFIER, -- cross-service ref to ai_dataset.dataset_asset, no FK across DBs
  class_id INT,
  bbox_x FLOAT, bbox_y FLOAT, bbox_w FLOAT, bbox_h FLOAT,
  shape_type VARCHAR(20), -- bbox/polygon
  polygon_points NVARCHAR(MAX) NULL,
  source VARCHAR(20) DEFAULT 'human',   -- human / ai_suggested
  confidence FLOAT NULL,
  risk_score FLOAT NULL,
  review_status VARCHAR(20) DEFAULT 'final', -- draft/pending_review/approved/rejected/final
  reviewed_by NVARCHAR(100) NULL,
  reviewed_at DATETIME2 NULL,
  annotated_by NVARCHAR(100),
  updated_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE annotation_demo (
  demo_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dataset_id UNIQUEIDENTIFIER, -- cross-service ref to ai_dataset.dataset
  class_id INT,
  demo_image_path NVARCHAR(500),
  demo_annotation_json NVARCHAR(MAX),
  text_description NVARCHAR(1000),
  created_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO
