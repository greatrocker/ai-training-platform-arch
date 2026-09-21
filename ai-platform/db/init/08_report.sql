-- LLM+RAG report generation schema (section 8). Reserved for future rollout
-- per roadmap step 8, after approved-report corpus has accumulated.
USE ai_report;
GO

CREATE TABLE report_template (
  template_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  report_type VARCHAR(50),
  structure_json NVARCHAR(MAX),
  is_active BIT DEFAULT 1
);
GO

CREATE TABLE report_draft (
  draft_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  report_type VARCHAR(50),
  source_data_json NVARCHAR(MAX),
  ai_draft_content NVARCHAR(MAX),
  final_content NVARCHAR(MAX) NULL,
  status VARCHAR(20) DEFAULT 'draft', -- draft/edited/approved/rejected
  edited_by NVARCHAR(100) NULL,
  approved_by NVARCHAR(100) NULL,
  approved_at DATETIME2 NULL
);
GO

CREATE TABLE report_source_import (
  import_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  draft_id UNIQUEIDENTIFIER NULL FOREIGN KEY REFERENCES report_draft(draft_id),
  source_type VARCHAR(20), -- file/pasted_text/image/dataset_ref
  raw_content_path NVARCHAR(500) NULL,
  raw_text NVARCHAR(MAX) NULL,
  uploaded_by NVARCHAR(100),
  uploaded_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE report_correction (
  correction_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  draft_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES report_draft(draft_id),
  section_key NVARCHAR(100),
  before_text NVARCHAR(MAX),
  after_text NVARCHAR(MAX),
  correction_type VARCHAR(20), -- wording/structure/data_fix/omission
  corrected_by NVARCHAR(100),
  corrected_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE report_corpus (
  corpus_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  draft_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES report_draft(draft_id),
  embedding_ref NVARCHAR(200),
  indexed_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE style_profile (
  user_id UNIQUEIDENTIFIER,
  profile_text NVARCHAR(2000),
  sample_count INT,
  updated_at DATETIME2
);
GO
