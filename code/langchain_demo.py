from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 2000)  

#LLM
MODEL_NAME = 'gemma:2b'
llm = Ollama(model=MODEL_NAME, keep_alive=0)


# Prompt template
prompt = PromptTemplate(
    input_variables=["text"],
    template="Categorize the sentiment of the following text as exactly one word: 'Positive', 'Negative', or 'Neutral' , \
    Do not provide any explanation or extra text. Only return the word.\n\nText: :\n {text}"
)

#Chain
chain = LLMChain(llm=llm, prompt=prompt)

# Data
df = pd.read_excel('../data/cust_data.xlsx',engine='openpyxl')

# Apply
df['Sentiment'] = df['Raw_Feedback'].apply(lambda x: chain.run(text=x))
print(df[['Raw_Feedback','Sentiment']].head(10))