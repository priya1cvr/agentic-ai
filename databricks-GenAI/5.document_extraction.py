# Databricks notebook source
# MAGIC %md
# MAGIC **Step 1: Explore the Three-Level Namespace** <br>
# MAGIC Every object in Databricks has a fully qualified name with three parts:
# MAGIC
# MAGIC catalog.schema.object
# MAGIC This is like a mailing address: Country.City.Street. You need all three to unambiguously find anything.
# MAGIC
# MAGIC Catalog = the top-level container (your workspace has workspace)
# MAGIC Schema (also called database) = a logical grouping inside a catalog
# MAGIC Object = a table, view, model, function, or volume

# COMMAND ----------

# ------------------------------------------------------------------
# Step 1: Explore catalogs and schemas
# ------------------------------------------------------------------

# List all catalogs you have access to
print("=== Available Catalogs ===")
catalogs = spark.sql("SHOW CATALOGS")
catalogs.show(truncate=False)

# List schemas in the 'workspace' catalog
print("\n=== Schemas in 'workspace' catalog ===")
schemas = spark.sql("SHOW SCHEMAS IN workspace")
schemas.show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC **Step 2: Create Your Personal Schema**
# MAGIC
# MAGIC For the rest of this course, all your lab artifacts (tables, models, functions) will live in a schema called genai_labs inside the workspace catalog.
# MAGIC
# MAGIC Think of this as creating your own drawer in the filing cabinet. Everything you build goes in this drawer, keeping it organized and separate from other users.
# MAGIC
# MAGIC UI -> After running the code below, go to Left nav -> Catalog -> expand workspace -> you should see genai_labs appear in the tree.

# COMMAND ----------

# ------------------------------------------------------------------
# Step 2: Create your personal schema for all lab work
# ------------------------------------------------------------------

# Create the schema (IF NOT EXISTS prevents errors if you run this twice)
spark.sql("""
    CREATE SCHEMA IF NOT EXISTS workspace.genai_labs
    COMMENT 'Personal schema for GenAI Engineer Associate lab work'
""")

# Set it as your default so you don't have to type 'workspace.genai_labs' every time
spark.sql("USE CATALOG workspace")
spark.sql("USE SCHEMA genai_labs")

# Verify
print(f"Current catalog: {spark.catalog.currentCatalog()}")
print(f"Current schema:  {spark.catalog.currentDatabase()}")
print("\nSchema 'workspace.genai_labs' is ready! All lab artifacts will go here.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Understand What Lives in Unity Catalog
# MAGIC
# MAGIC Here's the key insight that separates Databricks from other platforms: **Unity Catalog manages far more than just tables.** It's the single governance layer for *all* assets:
# MAGIC
# MAGIC | Asset Type | What It Is | Example from This Course |
# MAGIC |---|---|---|
# MAGIC | **TABLE** | Structured data (Delta format) | `document_chunks` — your RAG knowledge base |
# MAGIC | **MODEL** | Registered ML/AI models | `rag_chain` — your deployed RAG application |
# MAGIC | **FUNCTION** | Python/SQL functions | `order_lookup` — an agent tool |
# MAGIC | **VOLUME** | Unstructured files (PDFs, images) | `source_docs` — raw documents before processing |
# MAGIC | **CONNECTION** | External data source credentials | Connections to S3, ADLS, external APIs |
# MAGIC
# MAGIC > **Why this matters:** This is why the exam says *"Unity Catalog is the governance layer for both data and AI assets."*
# MAGIC >
# MAGIC > - When you **register a model** with MLflow, it goes into Unity Catalog.
# MAGIC > - When you **create a function** for an agent tool, it goes into Unity Catalog.
# MAGIC > - When you **upload documents** for RAG, they go into a Volume in Unity Catalog.

# COMMAND ----------

# ------------------------------------------------------------------
# Step 3: Create example assets to see the different object types
# ------------------------------------------------------------------

# Create a sample table
spark.sql("""
    CREATE TABLE IF NOT EXISTS workspace.genai_labs.sample_assets (
        id INT,
        name STRING,
        description STRING
    )
    COMMENT 'Sample table to demonstrate Unity Catalog asset types'
""")

# Insert some sample data
spark.sql("""
    INSERT OVERWRITE workspace.genai_labs.sample_assets VALUES
    (1, 'Delta Table', 'Stores structured data like document chunks'),
    (2, 'ML Model', 'Registered AI models like your RAG chain'),
    (3, 'UC Function', 'Python/SQL functions that become agent tools'),
    (4, 'Volume', 'Unstructured file storage for PDFs, images, etc.')
""")

# Create a Volume (for storing unstructured files like PDFs)
spark.sql("""
    CREATE VOLUME IF NOT EXISTS workspace.genai_labs.source_docs
    COMMENT 'Volume for storing source documents (PDFs, images, HTML)'
""")

# List everything in our schema
print("=== Tables in workspace.genai_labs ===")
spark.sql("SHOW TABLES IN workspace.genai_labs").show(truncate=False)

print("\n=== Volumes in workspace.genai_labs ===")
spark.sql("SHOW VOLUMES IN workspace.genai_labs").show(truncate=False)

# COMMAND ----------

spark.sql("""SELECT * FROM workspace.genai_labs.sample_assets""").show(truncate=False)

# COMMAND ----------

# ------------------------------------------------------------------
# Step 4: Practice GRANT and REVOKE syntax
# ------------------------------------------------------------------

# NOTE: These commands may fail on Community Edition / limited workspaces.
# That's OK — the important thing is to understand the syntax for the exam.

# Example: Grant SELECT on a table to a user
# GRANT SELECT ON TABLE workspace.genai_labs.sample_assets TO `user@example.com`;

# Example: Grant USE SCHEMA to a group
# GRANT USE SCHEMA ON SCHEMA workspace.genai_labs TO `data_scientists`;

# Example: Revoke access
# REVOKE SELECT ON TABLE workspace.genai_labs.sample_assets FROM `user@example.com`;

# Let's check the current grants on our schema (this usually works)
try:
    grants = spark.sql("SHOW GRANTS ON SCHEMA workspace.genai_labs")
    grants.show(truncate=False)
except Exception as e:
    print(f"Note: SHOW GRANTS requires admin privileges.")
    print(f"Error: {e}")
    print("\nDon't worry — learn the syntax, that's what the exam tests:")
    print("  GRANT  ON   TO ``")
    print("  REVOKE  ON   FROM ``")
     

# COMMAND ----------

# ------------------------------------------------------------------
# Step 5: Inspect object metadata
# ------------------------------------------------------------------

# Describe the schema itself
print("=== Schema Description ===")
spark.sql("DESCRIBE SCHEMA workspace.genai_labs").show(truncate=False)

# Describe a table — shows columns, types, and comments
print("\n=== Table Description ===")
spark.sql("DESCRIBE TABLE workspace.genai_labs.sample_assets").show(truncate=False)

# Extended describe — shows storage location, owner, created time, table properties
print("\n=== Table Extended Details ===")
spark.sql("DESCRIBE TABLE EXTENDED workspace.genai_labs.sample_assets").show(truncate=False)
     

# COMMAND ----------

# MAGIC %md
# MAGIC **Objectives Covered**
# MAGIC
# MAGIC Identify needed source documents that provide necessary knowledge and quality for a given RAG application <br>
# MAGIC Select the right extraction package for a given document type  <br>
# MAGIC Extract text using pytesseract, pypdf, and beautifulsoup4  <br>
# MAGIC Filter extracted text to remove noise (headers, footers, navigation)  <br>

# COMMAND ----------

# MAGIC %md
# MAGIC **Step 0: Identifying Needed Source Documents**
# MAGIC
# MAGIC This is the step most teams skip -- and it is the step that determines whether your RAG application actually works.
# MAGIC
# MAGIC Before you extract a single byte of text, you must answer three questions:
# MAGIC
# MAGIC What questions will users ask? <br>
# MAGIC What data answers those questions? <br>
# MAGIC Where does that data live -- and in what format?

# COMMAND ----------

# Step 0: Source Document Identification -- Practice Scenarios
#
# For each scenario, we identify:
#   1. What users will ask
#   2. What data source answers those questions
#   3. Whether it belongs in vector search or a feature store / SQL query

SCENARIOS = [
    {
        "app": "FAQ Bot for HR Department",
        "user_asks": "How much PTO do I get? What is the parental leave policy?",
        "data_needed": "Company policy documents + knowledge base articles",
        "data_type": "UNSTRUCTURED",
        "storage": "Vector Search Index",
        "why": (
            "Policy docs are static, unstructured text. Users ask natural-language "
            "questions that require semantic search to find the right policy section."
        ),
    },
    {
        "app": "Order Support Bot",
        "user_asks": "Where is my order #12345? When will it arrive?",
        "data_needed": "Order database / Feature Serving table with order + shipping data",
        "data_type": "STRUCTURED (real-time)",
        "storage": "Feature Serving endpoint or SQL query -- NOT vector search",
        "why": (
            "Order data changes every minute (shipped, delivered, delayed). "
            "You need exact-match lookup by order ID, not semantic similarity. "
            "Embedding order records into a vector store would be stale instantly."
        ),
    },
    {
        "app": "Legal Research Assistant",
        "user_asks": "What precedents exist for patent infringement in software?",
        "data_needed": "Case law documents + statute database",
        "data_type": "UNSTRUCTURED",
        "storage": "Vector Search Index",
        "why": (
            "Case law is long-form unstructured text. Users ask open-ended questions "
            "that require semantic understanding to match relevant cases."
        ),
    },
    {
        "app": "Product Recommender",
        "user_asks": "What laptop should I buy for video editing under $1500?",
        "data_needed": "Product catalog + user preference features",
        "data_type": "STRUCTURED (catalog) + STRUCTURED (preferences)",
        "storage": "Feature Serving endpoint for user prefs + SQL query for catalog filtering",
        "why": (
            "Product specs and prices are structured data that change frequently. "
            "User preferences are structured feature vectors. Neither benefits from "
            "semantic similarity search -- you need exact filters (price < $1500, "
            "category = 'laptop') and feature lookups."
        ),
    },
]


print("=" * 76)
print("SOURCE DOCUMENT IDENTIFICATION -- 4 SCENARIOS")
print("=" * 76)

for i, s in enumerate(SCENARIOS, 1):
    print(f"\n{'~' * 76}")
    print(f"  SCENARIO {i}: {s['app']}")
    print(f"{'~' * 76}")
    print(f"  Users ask     : {s['user_asks']}")
    print(f"  Data needed   : {s['data_needed']}")
    print(f"  Data type     : {s['data_type']}")
    print(f"  Store in      : {s['storage']}")
    print(f"  Why           : {s['why']}")

print(f"\n{'=' * 76}")
print("KEY RULE OF THUMB:")
print("  - Unstructured knowledge (docs, policies, articles) -> Vector Search")
print("  - Structured real-time data (orders, inventory, profiles) -> Feature Serving / SQL")
print("  - If you are doing exact-match lookup (order ID), do NOT use vector search.")
print("=" * 76)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Step 1: Upload Documents to a Volume
# MAGIC
# MAGIC In Databricks, **Volumes** are the Unity Catalog object for storing files -- PDFs, images, CSVs, or any other raw data. Think of a Volume like a shared network drive that is governed by Unity Catalog permissions.
# MAGIC
# MAGIC Volumes live at:
# MAGIC
# MAGIC ```
# MAGIC /Volumes/<catalog>/<schema>/<volume_name>/
# MAGIC ```
# MAGIC
# MAGIC ### Why Volumes?
# MAGIC
# MAGIC | Property | Description |
# MAGIC |---|---|
# MAGIC | **Governed** | Permissions are managed through Unity Catalog (same as tables). |
# MAGIC | **Accessible** | Files can be read from notebooks, jobs, and pipelines using standard file paths. |
# MAGIC | **Integrated** | The Data Ingestion UI lets non-technical users upload files via drag-and-drop. |
# MAGIC
# MAGIC ### UI Navigation
# MAGIC
# MAGIC 1. **Catalog** (left sidebar) &rarr; navigate to your schema.
# MAGIC 2. Click **Create** &rarr; **Volume** (if one does not exist).
# MAGIC 3. Click into the Volume &rarr; **Upload to this volume** (top right).
# MAGIC 4. Drag and drop your source documents.

# COMMAND ----------

# Step 1: Create sample documents to simulate different file types
#
# In production, these would be real files uploaded to a Volume.
# Here, we create them locally so the lab runs anywhere.

import os
import tempfile

# Create a temporary directory to simulate a Volume path
VOLUME_PATH = tempfile.mkdtemp(prefix="lab_02_01_volume_")
print(f"Simulated Volume path: {VOLUME_PATH}")
print(f"In production, this would be: /Volumes////\n")

# --- Sample 1: A text file simulating extracted PDF content ---
pdf_text = """ACME Corp Employee Handbook
Page 1 of 25
Last Updated: January 2025
===========================================

Chapter 3: Paid Time Off (PTO)

All full-time employees receive 20 days of PTO per calendar year.
PTO accrues at a rate of 1.67 days per month.
Unused PTO may be carried over up to a maximum of 5 days.

Requesting PTO:
- Submit requests via the HR portal at least 5 business days in advance.
- Requests are approved by your direct manager.
- Requests of 5+ consecutive days require VP-level approval.

===========================================
ACME Corp Confidential -- Do Not Distribute
Page 1 of 25
"""

pdf_path = os.path.join(VOLUME_PATH, "employee_handbook.txt")
with open(pdf_path, "w") as f:
    f.write(pdf_text)


# --- Sample 2: An HTML file simulating a web page ---
html_content = """

ACME Corp - Shipping FAQ

  
    Home | Products | FAQ
  
  
    Shipping FAQ
    How long does shipping take?
    Standard shipping takes 5-7 business days. Express shipping takes 2-3 business days.
    Do you ship internationally?
    Yes, we ship to over 50 countries. International orders take 10-14 business days.
    How do I track my order?
    Log in to your account and visit the Orders page. Click on any order to see tracking details.
  
  
    Copyright 2025 ACME Corp. All rights reserved.
    Privacy Policy | Terms of Service
  


"""

html_path = os.path.join(VOLUME_PATH, "shipping_faq.html")
with open(html_path, "w") as f:
    f.write(html_content)


# --- Sample 3: A plain text file simulating OCR output from a scanned image ---
scanned_text = """INVOICE #20250115-A
Date: January 15, 2025

Bill To:                     Ship To:
Jane Doe                     Jane Doe
123 Main St                  456 Oak Ave
Springfield, IL 62701        Springfield, IL 62704

Item            Qty    Price     Total
Widget A          2   
39.98
Widget B          1   
49.99
Shipping                        
95.96

Thank you for your business!
"""

scan_path = os.path.join(VOLUME_PATH, "scanned_invoice.txt")
with open(scan_path, "w") as f:
    f.write(scanned_text)


# List all files in our simulated Volume
print("Files in simulated Volume:")
for fname in os.listdir(VOLUME_PATH):
    fpath = os.path.join(VOLUME_PATH, fname)
    size_kb = os.path.getsize(fpath) / 1024
    print(f"  {fname:30s}  ({size_kb:.1f} KB)")

# COMMAND ----------

import os
os.listdir("/tmp/lab_02_01_volume_fu_gg19c")

# COMMAND ----------

# MAGIC %sh ls -l /tmp/lab_02_01_volume_fu_gg19c
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Step 2: Extract Text from a PDF (`pypdf`)
# MAGIC
# MAGIC **When to use `pypdf`:** The PDF contains selectable text -- you can highlight and copy text when viewing it in a PDF reader. Most digitally-created PDFs (reports, e-books, generated invoices) fall into this category.
# MAGIC
# MAGIC **When NOT to use `pypdf`:** The PDF is a scanned image (you cannot select text). In that case, `pypdf` returns empty strings and you need `pytesseract` (OCR).
# MAGIC
# MAGIC ### How `pypdf` Works (Simplified)
# MAGIC
# MAGIC ```
# MAGIC PDF file on disk
# MAGIC     |
# MAGIC     v
# MAGIC PdfReader("file.pdf")             # Open the file
# MAGIC     |
# MAGIC     v
# MAGIC reader.pages                     # Access individual pages
# MAGIC     |
# MAGIC     v
# MAGIC page.extract_text()              # Pull the text from one page
# MAGIC     |
# MAGIC     v
# MAGIC Clean text (remove headers,      # Post-processing
# MAGIC  footers, page numbers)
# MAGIC ```

# COMMAND ----------

# Step 2: Extract text from a PDF using pypdf
#
# Since we cannot guarantee pypdf is installed or that a real PDF exists,
# we show the real code pattern AND simulate the output.

# ---------- REAL CODE (run this on Databricks with a real PDF) ----------
# from pypdf import PdfReader
#
# reader = PdfReader("/Volumes/my_catalog/my_schema/my_volume/handbook.pdf")
# full_text = ""
# for page in reader.pages:
#     full_text += page.extract_text() + "\n"
# print(full_text[:500])


# ---------- SIMULATION (works anywhere) ----------
# We will read our sample text file and demonstrate the extraction + cleaning
# pipeline that you would apply to real pypdf output.

with open(pdf_path, "r") as f:
    raw_pdf_text = f.read()

print("=" * 60)
print("RAW EXTRACTED TEXT (before cleaning)")
print("=" * 60)
print(raw_pdf_text)
print(f"\nCharacter count: {len(raw_pdf_text)}")

# COMMAND ----------

# DBTITLE 1,Install pypdf
# MAGIC %pip install pypdf

# COMMAND ----------

# MAGIC %restart_python

# COMMAND ----------

# 
# ---------- REAL CODE (run with a real PDF) ----------
from pypdf import PdfReader

reader = PdfReader("/Volumes/workspace/genai_labs/source_docs/databricks-certified-gen-ai-associate-exam-guide-august-2026.pdf")
full_text = ""
for page in reader.pages:
    full_text += page.extract_text() + "\n"
print(full_text[:500])


# COMMAND ----------

# Step 2 (continued): Clean the extracted text
#
# Real PDF extraction produces noise:
#   - Page numbers ("Page 1 of 25")
#   - Headers/footers repeated on every page
#   - Excessive whitespace
#   - Confidentiality notices
#
# Cleaning this text BEFORE chunking improves retrieval quality.

import re


def clean_pdf_text(text: str) -> str:
    """Remove common PDF extraction noise."""
    # Remove page number patterns like "Page X of Y"
    text = re.sub(r"Page \d+ of \d+", "", text)

    # Remove confidentiality footers
    text = re.sub(r".*Confidential.*Do Not Distribute.*", "", text)

    # Remove "Last Updated" lines (metadata, not content)
    text = re.sub(r"Last Updated:.*\n", "", text)

    # Remove separator lines
    text = re.sub(r"={3,}", "", text)

    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


cleaned_pdf_text = clean_pdf_text(raw_pdf_text)

print("=" * 60)
print("CLEANED TEXT (after filtering)")
print("=" * 60)
print(cleaned_pdf_text)
print(f"\nCharacter count: {len(cleaned_pdf_text)} (was {len(raw_pdf_text)})")
print(f"Removed {len(raw_pdf_text) - len(cleaned_pdf_text)} characters of noise")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Step 3: Extract Text from HTML (`beautifulsoup4`)
# MAGIC
# MAGIC **When to use `beautifulsoup4`:** You have HTML files (saved web pages, internal wiki exports, HTML emails) and need to extract just the meaningful text content, discarding navigation bars, footers, scripts, and styling.
# MAGIC
# MAGIC **Important distinction:** `beautifulsoup4` parses HTML. It does **not** fetch web pages. To download a page, use `requests` first, then parse with `BeautifulSoup`.
# MAGIC
# MAGIC ### How `beautifulsoup4` Works (Simplified)
# MAGIC
# MAGIC ```
# MAGIC HTML string or file
# MAGIC     |
# MAGIC     v
# MAGIC BeautifulSoup(html, "html.parser")    # Parse the HTML tree
# MAGIC     |
# MAGIC     v
# MAGIC Remove unwanted tags                   # Drop <nav>, <footer>, <script>, <style>
# MAGIC     |
# MAGIC     v
# MAGIC soup.get_text()                        # Extract visible text
# MAGIC     |
# MAGIC     v
# MAGIC Clean whitespace                       # Collapse blank lines
# MAGIC ```

# COMMAND ----------


# Step 3: Extract text from HTML using beautifulsoup4

from bs4 import BeautifulSoup
import re
# Read the HTML file
with open(html_path,"r") as f:
    raw_html =f.read()

print("=" * 60)
print("RAW HTML (first 400 characters)")
print("=" * 60)
print(raw_html[:400])
print("...\n")

# Parse the HTML
soup = BeautifulSoup(raw_html, "html.parser")
# Remove unwanted elements: navigation, footer, scripts, styles
for tag in soup.find_all(["nav", "footer", "script", "style"]):
    tag.decompose() # Completely removes the tag and its contents

# Extract clean text
clean_html_text = soup.get_text(separator="\n", strip=True)

# Collapse multiple blank lines
clean_html_text = re.sub(r"\n{3,}", "\n\n", clean_html_text)

print("=" * 60)
print("CLEANED TEXT (nav/footer/script removed)")
print("=" * 60)
print(clean_html_text)
print(f"\nExtracted {len(clean_html_text)} characters of content")
print(f"Discarded {len(raw_html) - len(clean_html_text)} characters of markup/noise")
                     


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Step 4: Extract Text from Scanned Images (`pytesseract`)
# MAGIC
# MAGIC **When to use `pytesseract`:** You have scanned documents -- images (`.jpg`, `.png`) or PDFs that are essentially photographs of paper. The text is not machine-readable; it exists only as pixels.
# MAGIC
# MAGIC
# MAGIC >
# MAGIC > If the question mentions **"scanned documents"**, **"images of text"**, **"OCR"**, or **"jpg/png files"**, the answer is `pytesseract`.
# MAGIC
# MAGIC ### How `pytesseract` Works (Simplified)
# MAGIC
# MAGIC ```
# MAGIC Scanned image (jpg/png)
# MAGIC     |
# MAGIC     v
# MAGIC PIL.Image.open("scan.jpg")          # Load the image
# MAGIC     |
# MAGIC     v
# MAGIC pytesseract.image_to_string(img)    # OCR: convert pixels to text
# MAGIC     |
# MAGIC     v
# MAGIC Raw OCR text (may have errors)      # "rn" misread as "m", etc.
# MAGIC     |
# MAGIC     v
# MAGIC Post-processing / cleaning          # Fix common OCR mistakes
# MAGIC ```
# MAGIC

# COMMAND ----------

# MAGIC %pip install pytesseract
# MAGIC dbutils.library.restartPython() 

# COMMAND ----------

# Lets uupload a scanned pdf to volume

# Step 4: Extract text from scanned images using pytesseract
#
# pytesseract requires Tesseract OCR to be installed on the system.
# On Databricks, install via: %pip install pytesseract
# and ensure Tesseract is available (usually pre-installed on ML runtimes).
#
# Since we cannot guarantee Tesseract is installed in all environments,
# we show the REAL code pattern and SIMULATE the output.

#---------- REAL CODE (run on Databricks with Tesseract installed) ----------
from PIL import Image
import pytesseract

# Load the scanned image
img = Image.open("/Volumes/workspace/genai_labs/source_docs/axis.jpeg")

# Run OCR
ocr_text = pytesseract.image_to_string(img)

print(ocr_text)

# COMMAND ----------

# Read the first few pages of a SCANNED PDF (image-based) with pytesseract
#
# A scanned PDF has no selectable text, so pypdf returns empty strings.
# We must render each page to an image first (PyMuPDF), then run OCR (pytesseract).
#
# Install requirements (pytesseract + PyMuPDF) if not already installed
%pip install pytesseract pymupdf --quiet

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

PDF_PATH = "/Volumes/workspace/genai_labs/source_docs/CamScanner 22-05-2026 17.33.pdf"
NUM_PAGES = 3  # how many pages to read

# Open the scanned PDF
pdf_doc = fitz.open(PDF_PATH)
print(f"Total pages in PDF: {pdf_doc.page_count}")

# Loop over the first few pages, render each page as an image, then OCR it
for page_num in range(min(NUM_PAGES, pdf_doc.page_count)):
    # Render page -> pixmap at 200 DPI (higher DPI = better OCR accuracy)
    page = pdf_doc.load_page(page_num)
    pix = page.get_pixmap(dpi=200)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    # OCR: convert the page image to text
    ocr_text = pytesseract.image_to_string(img)

    print("=" * 70)
    print(f"PAGE {page_num + 1} (OCR output, first 500 characters)")
    print("=" * 70)
    print(ocr_text[:500])
    print()

pdf_doc.close()

# COMMAND ----------

# ---------- SIMULATION ----------
# We read our pre-created "scanned" text to demonstrate the post-processing
# pipeline you would apply to real OCR output.

with open(scan_path, "r") as f:
    ocr_text = f.read()

print("=" * 60)
print("SIMULATED OCR OUTPUT (pytesseract.image_to_string)")
print("=" * 60)
print(ocr_text)

# Demonstrate common OCR post-processing
print("\n" + "=" * 60)
print("pytesseract USAGE SUMMARY")
print("=" * 60)
print("""
Essential code pattern:

    from PIL import Image
    import pytesseract

    img = Image.open("scanned_document.jpg")   # or .png
    text = pytesseract.image_to_string(img)     # OCR magic

That's it. Two lines to go from pixels to text.

Exam key facts:
  - pytesseract is for SCANNED IMAGES (jpg, png)
  - It uses Tesseract OCR under the hood
  - It requires PIL/Pillow to load the image
  - It is SLOWER and LESS ACCURATE than pypdf for text-based PDFs
  - Use it ONLY when text is not machine-readable
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Feature Store for Structured Transaction Data
# MAGIC
# MAGIC Steps 1–5 covered **unstructured data** — documents you extract, chunk, embed, and store in a Vector Search Index. But the exam also tests whether you know **when NOT to use vector search**.
# MAGIC
# MAGIC ### Why Feature Store?
# MAGIC
# MAGIC Shipping and arrival dates are:
# MAGIC
# MAGIC - **Structured** — columns in a table, not paragraphs of text
# MAGIC - **Transaction-specific** — different for every order
# MAGIC - **Constantly changing** — updated as shipments progress
# MAGIC - **Looked up by key** — you have the `transaction_id`, you want the row
# MAGIC
# MAGIC This is exactly what the **Databricks Feature Store** (now part of Feature Engineering) is designed for: fast, low-latency lookups of factual data by primary key.
# MAGIC
# MAGIC ### Vector Search vs. Feature Store
# MAGIC
# MAGIC | | Vector Search | Feature Store |
# MAGIC |---|---|---|
# MAGIC | **Query pattern** | "Find documents semantically similar to this query" | "Give me the row where `transaction_id = 'TXN-0042'`" |
# MAGIC | **Great for** | Policies, FAQs, manuals | Orders, shipments, user profiles, inventory |
# MAGIC | **Bad for** | "What is the delivery date for order TXN-0042?" | "What is your return policy?" |

# COMMAND ----------

# Step 6: Feature Store for Structured Transaction Data
#
# We simulate an automotive parts order system to show why
# Feature Store (key-based lookup) beats Vector Search for
# structured, transaction-specific data.

import pandas as pd
from datetime import datetime, timedelta
import random

random.seed(42)

# ── 1. Build a realistic order/shipping table ──────────────────────
#    In production, this data lives in your transactional database.
#    The Feature Store syncs it for low-latency serving.

CARRIERS = ["FedEx", "UPS", "USPS", "DHL"]
STATUSES = ["Processing", "Shipped", "In Transit", "Out for Delivery", "Delivered"]
PARTS = ["Brake Pad Set", "Oil Filter", "Spark Plug Pack", "Air Filter",
         "Transmission Fluid", "Alternator", "Radiator Hose", "Wiper Blades"]

orders = []
for i in range(20):
    order_date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 60))
    ship_days = random.choice([2, 3, 5, 7, 10, 14])
    orders.append({
        "transaction_id": f"TXN-{1000 + i:04d}",
        "account_id": f"ACCT-{random.randint(100, 999)}",
        "part_name": random.choice(PARTS),
        "invoice_amount": round(random.uniform(15.99, 499.99), 2),
        "order_date": order_date.strftime("%Y-%m-%d"),
        "shipping_carrier": random.choice(CARRIERS),
        "expected_delivery_date": (order_date + timedelta(days=ship_days)).strftime("%Y-%m-%d"),
        "shipping_status": random.choice(STATUSES),
        "tracking_number": f"{random.choice(CARRIERS)[:2].upper()}{random.randint(100000, 999999)}",
    })

df_orders = pd.DataFrame(orders)

print("=" * 80)
print("ORDER / SHIPPING TABLE (simulated automotive parts orders)")
print("=" * 80)
print(df_orders.to_string(index=False))
print(f"\n{len(df_orders)} rows, primary key: transaction_id")







# COMMAND ----------

# DBTITLE 1,Install databricks-feature-engineering
# MAGIC %pip install databricks-feature-engineering

# COMMAND ----------

# ── 2. Show what the Databricks Feature Store code looks like ─────
#    This is the REAL pattern you would use on Databricks.

print("\n" + "=" * 80)
print("DATABRICKS FEATURE STORE -- CREATE TABLE PATTERN")
print("=" * 80)

# ----- Real Databricks code (run on a cluster) -----

from databricks.feature_engineering import FeatureEngineeringClient

fe = FeatureEngineeringClient()

# Step 1 + 2: Write the DataFrame as a Delta table AND register it as a
# Feature Store table with a primary key -- create_table(df=...) does both.
spark_df = spark.createDataFrame(df_orders)
feature_table = fe.create_table(
    name="workspace.genai_labs.order_shipping_features",
    primary_keys=["transaction_id"],         # <-- THE KEY CONCEPT
    df=spark_df,
    description="Order and shipping data for the automotive parts app"
)
print(f"Created feature table: {feature_table}")

# Step 3: Enable online serving for low-latency lookups.
# This client version publishes through a Databricks online store:
#
online_store = fe.get_online_store(name="order-shipping-store") # It's a metadata lookup — it asks Databricks' Feature Store control plane: "does an online store named order-shipping-store exist in this workspace?" and returns an object describing it.
if online_store is None:
    online_store = fe.create_online_store(name="order-shipping-store", capacity="CU_2")
# CU_2 means the online store is provisioned with 2 Capacity Units — Databricks' billing/sizing unit for managed online store
# wait until online_store.state == "AVAILABLE"
# Triggered publishing requires change data feed on the source table
spark.sql("ALTER TABLE workspace.genai_labs.order_shipping_features SET TBLPROPERTIES (delta.enableChangeDataFeed = 'true')")
fe.publish_table(
      online_store=online_store,
      source_table_name="workspace.genai_labs.order_shipping_features",
      online_table_name="workspace.genai_labs.order_shipping_features_online"
  )
#
# UI -> Machine Learning -> Feature Serving -> Create endpoint

# COMMAND ----------

# MAGIC %md
# MAGIC ### Why `FeatureEngineeringClient` instead of `df.write.saveAsTable()`?
# MAGIC
# MAGIC > **Note:** We could have used `df.write.saveAsTable` — so why did we import `FeatureEngineeringClient` and use `fe.create_table`, `fe.create_online_store`, etc.?
# MAGIC
# MAGIC It comes down to a **technical difference that separates raw database storage from a Compound AI production pipeline**.
# MAGIC
# MAGIC If you just run `spark_df.write.saveAsTable()`, you are only writing bytes to an **offline analytical table**. By introducing the `FeatureEngineeringClient` and running the extra configuration block, you are turning that static table into a **live, globally managed production entity**.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 1. Why we use `fe.create_table()` (the Metastore Registry)
# MAGIC
# MAGIC If you write a table using standard Spark, it is just a pile of data — the system has no idea how the data is structured or what it is meant for.
# MAGIC
# MAGIC By wrapping it in `fe.create_table(primary_keys=["transaction_id"])`, you register it into the **Unity Catalog Feature Registry**. This layer registers metadata that standard Spark tables completely lack:
# MAGIC
# MAGIC - **Enforced uniqueness constraints** — it declares `transaction_id` as the absolute primary key. If a data engineer accidentally attempts to append a duplicate transaction ID tomorrow, Unity Catalog will catch it and block it to prevent data corruption.
# MAGIC - **Lineage & governance** — if an AI model starts making bad predictions, an administrator can open the Unity Catalog UI, click on this feature table, and see exactly which notebook generated it, which raw data pipelines populated it, and which ML models are currently consuming it.
# MAGIC
# MAGIC ### 2. Why we use `fe.create_online_store(capacity="CU_2")`
# MAGIC
# MAGIC This is the **most critical block** in the script — it addresses the **"Offline vs. Online" speed dilemma**.
# MAGIC
# MAGIC - A standard Delta table is optimized for **throughput**: it can read 10 million rows in 30 seconds, but reading a *single* row takes 1–2 seconds because Spark has to unpack compressed Parquet files from cloud storage (S3 / Azure Blob). For a web application or a real-time customer service chatbot, a 2-second wait time is a failure.
# MAGIC - By running `fe.create_online_store()`, you instruct Databricks to automatically spin up a **low-latency key-value store** (an internal managed Redis- or DynamoDB-like engine). Databricks provisions this compute capacity immediately (configured here with 2 Capacity Units, `CU_2`).
# MAGIC
# MAGIC ### 3. Why we run `ALTER TABLE ... SET TBLPROPERTIES (delta.enableChangeDataFeed = 'true')`
# MAGIC
# MAGIC Once you have an offline Delta table (on S3) *and* an online database (like Redis) running at the same time, you face a new problem: **how do you keep them synchronized when data updates?**
# MAGIC
# MAGIC If a tracking status shifts from *"In Transit"* to *"Delivered,"* that modification lands in the Delta table first. To prevent you from writing complex, brittle cron jobs or streaming sync scripts to copy the update to the online database, we turn on **Delta Change Data Feed (CDF)**:
# MAGIC
# MAGIC - **What CDF does** — it turns on an automated transactional ledger inside the Delta Lake folder, explicitly tracking every `INSERT`, `UPDATE`, and `DELETE` at the millisecond level.
# MAGIC - **The automation** — the Feature Store client listens directly to this Change Data Feed stream. The moment a row changes in your offline table, Databricks automatically catches the change, packages it, and replicates it to your Online Store in real time.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC #### Summary: What the app gains from this setup
# MAGIC
# MAGIC If you only use `saveAsTable()` and try to fetch an order status, your app has to execute this heavy, slow process:
# MAGIC
# MAGIC ```python
# MAGIC # SLOW: Spreads across the cluster, opening S3 files sequentially (takes 1-2 seconds)
# MAGIC df = spark.table("workspace.genai_labs.order_shipping_features")
# MAGIC result = df.filter(df.transaction_id == "TXN-1005").collect()
# MAGIC ```
# MAGIC
# MAGIC Because you used the `FeatureEngineeringClient` configuration, your live production app or LLM agent **bypasses Spark completely** and targets the low-latency serving endpoint directly via a fast REST API call:
# MAGIC
# MAGIC ```python
# MAGIC # ULTRA-FAST: Hits the online key-value database directly (takes < 10 ms)
# MAGIC features = fe.get_online_features(
# MAGIC     table_name="workspace.genai_labs.order_shipping_features",
# MAGIC     entity_keys=[{"transaction_id": "TXN-1005"}],
# MAGIC )
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## What `fe.create_table(df=...)` did that `saveAsTable` wouldn't
# MAGIC
# MAGIC 1. **Enforced the key semantics** — you saw it in the run log: it set `transaction_id` to `NOT NULL` and added a primary key constraint on the table. A bare `saveAsTable` just dumps rows; nothing marks which column is the entity key, and duplicate/missing keys would poison online serving.
# MAGIC 2. **Registered it as a feature table** — it created a `FeatureTable` entity (`table_id`, `primary_keys`, feature list) that the Feature Store tracks, so it's discoverable and reusable as an ML asset rather than being "just a table."
# MAGIC 3. **Unlocked the serving pipeline** — *(the big one)* — `fe.publish_table(online_store=...)`, online stores, and Feature Serving endpoints only work on **registered** feature tables. Step 3 above would be impossible on a plain `saveAsTable` table; a plain table has no online-store path.
# MAGIC 4. **Train/serve consistency** — the same client provides `read_table` / feature lookups for training, so the model trains on *exactly* the features (same definitions, same PK) that get served at inference time.
# MAGIC
# MAGIC > **When plain `saveAsTable` is fine:** batch analytics, training-data snapshots, anything where you just need rows. If you never serve features online or share feature definitions across models, you don't need the client.
# MAGIC

# COMMAND ----------

spark.sql("SELECT * FROM workspace.genai_labs.order_shipping_features_online").show(truncate=False)


# COMMAND ----------

# ── 3. Demonstrate key-based lookup (what the app actually does) ──

from pyspark.sql import functions as F

def feature_store_lookup(transaction_id: str) -> dict:
    """Key-based lookup against the published ONLINE table (the serving layer).

    In production, an application would make an HTTP call to a Feature
    Serving endpoint:
        POST https://<workspace-url>/serving-endpoints/<endpoint-name>/invocations
        {"dataframe_records": [{"transaction_id": "TXN-1005"}]}
    Here we perform the identical primary-key lookup against the online
    table that the serving endpoint reads from.
    """
    rows = (
        spark.read.table("workspace.genai_labs.order_shipping_features_online")
        .where(F.col("transaction_id") == transaction_id)
        .collect()
    )
    if not rows:
        return {"error": f"Transaction {transaction_id} not found"}
    return rows[0].asDict()


# Test lookups -- exactly what the automotive parts app would do
print("\n" + "=" * 80)
print("FEATURE STORE LOOKUP -- Key-Based Retrieval")
print("=" * 80)

for txn_id in ["TXN-1005", "TXN-1012", "TXN-9999"]:
    result = feature_store_lookup(txn_id)
    print(f"\n  Lookup: {txn_id}")
    if "error" in result:
        print(f"  Result: {result['error']}")
    else:
        print(f"  Part ordered      : {result['part_name']}")
        print(f"  Invoice amount    : ${result['invoice_amount']}")
        print(f"  Shipping carrier  : {result['shipping_carrier']}")
        print(f"  Expected delivery : {result['expected_delivery_date']}")
        print(f"  Status            : {result['shipping_status']}")
        print(f"  Tracking number   : {result['tracking_number']}")

# COMMAND ----------

# ── 4. Show WHY vector search fails for this data ─────────────────

print("\n" + "=" * 80)
print("WHY VECTOR SEARCH IS WRONG FOR THIS DATA")
print("=" * 80)
print("""
Imagine embedding these rows as text and searching semantically:

  Query: "When will transaction TXN-1005 arrive?"

  Vector search returns the 3 most SEMANTICALLY SIMILAR rows:
    1. TXN-1008 (talks about 'arrive' and 'delivery')    <- WRONG transaction!
    2. TXN-1003 (mentions 'expected delivery date')      <- WRONG transaction!
    3. TXN-1005 (the correct one -- if you are lucky)    <- MIGHT be here

  Problems:
  - Semantic similarity does not understand primary keys
  - ALL rows contain similar words ('delivery', 'shipping', 'order')
  - The correct row is NOT guaranteed to be the top result
  - Data changes hourly -- re-embedding 100K orders is expensive

  Feature Store lookup returns EXACTLY the right row, every time:
    WHERE transaction_id = 'TXN-1005'  -->  100% accurate, <10ms
""")

# ── 5. Decision flowchart ────────────────────────────────────────

print("=" * 80)
print("DECISION GUIDE: Feature Store vs Vector Search vs Fine-Tuning")
print("=" * 80)
print("""
  Is the data STRUCTURED with a known primary key (order_id, user_id)?
  |                                                                    
  +-- YES --> Does it change frequently (daily/hourly)?                
  |     |                                                              
  |     +-- YES --> Feature Store / Feature Serving endpoint           
  |     |           (real-time key lookup, always fresh)               
  |     |                                                              
  |     +-- NO  --> SQL query or Feature Store                         
  |                 (batch lookup is fine for static data)             
  |                                                                    
  +-- NO  --> Is it unstructured text (docs, policies, articles)?      
        |                                                              
        +-- YES --> Extract -> Chunk -> Embed -> Vector Search Index   
        |                                                              
        +-- NO  --> Is it general world knowledge the model lacks?     
              |                                                        
              +-- YES --> Fine-tune (expensive, last resort)            
              +-- NO  --> Prompt engineering (add instructions)         
""")

# COMMAND ----------

