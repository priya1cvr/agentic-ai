# Databricks notebook source
# MAGIC %md
# MAGIC Explore the Discover Page
# MAGIC Now let's explore what's available in your workspace. The Discover page is where you browse models and datasets.
# MAGIC
# MAGIC UI -> Left nav -> Discover
# MAGIC
# MAGIC What to look for:
# MAGIC
# MAGIC Model types available: Chat models (for generation), Embedding models (for Vector Search), Code models, etc. <br>
# MAGIC Model providers: Databricks-hosted (Meta Llama, etc.), third-party <br>
# MAGIC Task filters: Filter by task to find models for your specific need <br>
# MAGIC
# MAGIC
# MAGIC UI -> Left nav -> Marketplace<br>
# MAGIC What to look for:
# MAGIC
# MAGIC Pre-built solutions: Agent templates, data products, ML models <br>
# MAGIC Datasets: Public datasets you can use for testing and development <br>
# MAGIC Providers: Databricks, partners, and community contributors<br>
# MAGIC
# MAGIC - - **Note** Know that Discover shows workspace-local assets and Marketplace shows installable external assets. They're different UI sections.

# COMMAND ----------

# ------------------------------------------------------------------
# Setup: Install dependencies
# ------------------------------------------------------------------

%pip install openai --quiet

# Restart Python to pick up the new package
dbutils.library.restartPython()

# COMMAND ----------

# ------------------------------------------------------------------
# Setup: Initialize the OpenAI-compatible client for Databricks
# ------------------------------------------------------------------
# Note : here i have used my personal open AI token  which asks as input 

import os
import requests
import getpass

print("🔑 Authenticating with your Paid OpenAI Account...")
# Securely prompt for the token without showing characters on the screen
openai_key = getpass.getpass("Paste your OpenAI API Key (starts with sk-...) and press Enter: ")

if not openai_key.strip():
    raise ValueError("❌ API Key cannot be empty.")

# Enforce the strict public API server destination to bypass corporate 403 walls
API_URL = "https://api.openai.com/v1/models"
headers = {"Authorization": f"Bearer {openai_key.strip()}"}

print("\n📡 Connecting to OpenAI servers...")
# Request the official model configurations deployment list
resp = requests.get(API_URL, headers=headers)

if resp.status_code == 200:
    models_data = resp.json().get("data", [])
    
    # Categorize OpenAI models into operational groups based on naming conventions
    gpt_models = [m for m in models_data if 'gpt' in m['id']]
    embedding_models = [m for m in models_data if 'embed' in m['id']]
    other_models = [m for m in models_data if 'gpt' not in m['id'] and 'embed' not in m['id']]
    
    print(f"\n=== Chat/Generation Models (GPT): {len(gpt_models)} ===")
    for m in sorted(gpt_models, key=lambda x: x['id'])[:10]:
        print(f"  {m['id']}")
        
    print(f"\n=== Feature Extraction Models (Embeddings): {len(embedding_models)} ===")
    for m in sorted(embedding_models, key=lambda x: x['id']):
        print(f"  {m['id']}")
        
    print(f"\n=== Specialized Models (Moderation/Audio/DALL-E): {len(other_models)} ===")
    for m in sorted(other_models, key=lambda x: x['id'])[:10]:
        print(f"  {m['id']}")
else:
    print(f"❌ Could not list OpenAI endpoints. Error Code: {resp.status_code}")
    print(f"Details: {resp.text}")
    print("\nIf you still see a 403, verify that your account has a positive prepaid credit balance ($5.00) active inside the platform dashboard.")



# COMMAND ----------

# MAGIC %md
# MAGIC **List the available foundational models inside the Databricks Free Edition** without using any OpenAI keys or tokens

# COMMAND ----------

# List available foundation models in Databricks Free Edition without any API keys
import mlflow.deployments

# 1. Initialize the built-in, local free tier MLflow deployment driver
client = mlflow.deployments.get_deploy_client("databricks")

print("📡 Scanning active foundation model endpoints on your free workspace shard...")

try:
    # 2. Query the local workspace driver to list out active endpoints
    # list_endpoints returns a list of dictionaries in the Databricks Free Edition runtime
    endpoints_raw = client.list_endpoints()
    
    # Safely extract the string names from the raw dictionary structure
    active_endpoints = [e.get("name") for e in endpoints_raw if isinstance(e, dict)]
    
    if active_endpoints:
        # 3. Categorize the discovered models based on standard naming conventions
        chat_models = [name for name in active_endpoints if any(kw in name.lower() for kw in ["llama", "dbrx", "mixtral", "instruct", "chat"])]
        embedding_models = [name for name in active_endpoints if any(kw in name.lower() for kw in ["gte", "bge", "embedding"])]
        other_models = [name for name in active_endpoints if name not in chat_models and name not in embedding_models]
        
        print(f"\n=== Chat / Generation Models (Instruct): {len(chat_models)} ===")
        for model in sorted(chat_models):
            print(f"  {model}")
            
        print(f"\n=== Feature Extraction Models (Embeddings): {len(embedding_models)} ===")
        for model in sorted(embedding_models):
            print(f"  {model}")
            
        if other_models:
            print(f"\n=== Specialized / Other System Endpoints: {len(other_models)} ===")
            for model in sorted(other_models):
                print(f"  {model}")
    else:
        print("\n⚠️ The model endpoint list returned empty.")
        print("This usually means no public token-serving configurations are active in this specific region shard.")

except Exception as e:
    print(f"\n❌ Local Driver Query Failed: {e}")
    print("\nExpected default foundation models pre-arranged for the associate exam:")
    print("  Chat/Instruct: databricks-meta-llama-3-1-70b-instruct")
    print("  Embedding:     databricks-gte-large-en")
    print("  Embedding:     databricks-bge-large-en")



# COMMAND ----------

# MAGIC %md
# MAGIC **Decision Framework Summary**
# MAGIC
# MAGIC ## Agent Brick Decision Framework
# MAGIC
# MAGIC | Primary Goal | Recommended Agent |
# MAGIC |---|---|
# MAGIC | Answer questions from DOCS | **KNOWLEDGE ASSISTANT** |
# MAGIC | Answer questions from TABLES | **AI/BI GENIE** |
# MAGIC | Route multiple task types to different specialists | **SUPERVISOR AGENT** |
# MAGIC | Extract structured fields from unstructured text | **INFORMATION EXTRACTION** |
# MAGIC | Parse document layout, OCR, extract tables from images | **DOCUMENT PARSING** |
# MAGIC | Custom text task (translate, generate, classify) | **CUSTOM LLM** |
# MAGIC | None of the above / need full control with OSS libraries | **CODE YOUR OWN AGENT** |
# MAGIC
# MAGIC ## Keywords to Watch for on the Exam
# MAGIC
# MAGIC | Agent Type | Keywords |
# MAGIC |---|---|
# MAGIC | Knowledge Assistant | "knowledge base", "FAQ", "documentation", "Q&A", "answer questions from docs" |
# MAGIC | AI/BI Genie | "tables", "SQL", "revenue", "metrics", "structured data Q&A", "text-to-SQL" |
# MAGIC | Supervisor Agent | "route", "different types of requests", "multiple specialists", "delegate", "orchestrate" |
# MAGIC | Information Extraction | "extract fields", "structured JSON", "invoices", "contracts", "entity resolution" |
# MAGIC | Document Parsing | "OCR", "scanned", "table extraction", "layout analysis", "document structure" |
# MAGIC | Custom LLM | "translate", "generate content", "custom task", "code generation", "specialized model" |
# MAGIC | Code Your Own | "LangGraph", "DSPy", "custom control flow", "OSS libraries", "full flexibility" |

# COMMAND ----------

