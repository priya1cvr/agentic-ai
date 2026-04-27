import pandas as pd
import ollama
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)  
# Unload the model to free up RAM immediately
MODEL_NAME = 'gemma:2b'
ollama.generate(model=MODEL_NAME, keep_alive=0)

def call_local_gemma(prompt, is_json=False):
    #ollama uses 'json' as a string for the format parameter
    format_type = 'json' if is_json else ''

    try:
        response = ollama.generate(
            model=MODEL_NAME,
            prompt=prompt,
            format=format_type
        )
        # In Ollama, the result is in the ['response'] key
        return response['response']
    except Exception as e:
        return f"Error: {e}"



# Load your spreadsheet
df = pd.read_excel('../data/cust_data.xlsx',engine='openpyxl')
print(df.head(10))
print("\n")

# Updated prompt with strict formatting instructions
prompt_template = (
    "Categorize the sentiment of the following text as exactly one word: 'Positive', 'Negative', or 'Neutral'. "
    "Do not provide any explanation or extra text. Only return the word.\n\nText: "
)

df['Sentiment'] = df['Raw_Feedback'].apply(
    lambda x: call_local_gemma(f"{prompt_template}{x}").strip()
)

print(df[['Raw_Feedback','Sentiment']].head(10))