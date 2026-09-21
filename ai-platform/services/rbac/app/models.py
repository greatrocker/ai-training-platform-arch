import uuid

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid_col():
    return mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)


user_group = Table(
    "user_group",
    Base.metadata,
    Column("user_id", UNIQUEIDENTIFIER, ForeignKey("app_user.user_id"), primary_key=True),
    Column("group_id", UNIQUEIDENTIFIER, ForeignKey("group_table.group_id"), primary_key=True),
)

group_role = Table(
    "group_role",
    Base.metadata,
    Column("group_id", UNIQUEIDENTIFIER, ForeignKey("group_table.group_id"), primary_key=True),
    Column("role_id", UNIQUEIDENTIFIER, ForeignKey("role.role_id"), primary_key=True),
)

role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", UNIQUEIDENTIFIER, ForeignKey("role.role_id"), primary_key=True),
    Column("perm_id", UNIQUEIDENTIFIER, ForeignKey("permission.perm_id"), primary_key=True),
)


class Department(Base):
    __tablename__ = "department"
    dept_id: Mapped[uuid.UUID] = _uuid_col()
    dept_name: Mapped[str] = mapped_column(String(100))
    users: Mapped[list["AppUser"]] = relationship(back_populates="department")


class AppUser(Base):
    __tablename__ = "app_user"
    user_id: Mapped[uuid.UUID] = _uuid_col()
    oauth_sub: Mapped[str] = mapped_column(String(200), unique=True)
    dept_id: Mapped[uuid.UUID | None] = mapped_column(UNIQUEIDENTIFIER, ForeignKey("department.dept_id"), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=True)

    department: Mapped[Department | None] = relationship(back_populates="users")
    groups: Mapped[list["Group"]] = relationship(secondary=user_group, back_populates="users")


class Group(Base):
    __tablename__ = "group_table"
    group_id: Mapped[uuid.UUID] = _uuid_col()
    group_name: Mapped[str] = mapped_column(String(100))

    users: Mapped[list[AppUser]] = relationship(secondary=user_group, back_populates="groups")
    roles: Mapped[list["Role"]] = relationship(secondary=group_role, back_populates="groups")


class Role(Base):
    __tablename__ = "role"
    role_id: Mapped[uuid.UUID] = _uuid_col()
    role_name: Mapped[str] = mapped_column(String(100))

    groups: Mapped[list[Group]] = relationship(secondary=group_role, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permission, back_populates="roles")


class Permission(Base):
    __tablename__ = "permission"
    perm_id: Mapped[uuid.UUID] = _uuid_col()
    perm_key: Mapped[str] = mapped_column(String(100), unique=True)

    roles: Mapped[list[Role]] = relationship(secondary=role_permission, back_populates="permissions")
