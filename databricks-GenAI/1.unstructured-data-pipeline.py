# Databricks notebook source
# MAGIC %md
# MAGIC This notebook creates a data pipeline using the following steps:<br>
# MAGIC
# MAGIC - Download sample PDF files from the GitHub repository Databricks demo dataset https://github.com/databricks-demos/dbdemos-dataset/tree/main. <br>
# MAGIC - Load documents into a Delta table.<br>
# MAGIC - Parse documents into text strings.<br>
# MAGIC - Chunk the text strings into smaller, more manageable pieces for retrieval.<br>
# MAGIC - Use an embedding model to embed the chunks into vectors and store the results in a vector index.<br>

# COMMAND ----------

# from databricks.sdk import WorkspaceClient
# from databricks.sdk.service.compute import DataSecurityMode

# w = WorkspaceClient()
# cluster = w.clusters.create(
#     cluster_name="ml-genai-pipeline-cluster",
#     spark_version="16.4.x-cpu-ml-photon-scala2.12",
#     node_type_id="m5.xlarge",
#     num_workers=0,
#     autotermination_minutes=60,
#     data_security_mode=DataSecurityMode.SINGLE_USER,
#     single_user_name="priya1cvr.pb@gmail.com",
# )
# print("Cluster ID:", cluster.cluster_id)
# print("State:", cluster.state)


# COMMAND ----------

# DBTITLE 1,Verify Databricks Runtime ML 14.3+
# Verify the attached compute: should show a Databricks Runtime ML version >= 14.3
# try:
#     runtime = spark.conf.get("spark.databricks.clusterUsageTags.sparkVersion")
#     print(f"Databricks Runtime: {runtime}")
#     if "-ml-" in runtime:
#         print("✓ Running on a Databricks Runtime ML cluster")
#     else:
#         print("✗ Not an ML runtime — attach a cluster with Databricks Runtime ML 14.3+")
# except Exception:
#     print("Runtime version tag not accessible — you are likely on serverless compute.")
#     print("Attach a dedicated cluster running Databricks Runtime ML 14.3+ and re-run this cell.")

# COMMAND ----------

# NOTE: pydantic, mlflow, databricks-sdk, pyyaml are preinstalled in the runtime — don't reinstall them.
# NOTE: tiktoken>=0.8.0 (not ==0.7.0) — the preinstalled databricks-agents requires tiktoken>=0.8.
%pip install -U \
  "databricks-ai-search" \
  "pymupdf4llm==0.0.5" \
  "pymupdf==1.24.13" \
  "markdownify==0.12.1" \
  "transformers==4.41.1" \
  "tiktoken>=0.8.0" \
  "langchain-text-splitters==0.2.0" \
  "pypandoc_binary==1.13"

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **The "Before": Life WITHOUT SerializableModel**
# MAGIC
# MAGIC Imagine you have a text file (config.yaml) that describes a team of agents. It looks like this standard YAML:
# MAGIC
# MAGIC ```yaml
# MAGIC team_name: "Alpha Squad"
# MAGIC agents:
# MAGIC   - name: "Genie"
# MAGIC     skills: ["coding"]
# MAGIC   - name: "Finder"
# MAGIC     search_engine: "Bing"
# MAGIC ```
# MAGIC
# MAGIC Now, you write a Python script to read this file and turn it back into Python objects so you can run your application.
# MAGIC
# MAGIC The Problem: <br>
# MAGIC
# MAGIC Look closely at the agents list in the YAML. The first agent has skills. The second agent has a search_engine. They are two completely different Python classes (GenieAgentConfig vs WebSearchAgentConfig).
# MAGIC When your Python code reads the YAML into a plain dictionary, it just sees a generic list of text:
# MAGIC
# MAGIC ```python
# MAGIC import yaml
# MAGIC
# MAGIC # Read the file
# MAGIC with open("config.yaml") as f:
# MAGIC     data = yaml.safe_load(f)
# MAGIC
# MAGIC # Python now loops through the agents to build them:
# MAGIC for agent_data in data["agents"]:
# MAGIC     # ❌ PROBLEM: How does Python know which class to instantiate?
# MAGIC     # Should it call GenieAgentConfig(**agent_data) or WebSearchAgentConfig(**agent_data)?
# MAGIC     # There is NO information in the YAML telling Python what class this data belongs to!
# MAGIC
# MAGIC ```
# MAGIC
# MAGIC To fix this without SerializableModel, you would have to write a massive, messy if/else statement inside your code:
# MAGIC <br>
# MAGIC ```python
# MAGIC # The ugly manual way:
# MAGIC if "skills" in agent_data:
# MAGIC     agent = GenieAgentConfig(**agent_data)
# MAGIC elif "search_engine" in agent_data:
# MAGIC     agent = WebSearchAgentConfig(**agent_data)
# MAGIC ```
# MAGIC
# MAGIC Why this breaks down: Every single time you or a coworker creates a new type of agent (e.g., a DatabaseAgent), you have to go back into the core framework code and add another elif block. If you forget, the system crashes. <br>
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC **Serialization Class**
# MAGIC
# MAGIC This system allows you to save a configuration (like settings for an agent or a tool) into a YAML file, and then load it back later without having to manually import the specific Python class first. <br>
# MAGIC Think of it like putting a "Return Address Label" on an envelope. When you save (serialize) the data, the system automatically writes down exactly where the Python code lives on your computer. When you open (deserialize) it, the system reads that label, goes and finds the code automatically, and rebuilds your object. <br>
# MAGIC Here is the step-by-step guide to building this, moving from the simplest scenario to the more advanced one.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **The "After": How SerializableModel Solves This**
# MAGIC
# MAGIC SerializableModel solves this by forcing the YAML file to remember the exact Python recipe needed to rebuild the class.
# MAGIC When you use SerializableModel, the YAML file automatically saves looking like this: <br><br>
# MAGIC
# MAGIC ```yaml
# MAGIC _class_path: my_project.agents.MultiAgentConfig
# MAGIC team_name: "Alpha Squad"
# MAGIC agents:
# MAGIC   - _class_path: my_project.agents.GenieAgentConfig
# MAGIC     name: "Genie"
# MAGIC     skills: ["coding"]
# MAGIC   - _class_path: my_project.agents.WebSearchAgentConfig
# MAGIC     name: "Finder"
# MAGIC     search_engine: "Bing"
# MAGIC ```
# MAGIC
# MAGIC
# MAGIC The Solution in Action:
# MAGIC
# MAGIC Now, look how clean and hands-off your loader code becomes. You don't need if/else statements anymore: <br>
# MAGIC
# MAGIC ``` python
# MAGIC # The universal loader way:
# MAGIC def load_obj_from_yaml(yaml_str):
# MAGIC     data = yaml.safe_load(yaml_str)
# MAGIC     
# MAGIC     # 1. Look at the label: "my_project.agents.MultiAgentConfig"
# MAGIC     class_path = data.pop("_class_path") 
# MAGIC     
# MAGIC     # 2. Python dynamically finds and imports that exact class on the fly
# MAGIC     target_class = dynamically_import_class(class_path)
# MAGIC     
# MAGIC     # 3. Let that class build itself and its sub-agents using their own labels
# MAGIC     return target_class._load_class_from_dict(data)
# MAGIC
# MAGIC ```
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC - • WHAT is it? It's a way to save configuration settings into text files (YAML) alongside a "hidden map" pointing back to the Python code that knows how to use those settings.
# MAGIC - • WHY are we writing it? To keep our app completely modular. We want the ability to add new agents or tools to our system in the future without changing the core engine code.
# MAGIC - • WHEN is it needed? When you have a collection of different types of objects stored in a single list (e.g., a multi-agent team composed of one ChatAgent, one CodingAgent, and one SearchToolAgent).
# MAGIC - • WHERE is it used? In production deployment environments or APIs. When a customer sends a request to your API with a complex YAML setup, your server needs to spin up the exact right agents instantly.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Step 1: The Foundation (SerializableModel) <br>
# MAGIC
# MAGIC Every configuration class you make must inherit from a base class called SerializableModel. This base class handles writing the "Return Address Label" (_CLASS_PATH_KEY) for you.

# COMMAND ----------

from pydantic import BaseModel 
import importlib 
import yaml 

# The "Return Address Label" key name
# just a constant holding the name of a dictionary key
_CLASS_PATH_KEY = "_class_path"

# What it stores: the string "_class_path" is the label of the field where the "return address" (the Python class location) gets written. 
# When your config is serialized, the output dict/YAML looks like this: chunk_size: 512 ,chunk_overlap: 64 ,_class_path: __main__.ChunkingConfig   <-- the return address lives here

class SerializableModel(BaseModel):
    def model_dump(self, **kwargs):
        # 1. Get the normal dictionary representation from Pydantic
        data = super().model_dump(**kwargs)
        # 2. Add the dynamic Python path of this specific class
        cls = self.__class__
        data[_CLASS_PATH_KEY] = f"{cls.__module__}.{cls.__name__}"
        print("data from SerializableModel is: ",data)
        print("\n")
        return data
    
    @classmethod
    def _load_class_from_dict(cls, data:dict):
        # Default behavior: Just unpack the dictionary into the Pydantic model
        return cls(**data)


# COMMAND ----------

# MAGIC %md
# MAGIC What @classmethod means
# MAGIC It's a decorator that changes what the first argument of the method receives:
# MAGIC <br>
# MAGIC
# MAGIC | Regular method | @classmethod |
# MAGIC |---|---|
# MAGIC | First arg is `self` = a specific object you already created | First arg is `cls` = the class itself |
# MAGIC | Must create an instance first: `obj = ChunkingConfig(...)` then `obj.method()` | Call directly on the class: `ChunkingConfig.method(...)` — no instance needed |
# MAGIC
# MAGIC <br>
# MAGIC The killer feature for the serialization design: inheritance. When a subclass inherits _load_class_from_dict, the cls inside it becomes the subclass. So the same inherited method builds the right type every time — this is why the doc uses cls(**data). <br>
# MAGIC
# MAGIC How to call it
# MAGIC SerializableModel is a foundation — you don't call it directly with data. You (1) subclass it with your fields, then (2) call the classmethod on the subclass:
# MAGIC

# COMMAND ----------

# DBTITLE 1,Cell 10
# How to call it
class ChunkingConfig(SerializableModel):
    chunk_size: int
    chunk_overlap: int
    model_name: str = "databricks-bge-large-en"

obj = ChunkingConfig(chunk_size=512, chunk_overlap=64)
print("Printing obj.model_dump")
print("\n")
print(obj.model_dump())
print("\n")
print(f"type: {type(obj).__name__}, chunk_size: {obj.chunk_size}, model: {obj.model_name} , _class_path: {obj.model_dump()['_class_path']} ")
print("\n object.model_dump finished \n")
# --- How _load_class_from_dict is invoked ---
# It's a @classmethod, so you call it ON THE CLASS, no instance needed:
#     ChunkingConfig._load_class_from_dict(data)
# Inside the method, 'cls' is then ChunkingConfig itself, so cls(**data)
# rebuilds exactly that subclass (not the base class).

d = obj.model_dump()        # dict incl. the "return address" key '_class_path'
print("Before Pop")
print(d)
d.pop("_class_path", None)  # Deletes the "_class_path" entry from d , d now holds only the real config fields 

print("\n","After Pop")
print(f"type: {type(d).__name__}, chunk_size: {d['chunk_size']}, model: {d['model_name']} , _class_path: {d.get('_class_path')} \n \n ")
rebuilt = ChunkingConfig._load_class_from_dict(d)   #   means: It's the final step of the round-trip — turning a plain dict back into a live object:
print("rebuilt :",rebuilt)
print("--------------")
print(f"type: {type(rebuilt).__name__}, chunk_size: {rebuilt.chunk_size}, model: {rebuilt.model_name}  ")

# COMMAND ----------

# MAGIC %md
# MAGIC Note in above output After Pop _class_path is None

# COMMAND ----------

import yaml
e = obj.model_dump()  
rebuilt = ChunkingConfig._load_class_from_dict(e)   # <-- the invocation
print("rebuilt :",rebuilt)
print("\n ==========yaml dump======= \n")
print(yaml.dump(e))



# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Step 2: The Universal Loader Helper**
# MAGIC
# MAGIC
# MAGIC You need a single function that reads the YAML string, looks at the label, finds the class dynamically, and loads it.

# COMMAND ----------

def load_obj_from_yaml(yaml_str: str):
    # 1. Parse the YAML into a standard Python dictionary
    data = yaml.safe_load(yaml_str)
    
    # 2. Extract the "Return Address Label"
    class_path = data.pop(_CLASS_PATH_KEY, None)
    if not class_path:
        raise ValueError("Missing class path in YAML data!")
        
    # 3. Dynamically import the class using Python's importlib
    module_name, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    target_class = getattr(module, class_name)
    print(f"module_name: {module_name} , class_name: {class_name} , Imported class: {target_class}")
    
    # 4. Hand the remaining data over to that class to build itself
    return target_class._load_class_from_dict(data)


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Step 3: Beginner Scenario (No Sub-Configs)**
# MAGIC
# MAGIC If your config only contains basic items like strings, numbers, or standard lists (e.g., GenieAgentConfig), you don't have to do anything extra.

# COMMAND ----------

# Just inherit from SerializableModel. That's it!
class GenieAgentConfig(SerializableModel):
    name: str
    temperature: float


# COMMAND ----------

## How to use it:
# 1. Create it
config = GenieAgentConfig(name="Genie", temperature=0.5)

# 2. Dump it to YAML
dictionary_data = config.model_dump()
yaml_string = yaml.safe_dump(dictionary_data)
print("dictionary_data: ",dictionary_data)
print("yaml_string: ",yaml_string)

# 3. Load it back dynamically (without knowing it's a GenieAgentConfig)
loaded_config = load_obj_from_yaml(yaml_string)
print(type(loaded_config))  # <class 'your_module.GenieAgentConfig'>
print("=================")
print(loaded_config)  # GenieAgentConfig(name='Genie', temperature=0.5)


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Step 4: Advanced Scenario (Has Sub-Configs)**
# MAGIC
# MAGIC
# MAGIC If your config contains a list of other dynamic SerializableModel objects (like a MultiAgentConfig containing a list of different types of agents), you must manually tell the system how to dump and load those sub-objects.
# MAGIC
# MAGIC How to write it:
# MAGIC

# COMMAND ----------

class MultiAgentConfig(SerializableModel):
    team_name: str
    # A list that could contain GenieAgentConfig, DevAgentConfig, etc.
    agents: list[SerializableModel]

    #Override 1 : Custom Dumping
    def model_dump(self, **kwargs):
        # Get the standard dump first
        data = super().model_dump(**kwargs)
        
        # Manually force each sub-agent to call its own model_dump() 
        # so they get their own custom labels written down
        data["agents"] = [agent.model_dump(**kwargs) for agent in self.agents]

        # CRITICAL: without this return statement the method returns None,
        # and yaml.safe_dump(None) prints 'null'
        return data
    
    # OVERRIDE 2: Custom Loading
    @classmethod
    def _load_class_from_dict(cls, data:dict):
        agents_data = data.pop("agents",[])
        rebuilt_agents = []

        # Loop through each raw sub-agent dictionary
        for agent_dict in agents_data:
            # Dynamically look up and load the sub-agent using its label
            class_path = agent_dict.pop(_CLASS_PATH_KEY)
            module_name, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            sub_class = getattr(module, class_name)
            # Rebuild the sub-agent
            rebuilt_agents.append(sub_class._load_class_from_dict(agent_dict))
            
        # Put the rebuilt sub-agents back and instantiate the main config
        data["agents"] = rebuilt_agents
        return cls(**data)


# COMMAND ----------

# MAGIC %md
# MAGIC - Rule 1: Always inherit your custom settings class from SerializableModel.
# MAGIC - Rule 2: If your class just holds normal data (strings, integers), you are done.
# MAGIC - Rule 3: If your class holds a list/dict of other dynamic configs, you must override model_dump (to save their inner labels) and _load_class_from_dict (to read their inner labels).
# MAGIC - Rule 4: Always use load_obj_from_yaml(yaml_string) when reading your configuration back.
# MAGIC

# COMMAND ----------

# 1. SETUP: Define your individual agents
class GenieAgentConfig(SerializableModel):
    name: str
    skills: list[str]

class WebSearchAgentConfig(SerializableModel):
    name: str
    search_engine: str

# 2. RUNTIME STEP 1: Create your agent team in Python
my_team = MultiAgentConfig(
    team_name="Alpha Squad",
    agents=[
        GenieAgentConfig(name="Genie", skills=["coding", "math"]),
        WebSearchAgentConfig(name="Finder", search_engine="Bing")
    ]
)

# 3. RUNTIME STEP 2: Serialize it (Save it to YAML)
# Because you overrode `model_dump`, it handles both the main config AND the sub-configs!
team_dict = my_team.model_dump()
yaml_output = yaml.safe_dump(team_dict)

print("--- SAVED YAML CONTENT ---")
print(yaml_output)


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **How to load it back (The Magic part):**
# MAGIC
# MAGIC Now, imagine this is a completely different computer or a fresh script. It receives that yaml_output string. It doesn't know GenieAgentConfig exists. You just call this:

# COMMAND ----------

# 4. RUNTIME STEP 3: Load it back blindly using the universal loader
rebuilt_team = load_obj_from_yaml(yaml_output)

# 5. VERIFY: Check that everything was restored perfectly
print("\n--- REBUILT OBJECT ---")
print(f"Team Name: {rebuilt_team.team_name}")
print(f"Agent 1 Type: {type(rebuilt_team.agents[0])}") # Automatically turned back into GenieAgentConfig!
print(f"Agent 2 Type: {type(rebuilt_team.agents[1])}") # Automatically turned back into WebSearchAgentConfig!
