from functools import lru_cache
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from utils.settings import settings

@lru_cache(maxsize=1)
def get_connection() -> Connection:
    creds = BasicAuthentication("", settings.azdo_pat)
    return Connection(base_url=str(settings.azdo_org_url), creds=creds)
