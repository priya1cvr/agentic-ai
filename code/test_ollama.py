import os 
import requests

#Set Threads
os.environ["OLLAMA_NUM_THREADS"] = "4"

#model auto-unload after inactivity
#os.environ["OLLAMA_KEEP_ALIVE"] = "0" 
# OLLAMA_KEEP_ALIVE must be set for Ollama server, not Python
# export OLLAMA_KEEP_ALIVE=0 must be done in os level

url = "http://localhost:11434/api/generate"

payload ={
    "model": "gemma:2b",   #"gemma4:e4b",
    "prompt": "Explain Spark partitioning in simple terms",
    "stream": False,
    "options": {
        "num_ctx": 512,     # reduce memory
        "num_predict": 500 , # limit output size
        "temperature": 0.7
    },
     "keep_alive": 0 # unloads the model after python completes
}
response = requests.post(url, json=payload)
# Print full response (for debugging)
print("RAW RESPONSE:")
print(response.json())

# Print only model output
print("\nMODEL OUTPUT:")
print(response.json()["response"])