"""My impl for OpenAI provider."""

import os

import llm
import yaml
from llm import hookimpl


def load_config():
    """Load config from azure/config.yaml."""
    azure_path = llm.user_dir() / "openai" / "config.yml"
    if not azure_path.exists():
        return []

    with open(azure_path) as f:
        models = yaml.safe_load(f)

    return models or []


@hookimpl
def register_models(register):
    models = load_config()

    for model in models:
        provider = model.get("provider")
        aliases = model.pop("aliases", [])

        if provider == "openai":
            from llm_plugin_openai.openai import OpenAIChat

            register(
                OpenAIChat(
                    model_id=model["model_id"],
                    model_name=model["model_name"],
                    api_key_name=model.get("api_key_name"),
                    endpoint=model.get("endpoint"),
                ),
                aliases=aliases,
            )
