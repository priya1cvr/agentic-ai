from dotenv import load_dotenv
import os
from openai import OpenAI
 
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

resp = client.chat.completions.create(
    model="gpt-4o-mini",  # cost-effective
    messages=[{"role": "user", "content": "Explain Spark partitioning simply"}]
)

print(resp.choices[0].message.content)