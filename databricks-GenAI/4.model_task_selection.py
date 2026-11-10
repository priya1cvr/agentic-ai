# Databricks notebook source
# ------------------------------------------------------------------
# Setup: Install dependencies
# ------------------------------------------------------------------

%pip install openai --quiet

# Restart Python to pick up the new package
dbutils.library.restartPython()
    

# COMMAND ----------


# ------------------------------------------------------------------
# Setup: Initialize the OpenAI-compatible client for Databricks
# Note: this won't work on databricks free tier 
# ------------------------------------------------------------------

from openai import OpenAI


# Get auth from the notebook context (works on both classic clusters and serverless)
db_host = spark.conf.get("spark.databricks.workspaceUrl")
print(db_host)

# COMMAND ----------

db_token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# COMMAND ----------

db_token

# COMMAND ----------

# Note: this won't work on databricks free tier 

client = OpenAI(
    api_key=db_token,
    base_url=f"{f'https://{db_host}'}/serving-endpoints"
)

MODEL = "databricks-meta-llama-3-3-70b-instruct"

print("Client initialized successfully.")
print(f"Model: {MODEL}")
print(f"Endpoint: {f'https://{db_host}'}/serving-endpoints")

# COMMAND ----------

# MAGIC %md
# MAGIC Above end point is not opening, So follow below steps: <br>
# MAGIC
# MAGIC
# MAGIC **Generate a Free Token in Databricks**
# MAGIC
# MAGIC 1. Look at the top right corner of your Databricks Free Edition screen and click on your User Profile email.
# MAGIC 2. Select Settings from the menu.
# MAGIC 3. Click on the Developer tab on the left sidebar.
# MAGIC 4. Next to Access tokens, click the Manage button.
# MAGIC 5. Click Generate new token, give it a name (e.g., genai-test), and click Generate.
# MAGIC
# MAGIC Update Your Code (The Free Edition Workaround) with below cell
# MAGIC

# COMMAND ----------

# MAGIC %pip install databricks-openai
# MAGIC

# COMMAND ----------

# Restart Python to pick up the new package
dbutils.library.restartPython()

# COMMAND ----------

import os
import getpass
from databricks_openai import DatabricksOpenAI

print("🔒 Step 1: Registering credentials...")
token_input = getpass.getpass("Paste your 'dapi...' token and press Enter: ")

if not token_input.strip():
    raise ValueError("Token entry cannot be blank.")

# 1. Establish environment variables
workspace_host = f"https://{spark.conf.get('spark.databricks.workspaceUrl')}"
os.environ["DATABRICKS_TOKEN"] = token_input.strip()
os.environ["DATABRICKS_HOST"] = workspace_host

# 2. Initialize the official client wrapper
client = DatabricksOpenAI()
MODEL = "databricks-meta-llama-3-1-70b-instruct"

# 3. Print verification info alongside the target endpoint path
print("\n✅ Client initialized successfully using native workspace credentials!")
print(f"Target Model:  {MODEL}")
print(f"Target Host:   {workspace_host}")
print(f"Base Endpoint: {workspace_host}/serving-endpoints")


# COMMAND ----------

# ------------------------------------------------------------------
# Step 1: Build the NLP task taxonomy as a reference DataFrame
# ------------------------------------------------------------------

import pandas as pd

task_taxonomy = pd.DataFrame([
    {
        "Task Type": "Summarization",
        "Description": "Condense long text into a shorter version that preserves key information",
        "Example Use Cases": "Meeting notes digest, article summaries, contract highlights",
        "Example Prompt Pattern": "Summarize the following text in 3 sentences: {text}",
        "Kitchen Analogy": "Blender -- reduces many ingredients into a smooth result"
    },
    {
        "Task Type": "Text Classification",
        "Description": "Assign one or more labels/categories to a piece of text",
        "Example Use Cases": "Sentiment analysis, spam detection, support ticket routing",
        "Example Prompt Pattern": "Classify the sentiment of this review as positive, negative, or neutral: {text}",
        "Kitchen Analogy": "Label maker -- sorts things into categories"
    },
    {
        "Task Type": "Text Generation",
        "Description": "Produce new text from a prompt -- the most general task type",
        "Example Use Cases": "Drafting emails, writing code, creative content, chatbot responses",
        "Example Prompt Pattern": "Write a professional email declining a meeting invitation.",
        "Kitchen Analogy": "Writing desk -- creates something new from an idea"
    },
    {
        "Task Type": "Question Answering",
        "Description": "Answer a question based on provided context or general knowledge",
        "Example Use Cases": "FAQ bots, document Q&A, RAG pipelines, customer support",
        "Example Prompt Pattern": "Based on the following context, answer the question.\nContext: {context}\nQuestion: {question}",
        "Kitchen Analogy": "Reference librarian -- finds the answer in a body of knowledge"
    },
    {
        "Task Type": "Feature Extraction",
        "Description": "Generate embeddings (dense vector representations) from text",
        "Example Use Cases": "Semantic search, similarity matching, clustering, vector databases",
        "Example Prompt Pattern": "(No prompt -- you call an embedding endpoint that returns a vector)",
        "Kitchen Analogy": "X-ray machine -- reveals hidden internal structure"
    },
    {
        "Task Type": "Token Classification",
        "Description": "Label individual tokens (words/subwords) within text",
        "Example Use Cases": "Named Entity Recognition (NER), POS tagging, detecting PII",
        "Example Prompt Pattern": "Identify all person names, organizations, and locations in this text: {text}",
        "Kitchen Analogy": "Highlighter -- marks specific parts of text"
    },
    {
        "Task Type": "Text2Text Generation",
        "Description": "Transform text from one form to another (input text --> output text)",
        "Example Use Cases": "Translation, paraphrasing, grammar correction, format conversion",
        "Example Prompt Pattern": "Translate the following English text to French: {text}",
        "Kitchen Analogy": "Translator -- transforms from one form to another"
    }
])

# Display the full table nicely
pd.set_option("display.max_colwidth", 80)
pd.set_option("display.max_columns", 6)
display(task_taxonomy)

# COMMAND ----------

# ------------------------------------------------------------------
# Step 2: Interactive quiz -- map business scenarios to task types
# ------------------------------------------------------------------

# Define the six scenarios the exam commonly tests
scenarios = [
    {
        "id": 1,
        "scenario": (
            "A legal team has 500-page contracts and needs a 1-page executive "
            "summary of each contract highlighting key terms and obligations."
        ),
        "answer": "Summarization",
        "explanation": (
            "The task is to CONDENSE long text into shorter text while preserving "
            "key information. This is the textbook definition of summarization. "
            "The input is long (500 pages), the output is short (1 page)."
        )
    },
    {
        "id": 2,
        "scenario": (
            "A customer support team receives thousands of tickets daily and needs "
            "each ticket automatically routed to the right department (billing, "
            "technical, shipping, general)."
        ),
        "answer": "Text Classification",
        "explanation": (
            "The task is to assign a CATEGORY (billing, technical, shipping, general) "
            "to each ticket. This is text classification -- the model reads the text "
            "and outputs a label. The key signal is 'routing to departments' = categories."
        )
    },
    {
        "id": 3,
        "scenario": (
            "A healthcare company needs to scan clinical notes and identify all "
            "mentions of patient names, medication names, and dosages."
        ),
        "answer": "Token Classification",
        "explanation": (
            "The task is to label INDIVIDUAL WORDS (tokens) within the text -- "
            "'Dr. Smith' = PERSON, 'Aspirin' = MEDICATION, '500mg' = DOSAGE. "
            "This is Named Entity Recognition (NER), which is a type of token "
            "classification. The key signal is 'identify mentions' of specific entity types."
        )
    },
    {
        "id": 4,
        "scenario": (
            "An e-commerce company wants to build a semantic search engine where "
            "users can search products by meaning (e.g., 'comfortable shoes for "
            "standing all day') rather than exact keyword match."
        ),
        "answer": "Feature Extraction",
        "explanation": (
            "Semantic search requires EMBEDDINGS -- vector representations of text that "
            "capture meaning. The model converts product descriptions and search queries "
            "into vectors, then finds the closest matches. Feature extraction = embeddings. "
            "The key signal is 'semantic search' or 'meaning-based similarity'."
        )
    },
    {
        "id": 5,
        "scenario": (
            "A multinational company needs to convert all their English product "
            "manuals into Spanish, French, and German for regional markets."
        ),
        "answer": "Text2Text Generation",
        "explanation": (
            "Translation is the canonical example of Text2Text generation -- you have "
            "input text in one form (English) and you transform it into another form "
            "(Spanish/French/German). The meaning is preserved, but the form changes. "
            "The key signal is 'convert' or 'translate' from one form to another."
        )
    },
    {
        "id": 6,
        "scenario": (
            "A knowledge base has 10,000 articles. Users ask natural language "
            "questions and the system should find the answer within the relevant "
            "article and return a direct answer."
        ),
        "answer": "Question Answering",
        "explanation": (
            "The task is to ANSWER A QUESTION based on a provided CONTEXT (the articles). "
            "This is extractive or generative QA -- the model reads the article and "
            "produces an answer grounded in that context. The key signal is 'ask questions' "
            "+ 'find the answer within' a document."
        )
    }
]


def run_task_quiz(scenarios):
    """Run an interactive quiz that presents business scenarios and checks answers."""
    valid_tasks = [
        "Summarization", "Text Classification", "Text Generation",
        "Question Answering", "Feature Extraction",
        "Token Classification", "Text2Text Generation"
    ]
    score = 0
    total = len(scenarios)

    print("=" * 70)
    print("  TASK MAPPING QUIZ -- Map each scenario to the correct NLP task")
    print("=" * 70)
    print(f"\nValid task types: {', '.join(valid_tasks)}\n")

    for s in scenarios:
        print(f"--- Scenario {s['id']} of {total} ---")
        print(f"  {s['scenario']}")
        print()

        # Interactive: prompt the user for their guess, then check it
        user_answer = input("Your answer: ").strip()

        if user_answer.lower() == s["answer"].lower():
            print("\n  ✅ CORRECT!\n")
            score += 1
        else:
            print(f"\n  ❌ Not quite. The correct answer is: {s['answer']}\n")

        print(f"  WHY: {s['explanation']}")
        print()

    print("=" * 70)
    print(f"  Quiz complete! Your score: {score} / {total}")
    print("=" * 70)


run_task_quiz(scenarios)

# COMMAND ----------

import mlflow.deployments

# 1. Initialize the built-in free tier MLflow driver 
mlflow_client = mlflow.deployments.get_deploy_client("databricks")

print("Scanning active foundation model endpoints on your workspace shard...")
MODEL = None

try:
    # list_endpoints returns a list of dictionaries in this Databricks runtime
    endpoints_raw = mlflow_client.list_endpoints()
    
    # Let's cleanly extract the names from the dictionary structures
    active_endpoints = [e.get("name") for e in endpoints_raw if isinstance(e, dict)]
    print(f"✨ Found Active Workspace Endpoints: {active_endpoints}")
    
    # Target any available instruct or chat model listed in your free workspace
    target_keywords = ["llama", "dbrx", "mixtral", "instruct", "chat"]
    for endpoint in active_endpoints:
        if endpoint and any(kw in endpoint.lower() for kw in target_keywords):
            MODEL = endpoint
            break
            
    # Absolute last-resort modern fallback string if the list is completely blank
    if not MODEL:
        if active_endpoints:
            MODEL = active_endpoints[0]  # Grab whatever text engine is online
        else:
            MODEL = "databricks-meta-llama-3-1-405b-instruct"
        
    print(f"🎯 Connected Successfully to: '{MODEL}'\n")

except Exception as err:
    print(f"⚠️ Parsing issue: {err}")
    MODEL = "databricks-meta-llama-3-1-405b-instruct"
    print(f"Using default fallback name: {MODEL}\n")

# 2. Main Operational Inference Routine
def run_inference(prompt, system_msg="You are a precise assistant. Follow instructions exactly."):
    """Helper function mapping OpenAI payloads into the local MLflow dictionary contract."""
    try:
        response = mlflow_client.predict(
            endpoint=MODEL,
            inputs={
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.0
            }
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Execution Error: {e}"

# ------------------------------------------------------------------
# Step 3a: Demonstrate task types using the same LLM with different prompts
# ------------------------------------------------------------------
sample_text = (
    "Apple Inc. reported record quarterly revenue of $123.9 billion for Q1 2024, "
    "driven by strong iPhone sales in emerging markets. CEO Tim Cook announced "
    "plans to expand manufacturing operations in Vietnam and India. The company "
    "also unveiled a new AI initiative called 'Apple Intelligence' that will be "
    "integrated across all devices starting with iOS 18. Analysts from Goldman "
    "Sachs and Morgan Stanley maintained their 'buy' ratings, citing strong "
    "services revenue growth of 11% year-over-year. However, sales in China "
    "declined 13% due to increased competition from Huawei."
)

task_demos = {
    "Summarization": f"Summarize the following text in exactly 2 sentences:\n\n{sample_text}",
    "Text Classification": f"Classify the overall sentiment of the following text as POSITIVE, NEGATIVE, or MIXED. Respond with only the label.\n\n{sample_text}",
    "Text Generation": "Write a 3-sentence LinkedIn post announcing a new AI product launch for a tech company. Keep it professional and exciting.",
    "Question Answering": f"Based on the following context, answer the question.\n\nContext: {sample_text}\n\nQuestion: Why did sales decline in China?",
    "Token Classification (NER)": f"Identify all named entities in the following text. For each entity, provide the entity text and its type (PERSON, ORGANIZATION, LOCATION, DATE, MONEY). Format as a list.\n\n{sample_text}",
    "Text2Text Generation": f"Translate the following text to French:\n\nApple reported record revenue driven by strong iPhone sales. The company plans to expand operations in Vietnam and India."
}

print("=" * 70)
print("  SAME MODEL, DIFFERENT TASKS -- Prompt is what drives behavior")
print("=" * 70)

for task_name, prompt in task_demos.items():
    result = run_inference(prompt)
    print(f"\n--- {task_name} ---")
    print(f"Result: {result}")


# COMMAND ----------

# ------------------------------------------------------------------
# Step 3b: Feature Extraction (embeddings) -- requires an embedding model
# ------------------------------------------------------------------

# Feature extraction is different: instead of generating text,
# it generates a numerical vector (embedding) that captures the
# meaning of the text. This is used for semantic search, similarity,
# and vector databases.

import mlflow.deployments
import math

# 1. Initialize the built-in free tier MLflow driver 
mlflow_client = mlflow.deployments.get_deploy_client("databricks")

# 2. Dynamic Discovery: Scan for active embedding models on your shard
print("Scanning active embedding endpoints on your workspace shard...")
EMBEDDING_MODEL = None

try:
    endpoints_raw = mlflow_client.list_endpoints()
    active_endpoints = [e.get("name") for e in endpoints_raw if isinstance(e, dict)]
    
    # Target standard, free-tier embedding pipelines (bge, gte, or embedding models)
    target_keywords = ["gte", "bge", "embedding"]
    for endpoint in active_endpoints:
        if endpoint and any(kw in endpoint.lower() for kw in target_keywords):
            EMBEDDING_MODEL = endpoint
            break
            
    # Absolute last-resort modern fallback string if the workspace list is masked
    if not EMBEDDING_MODEL:
        if active_endpoints:
            EMBEDDING_MODEL = active_endpoints[0]
        else:
            EMBEDDING_MODEL = "databricks-bge-large-en"
            
    print(f"🎯 Connected Successfully to Embedding Model: '{EMBEDDING_MODEL}'\n")

except Exception as err:
    EMBEDDING_MODEL = "databricks-bge-large-en"
    print(f"⚠️ Falling back to default baseline embedding routing: {err}\n")

# 3. Main Operational Vector Extraction Routine
def get_embeddings(texts):
    """Helper function mapping embedding payloads into the local MLflow dictionary contract."""
    try:
        response = mlflow_client.predict(
            endpoint=EMBEDDING_MODEL,
            inputs={
                "input": texts
            }
        )
        # Safely parse out the raw nested floating point vector array from the data response
        # MLflow structures embeddings inside a list array under the 'data' key object block
        vectors = [item["embedding"] for item in response["data"]]
        return vectors
    except Exception as e:
        print(f"❌ Core Vector Extraction Failed: {e}")
        return None

# ------------------------------------------------------------------
# Step 3b: Feature Extraction and Semantic Closeness Testing
# ------------------------------------------------------------------

texts_to_embed = [
    "Apple reported record revenue from iPhone sales.",
    "The tech company saw strong smartphone earnings.",
    "I love cooking Italian pasta on weekends."
]

# Extract vectors using our tuned MLflow pipeline
extracted_vectors = get_embeddings(texts_to_embed)

if extracted_vectors:
    print("=== Feature Extraction (Embeddings) ===")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Number of texts embedded: {len(texts_to_embed)}")
    print(f"Embedding dimension: {len(extracted_vectors[0])}")
    print()

    for i, text in enumerate(texts_to_embed):
        vec = extracted_vectors[i]
        print(f"Text {i+1}: \"{text}\"")
        print(f"  Vector (first 5 dims): {[round(v, 4) for v in vec[:5]]}...")
        print()

    # Compute cosine similarity to show semantic closeness
    def cosine_similarity(a, b):
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    vec_0 = extracted_vectors[0]
    vec_1 = extracted_vectors[1]
    vec_2 = extracted_vectors[2]

    sim_01 = cosine_similarity(vec_0, vec_1)
    sim_02 = cosine_similarity(vec_0, vec_2)

    print("=== Semantic Similarity ===")
    print(f"Text 1 vs Text 2 (both about tech revenue): {sim_01:.4f}")
    print(f"Text 1 vs Text 3 (tech revenue vs cooking):  {sim_02:.4f}")
    print()
    print("The two tech-related sentences are semantically closer (higher similarity)")
    print("than the tech sentence vs the cooking sentence. This is what powers")
    print("semantic search -- find documents with similar MEANING, not just keywords.")
else:
    print("Execution halted due to extraction setup mismatch.")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3c: Deep Dive — Feature Extraction and Token Classification
# MAGIC
# MAGIC The table in **Step 1** gives you short descriptions. But two task types deserve a deeper explanation, because the exam tests *what they are*, *how they work under the hood*, and *how they differ from each other*.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 📐 Feature Extraction: Turning Text into Numbers
# MAGIC
# MAGIC Machine learning models cannot read text — they need **numbers**. Feature extraction is the process of converting text into numerical representations that capture its meaning.
# MAGIC
# MAGIC There are **three generations** of techniques:
# MAGIC
# MAGIC | Generation | Technique | How It Works | Captures Meaning? |
# MAGIC |:---:|:---|:---|:---|
# MAGIC | **1st** | Bag of Words (BoW) | Count how many times each word appears in a document. Each word = one column. | ❌ **No** — ignores word order and context. *"dog bites man" = "man bites dog"* |
# MAGIC | **2nd** | TF-IDF | Like BoW, but downweights common words (*"the"*, *"a"*) and upweights rare, informative words. | ⚠️ **Slightly** — rare words get higher scores, but still no context. |
# MAGIC | **3rd** | Embeddings (transformers) | A neural network reads the *full sentence* and outputs a **dense vector** (e.g., 1024 numbers) that encodes the meaning of the text. | ✅ **Yes** — *"happy"* and *"joyful"* get similar vectors. |
# MAGIC
# MAGIC #### 💡 Key Exam Point
# MAGIC > Only **embeddings** (feature extraction) capture *meaning*. BoW and TF-IDF just count words — two sentences with the same words but opposite meanings get identical representations.

# COMMAND ----------

# ==================================================================
# Step 3c: Feature Extraction and Token Classification -- Deep Dive
# ==================================================================
import math
from collections import Counter
import mlflow.deployments

# 1. Initialize the built-in free tier MLflow driver 
mlflow_client = mlflow.deployments.get_deploy_client("databricks")

# 2. Dynamic Discovery: Scan for active embedding models on your shard
print("Scanning active embedding endpoints on your workspace shard...")
EMBEDDING_MODEL = None

try:
    endpoints_raw = mlflow_client.list_endpoints()
    active_endpoints = [e.get("name") for e in endpoints_raw if isinstance(e, dict)]
    
    # Target standard, free-tier embedding pipelines
    target_keywords = ["gte", "bge", "embedding"]
    for endpoint in active_endpoints:
        if endpoint and any(kw in endpoint.lower() for kw in target_keywords):
            EMBEDDING_MODEL = endpoint
            break
            
    if not EMBEDDING_MODEL:
        EMBEDDING_MODEL = active_endpoints if active_endpoints else "databricks-bge-large-en"
    print(f"🎯 Connected Successfully to Embedding Model: '{EMBEDDING_MODEL}'\n")

except Exception as err:
    EMBEDDING_MODEL = "databricks-bge-large-en"
    print(f"⚠️ Falling back to default baseline embedding routing: {err}\n")

# 3. Helper Function to calculate Cosine Similarity
def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# ── PART 1: Three Generations of Feature Extraction ────────────────

docs = [
    "The cat sat on the mat",
    "A kitten rested on a rug",
    "Stock prices fell sharply today",
]

# --- Bag of Words ---
def bag_of_words(documents):
    vocab = sorted(set(w for doc in documents for w in doc.lower().split()))
    matrix = []
    for doc in documents:
        words = doc.lower().split()
        row = [words.count(w) for w in vocab]
        matrix.append(row)
    return vocab, matrix

vocab, bow_matrix = bag_of_words(docs)

print("=" * 70)
print("GENERATION 1: Bag of Words (BoW)")
print("=" * 70)
print(f"\n  Vocabulary ({len(vocab)} words): {vocab}")
print(f"\n  {'Document':<35} Vector")
print(f"  {'-' * 65}")
for doc, row in zip(docs, bow_matrix):
    print(f"  {doc:<35} {row}")
print(f"\n  Problem: 'cat sat on mat' and 'kitten rested on rug' look VERY")
print(f"  different (almost no overlap), even though they mean the same thing.")

# --- TF-IDF ---
def compute_tfidf(documents):
    vocab = sorted(set(w for doc in documents for w in doc.lower().split()))
    N = len(documents)
    df = {}
    for w in vocab:
        df[w] = sum(1 for doc in documents if w in doc.lower().split())
    
    results = []
    for doc in documents:
        words = doc.lower().split()
        total = len(words)
        row = {}
        for w in vocab:
            tf = words.count(w) / total
            idf = math.log(N / df[w]) if df[w] > 0 else 0
            row[w] = round(tf * idf, 3)
        results.append(row)
    return vocab, results

vocab_tfidf, tfidf_results = compute_tfidf(docs)

print(f"\n{'=' * 70}")
print("GENERATION 2: TF-IDF")
print("=" * 70)
print(f"\n  TF-IDF scores (0 = common/absent, higher = more informative):")
for doc, scores in zip(docs, tfidf_results):
    nonzero = {k: v for k, v in scores.items() if v > 0}
    print(f"\n  '{doc}'")
    for word, score in sorted(nonzero.items(), key=lambda x: -x[1]):
        bar = '#' * int(score * 40)
        print(f"    {word:<12} {score:.3f}  {bar}")
print(f"\n  Notice: 'on' scores low (appears in 2/3 docs = common).")
print(f"  Words like 'cat', 'kitten', 'stock' score higher (unique to 1 doc).")
print(f"  But TF-IDF STILL doesn't know 'cat' and 'kitten' are related!")

# --- Embeddings ---
print(f"\n{'=' * 70}")
print("GENERATION 3: Transformer Embeddings")
print("=" * 70)

try:
    # Query the local workspace embedding pipeline using MLflow syntax
    response = mlflow_client.predict(
        endpoint=EMBEDDING_MODEL,
        inputs={"input": docs}
    )
    
    # Safely extract the raw nested vector arrays from the prediction dictionary payload
    vecs = [item["embedding"] for item in response["data"]]

    sim_01 = cosine_similarity(vecs[0], vecs[1])
    sim_02 = cosine_similarity(vecs[0], vecs[2])
    sim_12 = cosine_similarity(vecs[1], vecs[2])

    print(f"\n  Cosine similarities (embeddings capture MEANING):")
    print(f"    'cat sat on mat' vs 'kitten rested on rug': {sim_01:.4f}  <- SIMILAR meaning")
    print(f"    'cat sat on mat' vs 'stock prices fell':     {sim_02:.4f}  <- DIFFERENT topic")
    print(f"    'kitten on rug'  vs 'stock prices fell':     {sim_12:.4f}  <- DIFFERENT topic")
    print(f"\n  Embeddings KNOW that 'cat' and 'kitten' are related!")
    print(f"  BoW and TF-IDF cannot do this.")

except Exception as e:
    print(f"❌ Embedding Generation Failed: {e}")

print(f"\n  {'Method':<25} {'Understands synonyms?':<25} {'Understands context?'}")
print(f"  {'-' * 70}")
print(f"  {'Bag of Words':<25} {'No':<25} {'No'}")
print(f"  {'TF-IDF':<25} {'No':<25} {'No'}")
print(f"  {'Embeddings':<25} {'YES':<25} {'YES'}")


# COMMAND ----------

# ==================================================================
# PART 2: Token Classification Deep Dive (Fixed & Verified)
# ==================================================================
import mlflow.deployments

# 1. Initialize the built-in free tier MLflow driver
mlflow_client = mlflow.deployments.get_deploy_client("databricks")

# 2. Dynamic Discovery: Scan for active instruct/chat models on your shard
MODEL_NAME = None
try:
    endpoints_raw = mlflow_client.list_endpoints()
    active_endpoints = [e.get("name") for e in endpoints_raw if isinstance(e, dict)]
    
    target_keywords = ["llama", "dbrx", "mixtral", "instruct", "chat"]
    for endpoint in active_endpoints:
        if endpoint and any(kw in endpoint.lower() for kw in target_keywords):
            MODEL_NAME = endpoint
            break
            
    if not MODEL_NAME:
        MODEL_NAME = active_endpoints[0] if active_endpoints else "databricks-meta-llama-3-1-405b-instruct"
    print(f"🎯 Token Engine Connected Successfully to: '{MODEL_NAME}'\n")
except Exception as err:
    MODEL_NAME = "databricks-meta-llama-3-1-405b-instruct"
    print(f"⚠️ Falling back to baseline model routing: {err}\n")

# 3. Fixed Inference Routine for Text Generation
def run_token_inference(prompt, max_tokens=500):
    """Helper function mapping token-classification requests into local MLflow text contracts."""
    try:
        response = mlflow_client.predict(
            endpoint=MODEL_NAME,
            inputs={
                "messages": [
                    {"role": "system", "content": "You are a precise technical assistant. Output exactly as formatted without conversational filler."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.0
            }
        )
        
        # FIX: Check if the response is wrapped in an OpenAI-style 'choices' key list dictionary
        if "choices" in response:
            return response["choices"][0]["message"]["content"].strip()
        # Alternative basic text model response structure
        elif "candidates" in response:
            return response["candidates"][0]["message"]["content"].strip()
        else:
            return str(response).strip()
            
    except Exception as e:
        return f"Execution Error: {e}"

# ------------------------------------------------------------------
# Execution Loops: Named Entity Recognition & Part-of-Speech Tagging
# ------------------------------------------------------------------

print(f"\n{'=' * 70}")
print("TOKEN CLASSIFICATION: Labeling Each Word Individually")
print("=" * 70)

# Use the LLM to demonstrate NER
ner_text = (
    "Tim Cook announced that Apple will expand operations in Vietnam "
    "and India. Goldman Sachs maintained a buy rating on January 15, 2025."
)

ner_prompt = (
    f"Perform Named Entity Recognition on the following text. "
    f"For EVERY word, output the word followed by its NER tag. "
    f"Use these tags: PERSON, ORG, LOC, DATE, MONEY, O (no entity).\n\n"
    f"Text: {ner_text}\n\n"
    f"Format each word on its own line as: word -> TAG"
)

# Call the local MLflow driver for NER processing
ner_output = run_token_inference(ner_prompt, max_tokens=500)

print(f"\n  --- Named Entity Recognition (NER) ---")
print(f"  Input: \"{ner_text}\"")
print(f"\n  NER Output (each token gets a label):")
for line in ner_output.split('\n')[:15]:
    print(f"    {line}")


# POS tagging demo
pos_prompt = (
    f"Perform Part-of-Speech tagging on: 'The cat sat on the mat.'\n\n"
    f"For each word, output: word -> POS_TAG\n"
    f"Use standard POS tags: DET, NOUN, VERB, ADP, PUNCT, etc."
)

# Call the local MLflow driver for POS processing
pos_output = run_token_inference(pos_prompt, max_tokens=200)

print(f"\n  --- Part-of-Speech (POS) Tagging ---")
print(f"  Input: 'The cat sat on the mat.'")
print(f"\n  POS Output (grammatical role of each word):")
for line in pos_output.split('\n')[:8]:
    print(f"    {line}")


# COMMAND ----------

# Summary comparison
print(f"\n{'=' * 70}")
print("TEXT CLASSIFICATION vs TOKEN CLASSIFICATION")
print("=" * 70)
print(f"""
  Text Classification (whole document -> one label):
    Input:  "This movie is amazing!"  ->  POSITIVE
    Input:  "Terrible service, rude staff"  ->  NEGATIVE
    Use for: sentiment analysis, spam detection, topic routing

  Token Classification (each word -> its own label):
    Input:  "Tim Cook announced Apple's expansion into Vietnam"
            Tim Cook -> PERSON,  Apple -> ORG,  Vietnam -> LOC
    Use for: NER, POS tagging, PII detection, invoice extraction

  The KEY difference: scope of the label.
    Text Classification = ONE label for the WHOLE text.
    Token Classification = ONE label PER WORD.
""")

# COMMAND ----------

# ------------------------------------------------------------------
# Step 4a: What Sentencizer actually does (spaCy sentence splitting)
# ------------------------------------------------------------------

# NOTE: This cell demonstrates what Sentencizer IS -- a simple rule-based
# sentence splitter, NOT an LLM task. We're showing this so you understand
# why it's a trap answer on the exam.

# You do NOT need spaCy installed to understand this concept.
# Here's what the Sentencizer does, implemented from scratch:

def simple_sentencizer(text):
    """Rule-based sentence boundary detection -- this is what spaCy's
    Sentencizer does. It splits text on punctuation boundaries.
    No ML involved -- just pattern matching."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s]

sample = (
    "Apple Inc. reported record revenue. Tim Cook announced expansion plans. "
    "The stock price rose 3% in after-hours trading! Will the trend continue?"
)

sentences = simple_sentencizer(sample)

print("=== Sentencizer Demo (Rule-Based Sentence Splitting) ===")
print(f"Input text: \"{sample}\"")
print(f"\nDetected {len(sentences)} sentences:")
for i, sent in enumerate(sentences, 1):
    print(f"  {i}. {sent}")

print("\n" + "=" * 70)
print("NOTICE: This is just text splitting. No understanding, no intelligence.")
print("A Sentencizer does NOT classify, summarize, generate, or answer anything.")
print("It is a pre-processing utility, NOT a model task.")
print("=" * 70)

# COMMAND ----------

# ------------------------------------------------------------------
# Step 4b: Contrast -- what an actual LLM task does with the same text
# ------------------------------------------------------------------

# Let's compare: Sentencizer (rule-based splitting) vs actual NLP tasks
# applied to the same text. This shows the qualitative difference.

# ==================================================================
# Step 3d: Sentencizer vs Actual NLP Tasks (Free Tier Optimized)
# ==================================================================
import mlflow.deployments
import re

# 1. Initialize the built-in free tier MLflow driver 
mlflow_client = mlflow.deployments.get_deploy_client("databricks")

# 2. Dynamic Discovery: Map the active text model running on your shard
MODEL = None
try:
    endpoints_raw = mlflow_client.list_endpoints()
    active_endpoints = [e.get("name") for e in endpoints_raw if isinstance(e, dict)]
    
    target_keywords = ["llama", "dbrx", "mixtral", "instruct", "chat"]
    for endpoint in active_endpoints:
        if endpoint and any(kw in endpoint.lower() for kw in target_keywords):
            MODEL = endpoint
            break
            
    if not MODEL:
        MODEL = active_endpoints[0] if active_endpoints else "databricks-meta-llama-3-1-405b-instruct"
except Exception:
    MODEL = "databricks-meta-llama-3-1-405b-instruct"

# 3. Rule-based Text Splitter (Simulating basic rule-based NLP)
def simple_sentencizer(text):
    """Splits text by punctuation boundaries using basic regex matching."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

# 4. Main Operational Inference Routine Wrapper
def run_comparison_inference(prompt):
    """Helper function mapping comparison prompts into local MLflow dictionary contracts."""
    try:
        response = mlflow_client.predict(
            endpoint=MODEL,
            inputs={
                "messages": [
                    {"role": "system", "content": "You are a precise technical assistant. Output exactly as requested without filler."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 150,
                "temperature": 0.0
            }
        )
        # Handle dict extraction paths cleanly
        if "choices" in response:
            return response["choices"][0]["message"]["content"].strip()
        else:
            return str(response).strip()
    except Exception as e:
        return f"Execution Error: {e}"

# ------------------------------------------------------------------
# Comparison Execution Flow
# ------------------------------------------------------------------

sample_for_comparison = (
    "Apple Inc. reported record revenue. Tim Cook announced expansion plans. "
    "The stock price rose 3% in after-hours trading."
)

comparison_tasks = {
    "Summarization": f"Summarize in one sentence: {sample_for_comparison}",
    "Text Classification": (
        f"Classify the sentiment as POSITIVE, NEGATIVE, or NEUTRAL. "
        f"Respond with only the label.\n\n{sample_for_comparison}"
    ),
    "Token Classification": (
        f"List all named entities (PERSON, ORG, PERCENTAGE) in this text:\n\n"
        f"{sample_for_comparison}"
    )
}

print("=== Sentencizer vs Actual NLP Tasks ===")
print(f"\nInput: \"{sample_for_comparison}\"\n")

# Sentencizer output (Rule-Based, Non-LLM execution path)
print("--- Sentencizer (rule-based, NOT an LLM task) ---")
sents = simple_sentencizer(sample_for_comparison)
for s in sents:
    print(f"  Sentence: {s}")
print("  (Just splits text. No understanding.)\n")

# Actual LLM task outputs running via local drivers
for task_name, prompt in comparison_tasks.items():
    result = run_comparison_inference(prompt)
    print(f"--- {task_name} (real LLM task) ---")
    print(f"  {result}")
    print()


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Multilingual Tokenization and Its Impact on Vectorization
# MAGIC
# MAGIC When you embed text for semantic search or RAG, the tokenizer silently determines how well your model handles different languages. This is critical for multilingual applications and frequently overlooked.
# MAGIC
# MAGIC ### 🌍 The Problem
# MAGIC
# MAGIC Tokenizers are trained on a **vocabulary** (often ~30K–100K tokens). If the training data was mostly English, the tokenizer learns efficient English tokens (`"running"` → **1 token**) but splits unfamiliar languages into many small fragments (`"laufend"` → `"l"`, `"auf"`, `"end"` → **3 tokens**).
# MAGIC
# MAGIC This matters because:
# MAGIC
# MAGIC | Effect | Consequence |
# MAGIC |:---|:---|
# MAGIC | **More tokens** | Higher cost — you pay per token |
# MAGIC | **More tokens** | Less context fits in the model's context window |
# MAGIC | **Fragmented tokens** | Worse embeddings — the model never saw these fragments as meaningful units |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 📊 Tokenizer Efficiency by Training Data
# MAGIC
# MAGIC | Tokenizer Trained On | English Text | Japanese Text | Arabic Text |
# MAGIC |:---|:---:|:---:|:---:|
# MAGIC | **Mostly English data** | ✅ Efficient (few tokens) | ⚠️ Fragmented (many tokens) | ⚠️ Fragmented (many tokens) |
# MAGIC | **Multilingual data** | ✅ Efficient | ✅ Efficient | ✅ Efficient |
# MAGIC Tokenizer Trained On	English Text	Japanese Text	Arabic Text
# MAGIC Mostly English data	Efficient (few tokens)	Fragmented (many tokens)	Fragmented (many tokens)
# MAGIC Multilingual data	Efficient	Efficient	Efficient
# MAGIC ### 💡 Analogy
# MAGIC
# MAGIC > Imagine a **filing system** designed for English documents. Filing an English letter is easy — one slot. But a Chinese scroll gets awkwardly folded and stuffed into multiple slots because the system wasn't designed for it. A **multilingual filing system** has proper slots for all formats.

# COMMAND ----------

# ==================================================================
# Step 5a: Multilingual Embedding Comparison (Free Tier Optimized)
# ==================================================================
import mlflow.deployments

# 1. Initialize the built-in free tier MLflow driver 
mlflow_client = mlflow.deployments.get_deploy_client("databricks")

# 2. Dynamic Discovery: Scan for active embedding models on your shard
print("Scanning active embedding endpoints on your workspace shard...")
EMBEDDING_MODEL = None

try:
    endpoints_raw = mlflow_client.list_endpoints()
    active_endpoints = [e.get("name") for e in endpoints_raw if isinstance(e, dict)]
    
    # Target standard, free-tier embedding pipelines
    target_keywords = ["gte", "bge", "embedding"]
    for endpoint in active_endpoints:
        if endpoint and any(kw in endpoint.lower() for kw in target_keywords):
            EMBEDDING_MODEL = endpoint
            break
            
    if not EMBEDDING_MODEL:
        EMBEDDING_MODEL = active_endpoints if active_endpoints else "databricks-bge-large-en"
    print(f"🎯 Connected Successfully to Embedding Model: '{EMBEDDING_MODEL}'\n")

except Exception as err:
    EMBEDDING_MODEL = "databricks-bge-large-en"
    print(f"⚠️ Falling back to default baseline embedding routing: {err}\n")

# 3. Main Operational Vector Extraction Routine
def get_multilingual_embeddings(texts_list):
    """Helper function mapping embedding payloads into the local MLflow dictionary contract."""
    try:
        response = mlflow_client.predict(
            endpoint=EMBEDDING_MODEL,
            inputs={
                "input": texts_list
            }
        )
        # Safely parse out the raw nested floating point vector array from the data response
        vectors = [item["embedding"] for item in response["data"]]
        return vectors
    except Exception as e:
        print(f"❌ Core Vector Extraction Failed: {e}")
        return None

# ------------------------------------------------------------------
# Multilingual Dataset Processing Execution Loop
# ------------------------------------------------------------------

multilingual_samples = {
    "English":    "The quick brown fox jumps over the lazy dog.",
    "German":     "Der schnelle braune Fuchs springt über den faulen Hund.",
    "French":     "Le rapide renard brun saute par-dessus le chien paresseux.",
    "Japanese":   "素早い茶色の狐が怠け者の犬を飛び越える。",
    "Arabic":     "الثعلب البني السريع يقفز فوق الكلب الكسول.",
    "Korean":     "빠른 갈색 여우가 게으른 개를 뛰어넘는다.",
}

texts = list(multilingual_samples.values())
labels = list(multilingual_samples.keys())

# Extract the cross-lingual vectors safely using our MLflow method
extracted_vectors = get_multilingual_embeddings(texts)

if extracted_vectors:
    print("=== Multilingual Embedding Comparison ===")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"All sentences say the same thing in different languages.\n")
    print(f"  {'Language':<10} | {'Chars':>5} | Text Sample")
    print(f"  {'-' * 65}")

    # Show character count alongside text mappings
    for i, (lang, text) in enumerate(multilingual_samples.items()):
        # Pull vector reference to ensure the embedding generation succeeded
        vec = extracted_vectors[i]
        print(f"  {lang:<10} | chars: {len(text):>3} | text: {text[:60]}")
    
    print(f"\n✅ All {len(extracted_vectors)} vectors extracted successfully.")
    print(f"Vector Dimensions per language: {len(extracted_vectors[0])} tokens.")
else:
    print("Execution halted due to extraction layout mismatch.")


# COMMAND ----------


# ------------------------------------------------------------------
# Step 5b: Measure cross-language semantic similarity
# ------------------------------------------------------------------

# If the embedding model handles a language well, the vector for
# "The quick brown fox..." in English should be CLOSE to the same
# sentence in German, French, etc. If it handles a language poorly,
# the vectors will drift apart.

# ==================================================================
# Step 5b: Cross-Language Similarity Analysis (Free Tier Optimized)
# ==================================================================
import math

# Use the native math block you defined
def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

# Extract the English baseline coordinates vector from index 0 of your array variable
if 'extracted_vectors' in locals() and extracted_vectors is not None:
    english_vec = extracted_vectors[0]

    print("=== Cross-Language Similarity (vs English) ===")
    print("If the model handles a language well, similarity should be high (>0.8).")
    print("Low similarity means the tokenizer/model struggles with that script style.\n")

    for i, (lang, text) in enumerate(multilingual_samples.items()):
        if i == 0:  # Skip evaluation of English against itself
            continue
            
        # Compute directional alignment against the language lists
        sim = cosine_similarity(english_vec, extracted_vectors[i])
        
        # Build a robust terminal-friendly alignment text bar
        bar = '#' * int(sim * 30)
        
        # Quantify vector thresholds for quality indicators
        quality = '✓ Good' if sim > 0.80 else '⚠ Weak' if sim > 0.60 else '✗ Poor'
        print(f"  English vs {lang:<10} | sim: {sim:.4f} | {bar:<30} | {quality}")

    print("\n" + "=" * 70)
    print("KEY INSIGHT: An English-focused embedding model (like GTE-Large-EN)")
    print("may produce weaker vectors for non-Latin scripts (CJK, Arabic, etc.).")
    print("For multilingual RAG, consider a multilingual model like:")
    print("  - multilingual-e5-large")
    print("  - paraphrase-multilingual-MiniLM")
    print("  - Cohere embed-multilingual-v3.0")
    print("=" * 70)
else:
    print("❌ Error: Missing active vector metrics array context. Re-run Step 5a first.")


# COMMAND ----------

# ==================================================================
# Step 5c: Visualize Tokenization Differences (Fixed & Verified)
# ==================================================================
import mlflow.deployments

# 1. Initialize the built-in free tier MLflow driver 
mlflow_client = mlflow.deployments.get_deploy_client("databricks")

print("Scanning active foundation model endpoints on your workspace shard...")
MODEL = None

try:
    # Fetch the endpoints payload structure
    endpoints_payload = mlflow_client.list_endpoints()
    
    # Extract the actual list of endpoints safely from the parent dictionary container
    endpoints_list = []
    if isinstance(endpoints_payload, dict) and "endpoints" in endpoints_payload:
        endpoints_list = endpoints_payload["endpoints"]
    elif isinstance(endpoints_payload, list):
        endpoints_list = endpoints_payload
        
    # Cleanly pull the string names out of each endpoint payload item
    active_endpoints = [e.get("name") for e in endpoints_list if isinstance(e, dict)]
    print(f"✨ Found Active Workspace Endpoints: {active_endpoints}")
    
    # Target any available instruct, chat, or llama text model running on your shard
    target_keywords = ["llama", "dbrx", "mixtral", "instruct", "chat"]
    for endpoint in active_endpoints:
        if endpoint and any(kw in endpoint.lower() for kw in target_keywords):
            MODEL = endpoint
            break
            
    # Absolute last-resort fallback string if the list is completely blank
    if not MODEL:
        MODEL = active_endpoints[0] if active_endpoints else "databricks-meta-llama-3-1-405b-instruct"
        
    print(f"🎯 Connected Successfully to Text Model: '{MODEL}'\n")

except Exception as err:
    print(f"⚠️ Parsing issue: {err}")
    MODEL = "databricks-meta-llama-3-1-405b-instruct"
    print(f"Using default fallback name: {MODEL}\n")

# 3. Main Operational Inference Routine Wrapper
def run_token_visualization(system_prompt, user_prompt):
    """Helper function mapping visualization prompts into local MLflow dictionary contracts."""
    try:
        response = mlflow_client.predict(
            endpoint=MODEL,
            inputs={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 400,
                "temperature": 0.0
            }
        )
        
        # Unpack the generated text response from the dictionary choices array securely
        if "choices" in response:
            return response["choices"][0]["message"]["content"].strip()
        elif "candidates" in response:
            return response["candidates"][0]["message"]["content"].strip()
        else:
            return str(response).strip()
            
    except Exception as e:
        return f"Execution Error: {e}"




# COMMAND ----------

# ------------------------------------------------------------------
# Execution of the Tokenization Visualization
# ------------------------------------------------------------------

print("=== How a BPE Tokenizer Splits Different Languages ===")
print("(Approximation — real tokenization depends on the specific model)\n")

# Dictated strict system prompt to force the exact requested layout
system_instruction = (
    "You are a tokenization expert. For each sentence, demonstrate how an English-focused "
    "BPE tokenizer fragments text. You must output only the language name, the tokens wrapped "
    "in [brackets], an arrow, and the token count. Do not include any introductory sentences, "
    "conversational filler, or explanations. Follow this exact template:\n"
    "Language: [token1] [token2] -> X tokens"
)

user_query = (
    "Show approximate BPE tokenization for these exact sentences based on the system layout:\n"
    "1. English: The quick brown fox\n"
    "2. German: Der schnelle braune Fuchs\n"
    "3. Japanese: 素早い茶色の狐\n"
    "4. Arabic: الثعلب البني السريع"
)

# Run the inference using the local driver configuration
output_text = run_token_visualization(system_instruction, user_query)
print(output_text)

print("\n" + "-" * 70)
print("TAKEAWAY SUMMARY:")
print("The LLM shows how English text gets cleanly tokenized into whole words/subwords, ")
print("while Japanese and Arabic text gets fragmented into individual characters or byte sequences.")
print("More tokens = higher API costs, smaller context window limits, and weaker vector space matching.")
print("-" * 70)



# COMMAND ----------

