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
# ------------------------------------------------------------------
# Note : here i have used my personal open AI token , so few lines are commented

from openai import OpenAI


# Get auth from the notebook context (works on both classic clusters and serverless)
# db_host = spark.conf.get("spark.databricks.workspaceUrl")
# db_token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
import getpass
token_input = getpass.getpass("Paste your 'openai...' token and press Enter: ")
os_token_string = token_input.strip()
OPENAI_ENDPOINT = "https://openai.com"
client = OpenAI(
    #api_key=db_token,
    api_key=os_token_string.strip(),
    #base_url=f"{f'https://{db_host}'}/serving-endpoints"
    base_url = OPENAI_ENDPOINT
)

MODEL = "databricks-meta-llama-3-3-70b-instruct"

# print("Client initialized successfully.")
# print(f"Model: {MODEL}")
# print(f"Endpoint: {f'https://{db_host}'}/serving-endpoints")

print("✅ Paid OpenAI Client successfully initialized via hardcoded text key!")
print(f"Model:    {MODEL}")
print(f"Endpoint: {OPENAI_ENDPOINT}")

# COMMAND ----------

# ------------------------------------------------------------------
# Step 3a: Demonstrate task types using the same LLM with different prompts
# ------------------------------------------------------------------

# Fix: the earlier client points at https://openai.com, which rejects requests
# for Databricks-hosted models (403). Re-point it at this workspace's AI Gateway
# using automatic notebook authentication (no pasted key needed).
from openai import OpenAI
from databricks.sdk import WorkspaceClient

_w = WorkspaceClient()
_api_headers = _w.config.authenticate()
client = OpenAI(
    api_key=_api_headers["Authorization"].split(" ", 1)[1],
    base_url=f"{_w.config.host.rstrip('/')}/ai-gateway/mlflow/v1",
)
# Same Llama 3.3 70B model, addressed by its Unity Catalog service name
MODEL = "system.ai.meta-llama-3-3-70b-instruct"

# Sample text we will use across multiple task demonstrations
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

# Define prompts for each task type
task_demos = {
    "Summarization": (
        f"Summarize the following text in exactly 2 sentences:\n\n{sample_text}"
    ),
    "Text Classification": (
        f"Classify the overall sentiment of the following text as POSITIVE, "
        f"NEGATIVE, or MIXED. Respond with only the label.\n\n{sample_text}"
    ),
    "Text Generation": (
        "Write a 3-sentence LinkedIn post announcing a new AI product launch "
        "for a tech company. Keep it professional and exciting."
    ),
    "Question Answering": (
        f"Based on the following context, answer the question.\n\n"
        f"Context: {sample_text}\n\n"
        f"Question: Why did sales decline in China?"
    ),
    "Token Classification (NER)": (
        f"Identify all named entities in the following text. For each entity, "
        f"provide the entity text and its type (PERSON, ORGANIZATION, LOCATION, "
        f"DATE, MONEY). Format as a list.\n\n{sample_text}"
    ),
    "Text2Text Generation": (
        f"Translate the following text to French:\n\n"
        f"Apple reported record revenue driven by strong iPhone sales. "
        f"The company plans to expand operations in Vietnam and India."
    )
}

# Call the LLM for each task
print("=" * 70)
print("  SAME MODEL, DIFFERENT TASKS -- Prompt is what drives behavior")
print("=" * 70)

for task_name, prompt in task_demos.items():
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a precise assistant. Follow instructions exactly."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0.0
    )
    result = response.choices[0].message.content.strip()
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

EMBEDDING_MODEL = "system.ai.gte-large-en"  # same GTE model, Unity Catalog service name

texts_to_embed = [
    "Apple reported record revenue from iPhone sales.",
    "The tech company saw strong smartphone earnings.",
    "I love cooking Italian pasta on weekends."
]

embedding_response = client.embeddings.create(
    model=EMBEDDING_MODEL,
    input=texts_to_embed
)

print("=== Feature Extraction (Embeddings) ===")
print(f"Model: {EMBEDDING_MODEL}")
print(f"Number of texts embedded: {len(texts_to_embed)}")
print(f"Embedding dimension: {len(embedding_response.data[0].embedding)}")
print()

for i, text in enumerate(texts_to_embed):
    vec = embedding_response.data[i].embedding
    print(f"Text {i+1}: \"{text}\"")
    print(f"  Vector (first 5 dims): {[round(v, 4) for v in vec[:5]]}...")
    print()

# Compute cosine similarity to show semantic closeness
import math

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

vec_0 = embedding_response.data[0].embedding
vec_1 = embedding_response.data[1].embedding
vec_2 = embedding_response.data[2].embedding

sim_01 = cosine_similarity(vec_0, vec_1)
sim_02 = cosine_similarity(vec_0, vec_2)

print("=== Semantic Similarity ===")
print(f"Text 1 vs Text 2 (both about tech revenue): {sim_01:.4f}")
print(f"Text 1 vs Text 3 (tech revenue vs cooking):  {sim_02:.4f}")
print()
print("The two tech-related sentences are semantically closer (higher similarity)")
print("than the tech sentence vs the cooking sentence. This is what powers")
print("semantic search -- find documents with similar MEANING, not just keywords.")

# COMMAND ----------

# ------------------------------------------------------------------
# Step 3c: Feature Extraction and Token Classification -- Deep Dive
# ------------------------------------------------------------------
#
# Part 1: Compare BoW, TF-IDF, and Embeddings on the same texts
# Part 2: Token classification with NER and POS tagging

import math
from collections import Counter

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
    # Document frequency: how many docs contain each word
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
    # Show only non-zero scores
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

resp = client.embeddings.create(model=EMBEDDING_MODEL, input=docs)
vecs = [r.embedding for r in resp.data]

sim_01 = cosine_similarity(vecs[0], vecs[1])
sim_02 = cosine_similarity(vecs[0], vecs[2])
sim_12 = cosine_similarity(vecs[1], vecs[2])

print(f"\n  Cosine similarities (embeddings capture MEANING):")
print(f"    'cat sat on mat' vs 'kitten rested on rug': {sim_01:.4f}  <- SIMILAR meaning")
print(f"    'cat sat on mat' vs 'stock prices fell':     {sim_02:.4f}  <- DIFFERENT topic")
print(f"    'kitten on rug'  vs 'stock prices fell':     {sim_12:.4f}  <- DIFFERENT topic")
print(f"\n  Embeddings KNOW that 'cat' and 'kitten' are related!")
print(f"  BoW and TF-IDF cannot do this.")

print(f"\n  {'Method':<25} {'Understands synonyms?':<25} {'Understands context?'}")
print(f"  {'-' * 70}")
print(f"  {'Bag of Words':<25} {'No':<25} {'No'}")
print(f"  {'TF-IDF':<25} {'No':<25} {'No'}")
print(f"  {'Embeddings':<25} {'YES':<25} {'YES'}")

# ── PART 2: Token Classification Deep Dive ─────────────────────────

print(f"\n\n{'=' * 70}")
print("TOKEN CLASSIFICATION: Labeling Each Word Individually")
print("=" * 70)

# Use the LLM to demonstrate NER
ner_text = (
    "Tim Cook announced that Apple will expand operations in Vietnam "
    "and India. Goldman Sachs maintained a buy rating on January 15, 2025."
)

ner_response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": (
        f"Perform Named Entity Recognition on the following text. "
        f"For EVERY word, output the word followed by its NER tag. "
        f"Use these tags: PERSON, ORG, LOC, DATE, MONEY, O (no entity).\n\n"
        f"Text: {ner_text}\n\n"
        f"Format each word on its own line as: word -> TAG"
    )}],
    temperature=0.0,
    max_tokens=500,
)

print(f"\n  --- Named Entity Recognition (NER) ---")
print(f"  Input: \"{ner_text}\"")
print(f"\n  NER Output (each token gets a label):")
for line in ner_response.choices[0].message.content.strip().split('\n')[:15]:
    print(f"    {line}")

# POS tagging demo
pos_response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": (
        f"Perform Part-of-Speech tagging on: 'The cat sat on the mat.'\n\n"
        f"For each word, output: word -> POS_TAG\n"
        f"Use standard POS tags: DET, NOUN, VERB, ADP, PUNCT, etc."
    )}],
    temperature=0.0,
    max_tokens=200,
)

print(f"\n  --- Part-of-Speech (POS) Tagging ---")
print(f"  Input: 'The cat sat on the mat.'")
print(f"\n  POS Output (grammatical role of each word):")
for line in pos_response.choices[0].message.content.strip().split('\n')[:8]:
    print(f"    {line}")

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

# Sentencizer output
print("--- Sentencizer (rule-based, NOT an LLM task) ---")
sents = simple_sentencizer(sample_for_comparison)
for s in sents:
    print(f"  Sentence: {s}")
print("  (Just splits text. No understanding.)\n")

# Actual LLM task outputs
for task_name, prompt in comparison_tasks.items():
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.0
    )
    result = response.choices[0].message.content.strip()
    print(f"--- {task_name} (real LLM task) ---")
    print(f"  {result}")
    print()

# COMMAND ----------

# ------------------------------------------------------------------
# Step 5a: See how tokenization differs across languages
# ------------------------------------------------------------------

# We'll use a simple heuristic: ask the LLM to tokenize text,
# then compare embedding token counts across languages for the SAME meaning.

multilingual_samples = {
    "English":    "The quick brown fox jumps over the lazy dog.",
    "German":     "Der schnelle braune Fuchs springt über den faulen Hund.",
    "French":     "Le rapide renard brun saute par-dessus le chien paresseux.",
    "Japanese":   "素早い茶色の狐が怠け者の犬を飛び越える。",
    "Arabic":     "الثعلب البني السريع يقفز فوق الكلب الكسول.",
    "Korean":     "빠른 갈색 여우가 게으른 개를 뛰어넘는다.",
}

# Embed all translations of the same sentence
EMBEDDING_MODEL = "system.ai.gte-large-en"  # same GTE model, Unity Catalog service name

texts = list(multilingual_samples.values())
labels = list(multilingual_samples.keys())

embedding_resp = client.embeddings.create(
    model=EMBEDDING_MODEL,
    input=texts
)

print("=== Multilingual Embedding Comparison ===")
print(f"Model: {EMBEDDING_MODEL}")
print(f"All sentences say the same thing in different languages.\n")

# Show character count as a proxy for tokenizer efficiency
for i, (lang, text) in enumerate(multilingual_samples.items()):
    vec = embedding_resp.data[i].embedding
    print(f"  {lang:<10} | chars: {len(text):>3} | text: {text[:60]}")


# COMMAND ----------

# ------------------------------------------------------------------
# Step 5b: Measure cross-language semantic similarity
# ------------------------------------------------------------------

# If the embedding model handles a language well, the vector for
# "The quick brown fox..." in English should be CLOSE to the same
# sentence in German, French, etc. If it handles a language poorly,
# the vectors will drift apart.

import math

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

english_vec = embedding_resp.data[0].embedding

print("=== Cross-Language Similarity (vs English) ===")
print("If the model handles a language well, similarity should be high (>0.8).")
print("Low similarity means the tokenizer struggles with that language.\n")

for i, (lang, text) in enumerate(multilingual_samples.items()):
    if i == 0:  # skip English vs English
        continue
    sim = cosine_similarity(english_vec, embedding_resp.data[i].embedding)
    bar = '█' * int(sim * 30)
    quality = '✓ Good' if sim > 0.80 else '⚠ Weak' if sim > 0.60 else '✗ Poor'
    print(f"  English vs {lang:<10} | sim: {sim:.4f} | {bar} | {quality}")

print("\n" + "=" * 70)
print("KEY INSIGHT: An English-focused embedding model (like GTE-Large-EN)")
print("may produce weaker vectors for non-Latin scripts (CJK, Arabic, etc.).")
print("For multilingual RAG, consider a multilingual model like:")
print("  - multilingual-e5-large")
print("  - paraphrase-multilingual-MiniLM")
print("  - Cohere embed-multilingual-v3.0")
print("=" * 70)


# COMMAND ----------

# ------------------------------------------------------------------
# Step 5c: Visualize the tokenization difference
# ------------------------------------------------------------------

# Ask the LLM to demonstrate how a tokenizer might split each language.
# This is an approximation — real tokenizers use BPE/SentencePiece,
# but this illustrates the core concept.

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": (
            "You are a tokenization expert. For each sentence, show how a "
            "BPE tokenizer trained primarily on English text would split it. "
            "Show the tokens in [brackets]. For non-Latin scripts, show that "
            "characters get split into individual Unicode code points or bytes."
        )},
        {"role": "user", "content": (
            "Show approximate BPE tokenization for these sentences:\n"
            "1. English: The quick brown fox\n"
            "2. German: Der schnelle braune Fuchs\n"
            "3. Japanese: 素早い茶色の狐\n"
            "4. Arabic: الثعلب البني السريع\n\n"
            "For each, show the tokens and count them."
        )}
    ],
    max_tokens=400,
    temperature=0.0
)

print("=== How a BPE Tokenizer Splits Different Languages ===")
print("(Approximation — real tokenization depends on the specific model)\n")
print(response.choices[0].message.content)

print("\n" + "-" * 50)
print("TAKEAWAY: The same meaning requires MORE tokens in languages")
print("the tokenizer wasn't trained on. More tokens = higher cost,")
print("less context window, and potentially weaker representations.")

# COMMAND ----------

