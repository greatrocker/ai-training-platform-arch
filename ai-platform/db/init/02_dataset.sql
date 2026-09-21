USE ai_dataset;
GO

CREATE TABLE dataset (
  dataset_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  name NVARCHAR(200),
  source_path NVARCHAR(500),
  source_type VARCHAR(20), -- video / image_folder
  filename_pattern NVARCHAR(200) NULL, -- image_folder only, fnmatch glob e.g. *Stitch_Img*
  status VARCHAR(20),      -- pending/processing/ready/failed
  created_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE dataset_asset (
  asset_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dataset_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES dataset(dataset_id),
  minio_path NVARCHAR(500),
  width INT, height INT,
  frame_index INT NULL
);
GO
