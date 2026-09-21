USE ai_rbac;
GO

CREATE TABLE department (
  dept_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  dept_name NVARCHAR(100) NOT NULL
);
GO

CREATE TABLE app_user (
  user_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  oauth_sub NVARCHAR(200) NOT NULL UNIQUE,
  dept_id UNIQUEIDENTIFIER NULL FOREIGN KEY REFERENCES department(dept_id),
  display_name NVARCHAR(100),
  created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE group_table (
  group_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  group_name NVARCHAR(100) NOT NULL
);
GO

CREATE TABLE role (
  role_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  role_name NVARCHAR(100) NOT NULL
);
GO

CREATE TABLE permission (
  perm_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
  perm_key VARCHAR(100) NOT NULL UNIQUE
);
GO

CREATE TABLE role_permission (
  role_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES role(role_id),
  perm_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES permission(perm_id),
  PRIMARY KEY (role_id, perm_id)
);
GO

CREATE TABLE user_group (
  user_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES app_user(user_id),
  group_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES group_table(group_id),
  PRIMARY KEY (user_id, group_id)
);
GO

CREATE TABLE group_role (
  group_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES group_table(group_id),
  role_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES role(role_id),
  PRIMARY KEY (group_id, role_id)
);
GO

-- seed baseline permissions referenced across services
INSERT INTO permission (perm_key) VALUES
  ('dataset:read'), ('dataset:write'),
  ('annotation:read'), ('annotation:write'), ('annotation:approve'),
  ('training:read'), ('training:execute'),
  ('pipeline:read'), ('pipeline:write'), ('pipeline:deploy'),
  ('monitor:read'), ('monitor:ack'),
  ('rbac:read'), ('rbac:write'),
  ('dashboard:read');
GO

INSERT INTO role (role_name) VALUES ('admin'), ('operator'), ('viewer');
GO
