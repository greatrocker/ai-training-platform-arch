-- Label schema/class management for Page3 (referenced in architecture doc
-- section 3 prose as `label_schema` but no DDL was given there — designed
-- here). One schema per dataset; classes are scoped to that schema so
-- annotation.class_id stays meaningful per-dataset.
USE ai_annotation;
GO

CREATE TABLE label_schema (
  schema_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dataset_id UNIQUEIDENTIFIER NOT NULL UNIQUE, -- cross-service ref to ai_dataset.dataset, no FK
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE label_class (
  class_id INT IDENTITY(1,1) PRIMARY KEY,
  schema_id UNIQUEIDENTIFIER NOT NULL FOREIGN KEY REFERENCES label_schema(schema_id),
  class_name NVARCHAR(100) NOT NULL,
  color VARCHAR(20) NULL,
  display_order INT NULL
);
GO
