import uuid

from pydantic import BaseModel, ConfigDict


class DepartmentIn(BaseModel):
    dept_name: str


class DepartmentOut(DepartmentIn):
    model_config = ConfigDict(from_attributes=True)
    dept_id: uuid.UUID


class GroupIn(BaseModel):
    group_name: str


class GroupOut(GroupIn):
    model_config = ConfigDict(from_attributes=True)
    group_id: uuid.UUID


class RoleIn(BaseModel):
    role_name: str


class RoleOut(RoleIn):
    model_config = ConfigDict(from_attributes=True)
    role_id: uuid.UUID


class PermissionIn(BaseModel):
    perm_key: str


class PermissionOut(PermissionIn):
    model_config = ConfigDict(from_attributes=True)
    perm_id: uuid.UUID


class UserIn(BaseModel):
    oauth_sub: str
    display_name: str | None = None
    dept_id: uuid.UUID | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    oauth_sub: str
    display_name: str | None
    dept_id: uuid.UUID | None


class AssignmentIn(BaseModel):
    target_id: uuid.UUID
