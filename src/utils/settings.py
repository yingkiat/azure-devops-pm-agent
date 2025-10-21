from __future__ import annotations
import getpass
from pathlib import Path
from typing import Literal, Optional, List

from dotenv import load_dotenv
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings

# auto‑load .env (repo root or cwd)
for p in (Path(__file__).parents[2] / ".env", Path(".env")):
    if p.exists():
        load_dotenv(p)
        break


class Settings(BaseSettings):
    # DevOps
    azdo_org_url: HttpUrl = Field(..., env="AZDO_ORG_URL")
    azdo_project: str = Field(..., env="AZDO_PROJECT")  # Primary project for plans
    azdo_projects: List[str] = Field(default_factory=list, env="AZDO_PROJECTS")  # All projects to monitor
    azdo_pat: str = Field(..., env="AZDO_PAT")
    azdo_process: str = Field("Agile", env="AZDO_PROCESS")
    azdo_assigned_to: Optional[str] = Field(None, env="AZDO_ASSIGNED_TO")
    azdo_wiki_name: str = Field(..., env="AZDO_WIKI_NAME")
    azdo_wiki_page: str = Field("/Epics", env="AZDO_WIKI_PAGE")
    
    def get_all_projects(self) -> List[str]:
        """Get all projects including primary project."""
        projects = [self.azdo_project]
        if self.azdo_projects:
            projects.extend([p.strip() for p in self.azdo_projects if p.strip() != self.azdo_project])
        return list(set(projects))  # Remove duplicates

    # OpenAI
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: str = Field(..., env="AZURE_OPENAI_KEY")
    azure_openai_api_version: str = Field(..., env="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment: str = Field(..., env="AZURE_OPENAI_DEPLOYMENT")

    # Gemini (for diagram generation)
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash-image-preview", env="GEMINI_MODEL")
    gemini_disable_ssl_verify: bool = Field(False, env="GEMINI_DISABLE_SSL_VERIFY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

def default_assignee() -> str:
    return settings.azdo_assigned_to or f"{getpass.getuser()}@yourcompany.com"
