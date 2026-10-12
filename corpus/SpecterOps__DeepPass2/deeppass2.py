import os
import re
import ssl
import time
import httpx
import torch
import openai
import structlog
import numpy as np

from dotenv import load_dotenv
# from huggingface_hub import login
from utils.nprules import AsyncRegexChecker
from utils.BERTprocessor import classify_tokens
from flask import Flask, request, jsonify
from transformers import AutoModelForTokenClassification, AutoTokenizer

load_dotenv()

# Configure SSL context for httpx
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Create a transport with the custom SSL context
transport = httpx.HTTPTransport(verify=False)


logger = structlog.get_logger(module=__name__)

############################################## Loading BERT Model ##############################################

print('Loading fine-tuned xlm roberta model')
# base_model_name = "xlm-roberta-base"
model_name = "path/to/merged-model"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

if torch.cuda.is_available():
    device = "cuda"
    print("Using CUDA GPU")
elif torch.backends.mps.is_available():
    device = "mps"
    print("Using Apple Silicon GPU (MPS)")
else:
    device = "cpu"
    print("Using CPU")

model.to(device)
model.eval()  # Set to evaluation mode
print('Model loading complete.')
############################################## BERT Model Loaded ##############################################


app = Flask(__name__)


## Using LiteLLM here, but you can use any other LLM router, or use the LLMs directly (with additional code changes in the following script)
litellm_client = openai.OpenAI(
    api_key=os.environ["LITELLM_API_KEY"],
    base_url=os.environ["LITELLM_BASE_URL"],
    http_client=httpx.Client(transport=transport),
)

def chunk_document(text, tokenizer, max_len=512, min_len=300, overlap_ratio=0.1):
    """Chunk the large document between max and min context length of BERT-based model"""
    
    tokenized = tokenizer(text, return_offsets_mapping=True, add_special_tokens=False)
    input_ids = tokenized["input_ids"]
    offsets = tokenized["offset_mapping"]
    
    total_tokens = len(input_ids)
    overlap = int(max_len * overlap_ratio)  # 10% overlap
    chunks = []
    start = 0
    
    while start <= total_tokens:
        # Determine chunk length randomly (between min_len and max_len) - That's what our model is trained on
        chunk_len = np.random.randint(min_len, max_len+1)
    
        chunk_end = min(start+chunk_len, total_tokens)
        chunk_text = text[offsets[start][0]:offsets[chunk_end-1][1]]  
        chunks.append(chunk_text)

        if chunk_end == total_tokens:
            break
        if chunk_end - overlap>0:
            start = chunk_end - overlap
        else:
            break

    return chunks


async def get_nosey_parker_results(doc):
    """Match and remove NoseyParker results"""
    checker = AsyncRegexChecker("./regexRules.jsonl")

    try:
        np_secret = await checker.check_document(doc)

        doc_cleaned = remove_np_result(doc, np_secret)
    except Exception as e:
        print(e)


    return np_secret, doc_cleaned
    

def remove_np_result(doc, matches, replacement=""):
    """Removes all noseyparker regex matched patterns from the document."""
    
    for match in matches:
        for matc in match:
            pattern = re.escape(matc["match"])  
            doc = re.sub(pattern, replacement, doc)  
    return doc

def get_prompt(text, passwords):
    """Prompt for the LLM"""
    prompt = f"""Identify if the given password or api key below is actually a password or api key in the given text or is it a false positive. 
    If you find the password or api key, please return it between <credential></credential> tag. If there are more than one credentials, 
    include them in additional <credential></credential> tag.
    Password: {str(passwords)}
    Text: {text}
    """
    return prompt

def get_secrets_LLM(bert_output):
    """Run LLM check and confirmation on the retrieved xlm-RoBERTa-base model"""
    secrets_list = []
    litellm_model = os.environ["AUGMENT_MODEL"]

    start = time.time()

    for secrets in bert_output:
        passw = secrets["secret"]
        text = secrets["chunk"]
        prompt = get_prompt(text, passw)

        ## Change the code here to accomodate non-litellm infra
        response = litellm_client.chat.completions.create(
            model=litellm_model,
            messages = [
                {
                "role": "system",
                "content": "You are a helpful assistant. Your expertise is to identify the presence of APIs, database links, or leaked passwords. Do not explain."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )
        execution_time = (time.time()-start)
        message = response.choices[0].message.content

        credential_pattern = r"<credential>(.*?)</credential>"
        credential_matches = list(re.finditer(credential_pattern, message))

        
        credentials = [match.group(1) for match in credential_matches]

        secrets_list.append({'Extracted_Credentials':credentials, 'LLM_response':message,'chunk':text, 'generation_time': execution_time})

    return secrets_list


def get_secrets_BERT(chunks, model=model, tokenizer=tokenizer):
    """Scan for secrets using finetuned xlm-RoBERTa-base model"""
    bert_secret = []

    
    for chunk in chunks:
        temp_secrets = classify_tokens(chunk, model, tokenizer, device=device)
        if temp_secrets != [] and temp_secrets:
            bert_secret.append({"secret":temp_secrets, 'chunk':chunk})
    

    return bert_secret

async def scan_secret(doc):
    """Main function to scan the document for secrets"""
    secrets = []
    try:
        np_secret, doc_np_cleaned = await get_nosey_parker_results(doc)
        secrets.append({'Nosey Parker': np_secret})
    except Exception as e:
        print(f"Nosey Parker error: {e}")
        doc_np_cleaned = doc  # Use original doc if Nosey Parker fails
        secrets.append({'Nosey Parker': 'Failed'})

    try:
        chunks = chunk_document(doc_np_cleaned, tokenizer)
    except Exception as e:
        print(f"Chunking error: {e}")
        chunks = None

    if chunks:  # Only proceed if chunking succeeded
        try:
            bert_secret = get_secrets_BERT(chunks)
            secrets.append({'BERT_secrets': bert_secret})
        except Exception as e:
            print(f"BERT error: {e}")
            bert_secret = None
            secrets.append({'BERT_secrets': 'Failed'})
        
        if bert_secret:  # Only run LLM if BERT succeeded
            try:
                LLM_secret = get_secrets_LLM(bert_secret)
                secrets.append({'LLM_scanning': LLM_secret})
            except Exception as e:
                print(f"LLM scanning error: {e}")
                secrets.append({'LLM_scanning': 'Failed'})
        

    return secrets


@app.route('/api/deeppass2', methods=['POST'])
async def deeppass_scanning():
    """DeepPass2 API call"""
    doc = request.data.decode('utf-8')
    try:
        secrets = await scan_secret(doc)
        return jsonify({'Success':secrets})
    except Exception as e:
        return jsonify({'error':f'Document counld not be scanned. Error {e}.'})


    

if __name__ == "__main__":
    app.run(port=5000, debug =True)

    