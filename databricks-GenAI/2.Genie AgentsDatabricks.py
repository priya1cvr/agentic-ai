# Databricks notebook source
# MAGIC %md
# MAGIC **Construct hybrid RAG using Genie Agents**
# MAGIC
# MAGIC Construct a full hybrid Retrieval-Augmented Generation (RAG) system directly inside Databricks using the new Genie Agents framework. Instead of writing complex vectorization, embedding, and LLM orchestration code yourself, the setup relies on Databricks to manage the heavy lifting natively over your Unity Catalog (UC) assets.
# MAGIC
# MAGIC Here is the step-by-step logic of what we need to accomplish: <br>
# MAGIC
# MAGIC 1. Unified the Data Layer (Structured + Unstructured)
# MAGIC
# MAGIC Genie Agents have two ways of interacting with data: Chat Mode (which dynamically translates your prompts into text-to-SQL commands to read tables) and Agent Mode (which performs continuous reasoning over documents).
# MAGIC By executing Steps 2 and 3, we prepared a real-world testing ground that forces Genie to use both modes simultaneously:
# MAGIC -  The Structured Layer: We created a Delta table (vendor_directory) that tracks columns like vendor_name and compliance_status.
# MAGIC -  The Unstructured Layer: We spun up a Unity Catalog Managed Volume (knowledge_base) and used Python to write a raw text file (sop_compliance.txt) directly into it.
# MAGIC
# MAGIC
# MAGIC 2. Connected the Assets to Genie (The Context Bridge)
# MAGIC
# MAGIC In Step 4, we bridge these two isolated data formats into a singular Genie Space.
# MAGIC - When you attach a Unity Catalog Volume to a Genie Agent, Databricks automatically reads, chunks, and creates a background index of the text/PDF files inside that volume.
# MAGIC - You don't have to build a vector database, configure embeddings, or maintain search indexes manually.
# MAGIC
# MAGIC 3. Programmatic Orchestration via SDK
# MAGIC
# MAGIC Instead of just chatting inside a static web UI, Step 5 leverages the Databricks Python SDK to run the agent programmatically inside a notebook pipeline.
# MAGIC -  We initialized a stateful conversation thread using w.genie.start_conversation().
# MAGIC - We fed it a highly contextual prompt: "What happens to our automated pipeline ingestion when a vendor is flagged as 'Under Review'?"
# MAGIC
# MAGIC 4. Cross-Context Reasoning (How Genie Responded)
# MAGIC
# MAGIC To answer that specific question, a standard LLM or a basic text-to-SQL engine would fail because the answer doesn't exist in one single place. Here is how the Genie Agent processed it under the hood:
# MAGIC 1. SQL Mode Lookup: It scans the structured vendor_directory table to understand what "Under Review" means and identifies the associated entity (e.g., Global Apex Storage).
# MAGIC 2. Agent Volume Search: It simultaneously triggers a search query across the attached Unity Catalog Volume documents to look up the exact Standard Operating Procedure (SOP) rule for "Under Review".
# MAGIC 3. Synthesis: It extracts the instruction from the text file ("immediately pause automated pipeline ingestion triggers"), binds it to the vendor data, and synthesizes a natural language response with precise citations back to the source text inside your S3-backed volume.
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Step 2: Initialize Unity Catalog and a Managed Volume**
# MAGIC
# MAGIC Run these SQL queries to initialize your namespaces and set up the Unity Catalog Volume. Volumes are the governed file storage locations in Databricks where unstructured PDFs, TXTs, or DOCX files reside.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Cell 1: SQL
# MAGIC CREATE CATALOG IF NOT EXISTS enterprise_dev;
# MAGIC USE CATALOG enterprise_dev;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS data_agent_store;
# MAGIC USE SCHEMA data_agent_store;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create a Managed Volume to host unstructured text/PDF documents
# MAGIC CREATE VOLUME IF NOT EXISTS enterprise_dev.data_agent_store.knowledge_base;

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Step 3: Populate Your Data (Structured Table + Volume Files)**
# MAGIC
# MAGIC Genie excels at reasoning over structural metrics and matching cross-context data simultaneously. Let’s stage a structured vendor table and upload unstructured files to the Volume using dbutils

# COMMAND ----------

# Cell 2: Python
# 1. Create a structured table to ground our structured queries 
spark.sql("""
CREATE TABLE IF NOT EXISTS enterprise_dev.data_agent_store.vendor_directory AS 
SELECT 101 AS vendor_id, 'S3 Logistic Services' AS vendor_name, 'Active' AS compliance_status
UNION ALL
SELECT 102 AS vendor_id, 'Global Apex Storage' AS vendor_name, 'Under Review' AS compliance_status
""")

# 2. Write an unstructured documentation file straight to the UC Volume
volume_path = "/Volumes/enterprise_dev/data_agent_store/knowledge_base/sop_compliance.txt"

sop_content = """
STANDARD OPERATING PROCEDURE FOR VENDORS:
- All Active vendors must execute a secure raw data load sequence to an S3/NAS container.
- If a vendor status enters 'Under Review', immediately pause automated pipeline ingestion triggers.
- For escalated checksum errors, notify the lead framework architect immediately.
"""

dbutils.fs.put(volume_path, sop_content, overwrite=True)
print("Structured and Unstructured data grounded successfully.")


# COMMAND ----------




# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM enterprise_dev.data_agent_store.vendor_directory;

# COMMAND ----------

# DBTITLE 1,Cell 7
# MAGIC %sql
# MAGIC SELECT * FROM read_files(
# MAGIC   '/Volumes/enterprise_dev/data_agent_store/knowledge_base/sop_compliance.txt',
# MAGIC   format => 'text'
# MAGIC )

# COMMAND ----------

# MAGIC %md
# MAGIC **Step 4: Provision the Genie Agent (UI Context)**
# MAGIC
# MAGIC As of late 2026, creating and defining new baseline Genie Spaces is natively handled via the low-code interface, while runtime interactions are automated.
# MAGIC 1. Look at the left sidebar menu of your Databricks space and click Genie Agents.
# MAGIC 2. Click New in the top right corner.
# MAGIC 3. Give it a name (e.g., Vendor Compliance Assistant).
# MAGIC 4. Under Sources, add your structured dataset: enterprise_dev.data_agent_store.vendor_directory.
# MAGIC 5. Click Add Source -> select Volumes -> check knowledge_base to automatically index the file layer.
# MAGIC 6. Copy the Space ID from the URL string or the Settings tab of the agent space. It will look similar to an alphanumeric GUID string (e.g., 01ef-xyz...)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Step 5: Query Your Volume and Tables via Python SDK**
# MAGIC
# MAGIC Now we can implement programmatic Agent Mode queries directly inside our Databricks Notebook. Ensure your environment has the latest SDK copy installed

# COMMAND ----------

#01f1d5cf3d5f13908c9f9c9510985aed?o=239435194635763
# Cell 3: Python
# Ensure the correct SDK layer is initialized
%pip install --upgrade databricks-sdk
dbutils.library.restartPython()



# COMMAND ----------

# Cell 4: Python
from databricks.sdk import WorkspaceClient

# Replace with the Space ID retrieved from your Genie Agent space settings
GENIE_SPACE_ID = "01f1d5cf3d5f13908c9f9c9510985aed" 

w = WorkspaceClient()

# Start a stateful conversational thread over Unity Catalog
conversation = w.genie.start_conversation(
    space_id=GENIE_SPACE_ID,
    content="What happens to our automated pipeline ingestion when a vendor is flagged as 'Under Review'?"
)

print(f"Conversation Started! ID: {conversation.conversation_id}")


# COMMAND ----------

# DBTITLE 1,Cell 12
# Cell 5: Python
# Fetch the response generated by the agent tracking cross-context parameters
messages = w.genie.list_conversation_messages(
    space_id=GENIE_SPACE_ID,
    conversation_id=conversation.conversation_id
)

# Pull the final markdown summary output compiled via Agent Mode
latest_message = messages.messages[-1]
answer = next(a.text.content for a in latest_message.attachments if a.text is not None)
print("Genie Agent Response:")
print(answer)


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Why You Are Getting This above Answer <br>
# MAGIC
# MAGIC The Genie Agent sent a rejection because the Python SDK call w.genie.start_conversation() defaults to Chat Mode, which strictly ignores unstructured files in Unity Catalog Volumes. <br>
# MAGIC As detailed in Databricks' runtime specifications:
# MAGIC - Chat Mode: Can only query and reason over structured Delta tables via text-to-SQL translation. It cannot search text documents or files.
# MAGIC - Agent Mode: Is required to process unstructured files in a Volume because it executes deeper multi-step reasoning loops and semantic search over text.
# MAGIC Because your code initialised a regular start_conversation (Chat Mode), Genie looked only at your structured vendor_directory table. Since that table does not contain a column or text regarding "automated pipeline ingestion," the Agent correctly declared that the question was unrelated to the available database schemas

# COMMAND ----------

from databricks.sdk import WorkspaceClient
import time

GENIE_SPACE_ID = "01f1d5cf3d5f13908c9f9c9510985aed"
w = WorkspaceClient()

# 1. Start the conversation with your explicit question to satisfy the SDK requirement
conversation = w.genie.start_conversation(
    space_id=GENIE_SPACE_ID,
    content="What happens to our automated pipeline ingestion when a vendor is flagged as 'Under Review'?"
)

print(f"Conversation initialized successfully. ID: {conversation.conversation_id}")

# 2. Give Genie a few seconds to run its agentic loop over the tables and volumes
print("Waiting for Genie Agent reasoning loop to complete...")
time.sleep(5) 

# 3. Pull the messages using your verified working extraction logic
messages = w.genie.list_conversation_messages(
    space_id=GENIE_SPACE_ID,
    conversation_id=conversation.conversation_id
)

# 4. Extract the final text content compiled from your UC Volume
latest_message = messages.messages[-1]
answer = next(a.text.content for a in latest_message.attachments if a.text is not None)

print("\nGenie Agent Response:")
print(answer)


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Why the UI/Agent is still giving you this response:<br>
# MAGIC
# MAGIC The UI response confirms exactly why your Python script is failing to see the volume content: <br>
# MAGIC The Genie Agent is completely ignoring your unstructured volume file right now and is only reading your structured table.<br>
# MAGIC Notice that the UI answer only pulls the vendor_id and names from the Delta table but entirely misses the SOP instructions about "immediately pause automated pipeline ingestion triggers" that we put in the text file.
# MAGIC
# MAGIC You cannot see "Volume" in that menu because your workspace administrator hasn't enabled the Public Preview feature for analyzing files in Genie Agents.<br>
# MAGIC By default, Genie spaces are built strictly for SQL Assets (Tables, Functions, Metrics, and Connectors). The ability to attach unstructured files via a Unity Catalog Volume is a separate, hidden feature flag that must be manually flipped in the admin control center <br>
# MAGIC
# MAGIC
# MAGIC The Workaround for Free Edition: <br>
# MAGIC
# MAGIC If you want to complete this task in your current workspace without upgrading, you can bypass the Volume feature completely by converting your text document into a structured Delta Table. This forces Genie back into its native Chat/SQL mode, which works perfectly in the Free Edition:
# MAGIC Replace Step 3 in your notebook with this Python block to load the rules as a table:

# COMMAND ----------

# Create a structural text reference table for Genie instead of using a Volume
spark.sql("""
CREATE TABLE IF NOT EXISTS enterprise_dev.data_agent_store.pipeline_rules (
    rule_id INT,
    topic STRING,
    standard_operating_procedure STRING
)
""")

spark.sql("""
INSERT INTO enterprise_dev.data_agent_store.pipeline_rules VALUES 
(1, 'Vendor Compliance Ingestion', 'All Active vendors must execute a secure raw data load sequence to an S3/NAS container. If a vendor status enters Under Review, immediately pause automated pipeline ingestion triggers. For escalated checksum errors, notify the lead framework architect immediately.')
""")

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from enterprise_dev.data_agent_store.pipeline_rules

# COMMAND ----------

# MAGIC %md
# MAGIC 1. Go back into your Genie Space UI (01f1d5cf3d5xxxxxxd).
# MAGIC 2. Click Add Source -> select Table.
# MAGIC 3. Add this new pipeline_rules table.
# MAGIC 4. Try asking your question again. Genie will instantly map it, convert it to a Text-to-SQL command, and give you the correct policy answer.
# MAGIC
# MAGIC See below screenshot in genie UI
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ![image_1793525816153.png](./image_1793525816153.png "image_1793525816153.png")
# MAGIC

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC For Inactive status it clearly shows there is no rule present <br>
# MAGIC ![image_1793527959920.png](./image_1793527959920.png "image_1793527959920.png")

# COMMAND ----------

# MAGIC %md
# MAGIC Now, to run this exact query programmatically via your Databricks Python Notebook using Agent Mode (Synchronous API execution), we need to adapt the code to look up the structured tables.
# MAGIC
# MAGIC 1. The Operational PySpark SDK Code
# MAGIC
# MAGIC Run this updated code pattern in your Databricks notebook. Since we shifted from unstructured files (Volumes) to a structured layout (Tables), this code executes a structured agent runner loop that ensures the exact text result seen in the UI is returned cleanly to your Python environment.
# MAGIC
# MAGIC
# MAGIC response.attachments / Natural Language Layer: This fetches the compiled summary. It reads the final text response generated by Genie's internal LLM layer (the Markdown sentence explaining that the pipeline is paused

# COMMAND ----------

from databricks.sdk import WorkspaceClient

# Paste your active space ID from your URL
GENIE_SPACE_ID = "01f1d5cf3d5f13908c9f9c9510985aed" 
w = WorkspaceClient()

print("Initializing Agent runner over structured schema space...")

# 1. Trigger the synchronous blocking API. This forces the background 
# Genie engine to execute its code analysis and generate the result table.
response = w.genie.start_conversation_and_wait(
    space_id=GENIE_SPACE_ID,
    content="What happens to our automated pipeline ingestion when a vendor is flagged as 'Under Review'?"
)

print(f"Agent Execution Complete. Thread ID: {response.conversation_id}\n")

# 2. Extract and print the natural language answer generated by the agent
print("Genie Agent Summary Response:")
for attachment in response.attachments:
    if attachment.text is not None:
        print(attachment.text.content)


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC 2. How to Fetch the Raw Underlying Data Frame Natively
# MAGIC
# MAGIC Because the agent generated a physical Result table (1 row) behind the scenes, you can also programmatically extract the exact data frame or SQL query code it ran directly into your notebook for further data engineering tasks!
# MAGIC Add this final cell to your notebook to see what Genie generated under the hood
# MAGIC
# MAGIC w.genie.get_message_attachment_query_result / Raw Data Layer: This bypasses the natural language generation and tries to grab the exact dataframe rows that were read from your Delta tables before the LLM wrote its summary.

# COMMAND ----------

# 3. Pull the detailed message trace history
messages = w.genie.list_conversation_messages(
    space_id=GENIE_SPACE_ID,
    conversation_id=response.conversation_id
)

# Extract the final message from the conversation list
latest_message = messages.messages[-1]

print("\n--- Technical Data Engineering Lineage ---")
for attachment in latest_message.attachments:
    
    # Check for text response attributes
    if attachment.text is not None:
        print(f"Genie Summary: {attachment.text.content}\n")
        
    # Check for structural query attributes
    if attachment.query is not None:
        print(f"Generated SQL Code: \n{attachment.query.query}\n")
        print(f"Query Description: {attachment.query.description}\n")
        
        # Correct pattern: Fetch the dataset results using the dedicated API endpoint
        print("Fetching underlying result table rows from workspace...")
        try:
            query_result = w.genie.get_message_attachment_query_result(
                space_id=GENIE_SPACE_ID,
                conversation_id=response.conversation_id,
                message_id=latest_message.id,
                attachment_id=attachment.attachment_id
            )
            
            # Print the table's structural column names
            columns = [col.name for col in query_result.manifest.schema.columns]
            print(f"Output Columns Extracted: {columns}")
            
            # Optional: Print raw row values if available in the result payload
            if query_result.data_array:
                print(f"Extracted Sample Row Data: {query_result.data_array}")
                
        except Exception as e:
            print(f"Could not retrieve raw row values (might require cluster privileges): {e}")


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Why this setup is clean:
# MAGIC
# MAGIC By moving your text rules into a structured table, you've optimized the query path for the Databricks Free Edition. The agent will now execute consistently both in the UI and programmatically via your Python SDK pipelines, providing a clear path forward for your data engineering workflows.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Breakdown of Your Code Output
# MAGIC
# MAGIC Your execution logs show exactly how Genie processed your data engineering metadata context under the hood:
# MAGIC
# MAGIC A. The Generated SQL Code
# MAGIC
# MAGIC sql
# MAGIC SELECT vd.`vendor_id`, vd.`vendor_name`, vd.`compliance_status`, pr.`standard_operating_procedure`
# MAGIC FROM `enterprise_dev`.`data_agent_store`.`vendor_directory` vd
# MAGIC LEFT JOIN `enterprise_dev`.`data_agent_store`.`pipeline_rules` pr
# MAGIC   ON pr.`topic` = 'Vendor Compliance Ingestion'
# MAGIC WHERE vd.`compliance_status` = 'Under Review'
# MAGIC
# MAGIC What happened here:<br> Genie automatically figured out a relational logic mapping without you telling it to do so. It saw your question, looked at its data dictionary, and decided to execute a LEFT JOIN connecting your vendor tracking metrics table (vendor_directory) with your text compliance table (pipeline_rules) filtering strictly by the operational condition state WHERE vd.compliance_status = 'Under Review'.

# COMMAND ----------

