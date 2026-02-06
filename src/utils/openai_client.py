import openai
from utils.settings import settings

client = openai.AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_key,
    api_version=settings.azure_openai_api_version,
)

def chat(messages: list[dict], temperature=0.4, max_tokens=4096):
    return client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
