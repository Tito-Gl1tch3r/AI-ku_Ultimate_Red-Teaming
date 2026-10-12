import torch


# model = PeftModel.from_pretrained(base_model, adapter_path)

def classify_tokens(document, model, tokenizer, device="cuda"):
    """Tokenizes the input document and predicts credential tokens."""
    
    # Tokenize the document
    tokenized = tokenizer(document, padding="max_length", truncation=True, return_offsets_mapping=True, return_tensors="pt")
    
    # Move input tensors to the correct device
    input_ids = tokenized["input_ids"].to(device)
    attention_mask = tokenized["attention_mask"].to(device)
    offsets = tokenized["offset_mapping"].tolist()[0]  # Get token offsets

    # Run inference
    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_mask)
    
    # Get predicted labels (0 or 1)
    predictions = torch.argmax(outputs.logits, dim=-1).cpu().numpy()[0]  # Get labels for first (only) batch
    
    # Extract credential spans using offsets
    credential_tokens = []
    current_credential = ""
    previous_end = -1  # Track last token's end position

    for i, label in enumerate(predictions):
        if label == 1:  # Credential token
            start, end = offsets[i]
            if start == 0 and end == 0:  # Skip special tokens
                continue

            token_text = document[start:end]

            if previous_end != -1 and start > previous_end + 1:
                # New credential detected, store previous and start a new one
                credential_tokens.append(current_credential)
                current_credential = token_text
            else:
                # Append to existing credential
                current_credential += token_text

            previous_end = end  # Update last token end position

    if current_credential:
        credential_tokens.append(current_credential)  

    return credential_tokens
