from __future__ import annotations
from typing import List, Dict

from azure.devops.v7_0.work_item_tracking.models import Wiql, TeamContext, JsonPatchOperation
from azure.devops.v7_0.work_item_tracking.work_item_tracking_client import WorkItemTrackingClient

from utils.settings import settings, default_assignee
from .connection import get_connection

# ── helpers ───────────────────────────────────────────────────────────
def _wit() -> WorkItemTrackingClient:
    return get_connection().clients.get_work_item_tracking_client()


def _run_wiql(query: str) -> List[Dict]:
    wit = _wit()
    wiql = Wiql(query=query)
    ctx = TeamContext(project=settings.azdo_project)
    res = wit.query_by_wiql(wiql=wiql, team_context=ctx)
    if not res.work_items:
        return []
    ids = [ref.id for ref in res.work_items]
    fields = ["System.Id", "System.Title", "System.State", "System.WorkItemType"]
    items = wit.get_work_items(ids=ids, fields=fields)
    return [i.as_dict() for i in items]

# ── list functions ────────────────────────────────────────────────────
def list_epics() -> List[Dict]:
    q = f"""
    SELECT [System.Id], [System.Title], [System.State]
    FROM WorkItems
    WHERE [System.WorkItemType] = 'Epic'
      AND [System.TeamProject] = '{settings.azdo_project}'
    ORDER BY [System.Id]"""
    return _run_wiql(q)


def list_features_and_stories(parent_id: int) -> List[Dict]:
    q = f"""
    SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
    FROM WorkItemLinks
    WHERE [Source].[System.Id] = {parent_id}
      AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'"""
    ctx = TeamContext(project=settings.azdo_project)
    res = _wit().query_by_wiql(Wiql(query=q), team_context=ctx)
    child_ids = [l.target.id for l in res.work_item_relations if l.target]
    return _run_wiql(f"SELECT * FROM WorkItems WHERE [System.Id] IN ({','.join(map(str, child_ids))})") if child_ids else []


def list_tasks(parent_id: int) -> List[Dict]:
    q = f"""
    SELECT [System.Id]
    FROM WorkItemLinks
    WHERE [Source].[System.Id] = {parent_id}
      AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'"""
    ctx = TeamContext(project=settings.azdo_project)
    res = _wit().query_by_wiql(Wiql(query=q), team_context=ctx)
    ids = [l.target.id for l in res.work_item_relations if l.target]
    return _run_wiql(f"SELECT * FROM WorkItems WHERE [System.Id] IN ({','.join(map(str, ids))})") if ids else []


def list_orphan_features() -> List[Dict]:
    """
    Features / User Stories that have NO parent Epic.
    """
    all_features_q = f"""
    SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
    FROM WorkItems
    WHERE [System.WorkItemType] IN ('Feature','User Story','Product Backlog Item')
      AND [System.TeamProject] = '{settings.azdo_project}'
    """
    all_items = _run_wiql(all_features_q)
    if not all_items:
        return []

    # find IDs that *do* have a parent Epic
    link_q = """
    SELECT [Target].[System.Id]
    FROM WorkItemLinks
    WHERE [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
      AND [Source].[System.WorkItemType] = 'Epic'
    """
    ctx = TeamContext(project=settings.azdo_project)
    linked = _wit().query_by_wiql(Wiql(query=link_q), team_context=ctx)
    child_ids_with_parent = {rel.target.id for rel in linked.work_item_relations if rel.target}

    return [it for it in all_items if it["id"] not in child_ids_with_parent]


def list_orphan_tasks() -> List[Dict]:
    """
    Tasks / Bugs that have NO parent Feature or Story.
    """
    all_tasks_q = f"""
    SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
    FROM WorkItems
    WHERE [System.WorkItemType] IN ('Task','Bug')
      AND [System.TeamProject] = '{settings.azdo_project}'
    """
    all_items = _run_wiql(all_tasks_q)
    if not all_items:
        return []

    link_q = """
    SELECT [Target].[System.Id]
    FROM WorkItemLinks
    WHERE [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
    """
    ctx = TeamContext(project=settings.azdo_project)
    linked = _wit().query_by_wiql(Wiql(query=link_q), team_context=ctx)
    child_ids_with_parent = {rel.target.id for rel in linked.work_item_relations if rel.target}

    return [it for it in all_items if it["id"] not in child_ids_with_parent]

def get_work_item_hierarchy() -> tuple[str, str, str]:
    return ("Epic", "Feature/User Story", "Task")

# ── CRUD helpers ──────────────────────────────────────────────────────
def create_work_item(work_item_type: str, title: str, description: str = "", parent_id: int | None = None) -> Dict:
    wit = _wit()
    document = [
        JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
        JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value=default_assignee()),
    ]
    if description:
        document.append(JsonPatchOperation(op="add", path="/fields/System.Description", value=description))
    if parent_id:
        document.append(
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value={
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": f"{settings.azdo_org_url}/{settings.azdo_project}/_apis/wit/workItems/{parent_id}",
                },
            )
        )
    return wit.create_work_item(document=document, project=settings.azdo_project, type=work_item_type).as_dict()


def delete_work_item(work_item_id: int):
    _wit().delete_work_item(id=work_item_id)
