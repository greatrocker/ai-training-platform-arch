-- Page9 agent-orchestrator schema. Reserved for future rollout per roadmap step 7.
USE ai_agent;
GO

CREATE TABLE agent_task (
  task_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  raw_instruction NVARCHAR(MAX),
  plan_json NVARCHAR(MAX),
  status VARCHAR(20), -- planning/awaiting_confirm/running/completed/failed/cancelled
  requested_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE agent_task_step (
  step_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  task_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES agent_task(task_id),
  step_order INT,
  target_service VARCHAR(50),
  action VARCHAR(100),
  risk_level VARCHAR(10), -- low/medium/high
  requires_confirmation BIT,
  confirmed_by NVARCHAR(100) NULL,
  confirmed_at DATETIME2 NULL,
  input_json NVARCHAR(MAX),
  output_json NVARCHAR(MAX),
  status VARCHAR(20)
);
GO

CREATE TABLE agent_tool_registry (
  tool_key VARCHAR(100) PRIMARY KEY,
  target_service VARCHAR(50),
  endpoint NVARCHAR(200),
  input_schema NVARCHAR(MAX),
  default_risk_level VARCHAR(10)
);
GO

CREATE TABLE voice_command_log (
  voice_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  task_id UNIQUEIDENTIFIER NULL FOREIGN KEY REFERENCES agent_task(task_id),
  raw_transcript NVARCHAR(MAX),
  confirmed_transcript NVARCHAR(MAX),
  asr_confidence FLOAT,
  audio_retained BIT DEFAULT 0,
  requested_by NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO
