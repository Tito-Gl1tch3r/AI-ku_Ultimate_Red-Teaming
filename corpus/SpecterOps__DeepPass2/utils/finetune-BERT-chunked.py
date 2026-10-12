import numpy as np
import torch
import random
import os
from datasets import load_from_disk
from peft import get_peft_model, LoraConfig, TaskType
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import set_seed as transformers_set_seed
from transformers import AutoModelForTokenClassification, AutoTokenizer, Trainer, TrainingArguments
from utils.trainingEvaluator import evaluate_during_training

## Set the model name you want for your new model
new_model_name = "version6.0-BERT"

def set_seed(seed=3):
    """
    Set seed for all random number generators to ensure reproducibility.
    
    Args:
        seed (int): The seed value to use
    """
    # Python's built-in random
    random.seed(seed)
    
    # Numpy
    np.random.seed(seed)
    
    # PyTorch
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)  # For multi-GPU
    
    # MPS (Metal Performance Shaders) for Mac
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)
    
    ## Uncomment if you want to set seed for CUDA
    # torch.backends.cudnn.deterministic = True
    # torch.backends.cudnn.benchmark = False
    
    # Environment variable for some operations
    os.environ['PYTHONHASHSEED'] = str(seed)
    
    # Transformers library seed setting
    transformers_set_seed(seed)
    
    print(f"Random seed set to {seed}")


def fine_tune_bert_for_token_retrieval(model_name="xlm-roberta-base", dataset_name="Dataset/chunked_training_BERT_realpass", epochs=4, batch_size=8):
    # Load dataset
    dataset = load_from_disk(dataset_name)
    dataset = dataset.train_test_split(test_size=0.1)  # 90% train, 10% validation


    # Load tokenizer and model for token classification
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name, num_labels=2)  # Binary labels: Token vs. Non-Token
    model.to("mps")

    # Apply LoRA adapters
    lora_config = LoraConfig(
        task_type=TaskType.TOKEN_CLS,  
        r=64,
        lora_alpha=128,
        lora_dropout=0.05,
        bias="none",
        target_modules=["query", "key", "value", "dense"]
    )
    model = get_peft_model(model, lora_config)

    # Tokenize dataset for token classification
    def preprocess(examples):
        """Extracts tokens from text and applies tokenization."""

        doc = examples['document']

        tokenized = tokenizer(doc, padding="max_length", truncation=True, return_offsets_mapping=True)

        # Generate labels (1 for credentials, 0 otherwise)
        labels = [0] * len(tokenized["input_ids"])

        credentials = examples["cred"]
        if credentials != []:
            for credential in credentials:
                start_idx = doc.find(credential)
                
                end_idx = start_idx + len(credential)

                # Label tokens within credential span
                for i, (tok_start, tok_end) in enumerate(tokenized["offset_mapping"]):
                    if tok_start >= start_idx and tok_end <= end_idx:
                        labels[i] = 1  # Mark as credential token

        tokenized["labels"] = labels
        return tokenized

    
    # Apply preprocessing to dataset
    dataset['train'].to_json("./Dataset/test/train_plain.json")
    dataset['test'].to_json("./Dataset/test/test_plain.json")
    tokenized_datasets_train = dataset["train"].map(preprocess, batched=False, remove_columns=["document", "cred"])
    tokenized_datasets_test = dataset["test"].map(preprocess, batched=False, remove_columns=["document", "cred"])
    

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)

        # Flatten lists (since token classification outputs are nested)
        true_labels = [label for batch in labels for label in batch]
        pred_labels = [pred for batch in predictions for pred in batch]

        accuracy = accuracy_score(true_labels, pred_labels)
        precision, recall, f1, _ = precision_recall_fscore_support(true_labels, pred_labels, average="binary")

        return {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


    # Define training arguments
    training_args = TrainingArguments(
        output_dir=f"./Model/{new_model_name}",
        # save_strategy="epoch",
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=epochs,
        weight_decay=0.01,
        logging_dir="./logs",
        logging_steps=10,
        push_to_hub=False,
    )

    # Define Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets_train,
        eval_dataset= tokenized_datasets_test,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    # # Train model
    trainer.train()

    # # Save adapter
    model.save_pretrained(f"./Model/{new_model_name}")
    tokenizer.save_pretrained(f"./Model/{new_model_name}")

    # try to save a merged model
    try:
        model = model.merge_and_unload()
        model.save_pretrained(f"./Model/{new_model_name}/merged-model")
        tokenizer.save_pretrained(f"./Model/{new_model_name}/merged-model")
    except Exception as e:
        print("Couldn't save as merged model")
    
    try:
        metrics = evaluate_during_training(
            model=model,
            tokenizer=tokenizer,
            test_data=tokenized_datasets_test,  
            device="cpu",  # or whatever device you're using
        )
        print(metrics)
    except Exception as e:
        print(f'The following error occured: {e}')

if __name__ == "__main__":
    set_seed(2)
    fine_tune_bert_for_token_retrieval()