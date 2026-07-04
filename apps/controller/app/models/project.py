from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class Project(Base):
    __tablename__ = "app_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    description = Column(String(1024))
    project_type = Column(String(256))
    owner_id = Column(String(128))
    created_at = Column(DateTime, server_default=func.now())


class ProjectMember(Base):
    __tablename__ = "app_project_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("app_projects.id"))
    user_id = Column(String(128))
    role = Column(String(32), default="member")
    created_at = Column(DateTime, server_default=func.now())


class ProjectConfig(Base):
    __tablename__ = "app_project_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("app_projects.id"))
    env_type = Column(String(32), nullable=False)
    config_key = Column(String(256), nullable=False)
    config_value = Column(String(512))
    created_at = Column(DateTime, server_default=func.now())