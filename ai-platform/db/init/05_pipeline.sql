USE ai_pipeline;
GO

CREATE TABLE logic_flow (
  flow_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  name NVARCHAR(200),
  graph_json NVARCHAR(MAX),
  created_by NVARCHAR(100),
  updated_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE cctv_device (
  device_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  device_name NVARCHAR(100),
  rtsp_url NVARCHAR(500),
  username NVARCHAR(100),
  password_encrypted VARBINARY(MAX),
  bound_flow_id UNIQUEIDENTIFIER NULL FOREIGN KEY REFERENCES logic_flow(flow_id),
  status VARCHAR(20) -- active/inactive/error
);
GO
