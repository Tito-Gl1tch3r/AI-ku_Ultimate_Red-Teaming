import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import torch
from tqdm import tqdm
from sklearn.metrics import (
    accuracy_score, 
    precision_recall_fscore_support, 
    classification_report,
    confusion_matrix
)
from datasets import Dataset
import pandas as pd
from pathlib import Path


class ModelEvaluator:
    """
    Comprehensive evaluator for token classification models.
    Can be called directly from training loop with model and tokenizer objects.
    """
    
    def __init__(self, save_dir="./evaluation_results"):
        """
        Initialize the evaluator.
        
        Args:
            save_dir (str): Directory to save evaluation results and plots
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
    def evaluate_model(self, model, tokenizer, test_data, device="cpu", batch_size=8, 
                      save_results=True, plot_confusion_matrix=True, analyze_errors=True):
        """
        Comprehensive evaluation of the model.
        
        Args:
            model: The trained model (already loaded)
            tokenizer: The tokenizer (already loaded)
            test_data: Test dataset (can be Dataset object or path to JSON)
            device: Device to run evaluation on
            batch_size: Batch size for evaluation
            save_results: Whether to save results to file
            plot_confusion_matrix: Whether to plot confusion matrix
            analyze_errors: Whether to perform error analysis
            
        Returns:
            dict: Comprehensive evaluation results
        """
        # Load test data if path is provided
        if isinstance(test_data, str):
            test_dataset = Dataset.from_json(test_data)
        else:
            test_dataset = test_data
            
        print(f"Evaluating on {len(test_dataset)} test examples...")
        
        # Get predictions
        all_predictions, all_labels = self._get_predictions(
            model, tokenizer, test_dataset, device, batch_size
        )
        
        # Compute metrics
        metrics = self._compute_comprehensive_metrics(all_predictions, all_labels)
        
        # Create confusion matrix
        cm = self._create_confusion_matrix(all_predictions, all_labels)
        metrics['confusion_matrix'] = cm
        
        # Plot confusion matrix if requested
        if plot_confusion_matrix:
            self._plot_confusion_matrix(cm, metrics)
        
        # Analyze errors if requested
        if analyze_errors:
            error_analysis = self._analyze_errors(
                model, tokenizer, test_dataset, device, num_examples=10
            )
            metrics['error_analysis'] = error_analysis
        
        # Save results if requested
        if save_results:
            self._save_results(metrics)
        
        # Print summary
        self._print_summary(metrics)
        
        return metrics
    
    def _get_predictions(self, model, tokenizer, test_dataset, device, batch_size):
        """Get model predictions on the test dataset."""
        model.eval()
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for i in tqdm(range(0, len(test_dataset), batch_size), desc="Getting predictions"):
                batch_indices = list(range(i, min(i + batch_size, len(test_dataset))))
                batch = test_dataset.select(batch_indices)
                
                # Prepare inputs
                inputs = {
                    "input_ids": torch.tensor([batch[j]["input_ids"] for j in range(len(batch))]).to(device),
                    "attention_mask": torch.tensor([batch[j]["attention_mask"] for j in range(len(batch))]).to(device)
                }
                
                # Get predictions
                outputs = model(**inputs)
                predictions = torch.argmax(outputs.logits, dim=-1)
                
                # Collect predictions and labels
                all_predictions.extend(predictions.detach().cpu().numpy().tolist())
                all_labels.extend([batch[j]["labels"] for j in range(len(batch))])
        
        return all_predictions, all_labels
    
    def _compute_comprehensive_metrics(self, predictions, labels):
        """Compute comprehensive metrics for token classification."""
        # Flatten predictions and labels
        flat_predictions = []
        flat_labels = []
        
        for pred, label in zip(predictions, labels):
            # Filter out padding tokens
            mask = np.array(label) != -100
            flat_predictions.extend(np.array(pred)[mask])
            flat_labels.extend(np.array(label)[mask])
        
        # Basic metrics
        accuracy = accuracy_score(flat_labels, flat_predictions)
        precision, recall, f1, support = precision_recall_fscore_support(
            flat_labels, flat_predictions, average="binary"
        )
        
        # Per-class metrics
        report = classification_report(
            flat_labels, flat_predictions, 
            labels=[0, 1], 
            target_names=["Non-Token", "Token"],
            output_dict=True
        )
        
        # Token statistics
        total_tokens = len(flat_labels)
        credential_tokens = sum(1 for label in flat_labels if label == 1)
        non_credential_tokens = total_tokens - credential_tokens
        
        # Additional metrics
        tn, fp, fn, tp = confusion_matrix(flat_labels, flat_predictions).ravel()
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        balanced_accuracy = (recall + specificity) / 2
        
        # Matthews Correlation Coefficient
        # mcc_num = (tp * tn) - (fp * fn)
        # mcc_den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        # mcc = mcc_num / mcc_den if mcc_den > 0 else 0
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "specificity": specificity,
            "balanced_accuracy": balanced_accuracy,
            # "mcc": mcc,
            "detailed_report": report,
            "token_stats": {
                "total": total_tokens,
                "credential": credential_tokens,
                "non_credential": non_credential_tokens,
                "credential_percentage": credential_tokens / total_tokens * 100
            },
            "confusion_matrix_values": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp)
            }
        }
    
    def _create_confusion_matrix(self, predictions, labels):
        """Create confusion matrix from predictions and labels."""
        flat_predictions = []
        flat_labels = []
        
        for pred, label in zip(predictions, labels):
            mask = np.array(label) != -100
            flat_predictions.extend(np.array(pred)[mask])
            flat_labels.extend(np.array(label)[mask])
        
        return confusion_matrix(flat_labels, flat_predictions)
    
    def _plot_confusion_matrix(self, cm, metrics):
        """Create and save confusion matrix visualization."""
        plt.figure(figsize=(10, 8))
        
        # Create the heatmap
        sns.heatmap(cm, annot=False, fmt='d', cmap='Blues', square=True,
                    xticklabels=['Non-passwords', 'Passwords'], 
                    yticklabels=['Non-passwords', 'Passwords'],
                    cbar_kws={'label': 'Count'})
        
        # Add custom annotations with counts and percentages
        total = cm.sum()
        for i in range(2):
            for j in range(2):
                count = cm[i, j]
                percentage = 100 * count / total
                
                # Add text with count and percentage
                plt.text(j + 0.5, i + 0.5, f'{count:,}\n({percentage:.2f}%)',
                        ha='center', va='center', fontsize=12,
                        color='white' if count > cm.max() / 2 else 'black')
        
        plt.ylabel('True Label', fontsize=14)
        plt.xlabel('Predicted Label', fontsize=14)
        plt.title('Confusion Matrix for Token Classification', fontsize=16, pad=20)
        
        # Add metrics as text
        plt.figtext(0.15, 0.02, f'F1 Score: {metrics["f1"]:.4f} | Precision: {metrics["precision"]:.4f} | Recall: {metrics["recall"]:.4f}', 
                   fontsize=10)
        
        plt.tight_layout()
        
        # Save the plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = self.save_dir / f'confusion_matrix_{timestamp}.png'
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Confusion matrix saved to: {save_path}")
    
    def _analyze_errors(self, model, tokenizer, test_dataset, device, num_examples=10):
        """Analyze prediction errors."""
        model.eval()
        false_positives = []
        false_negatives = []
        
        # Analyze first 100 examples for errors
        with torch.no_grad():
            for i in range(min(100, len(test_dataset))):
                example = test_dataset[i]
                
                inputs = {
                    "input_ids": torch.tensor([example["input_ids"]]).to(device),
                    "attention_mask": torch.tensor([example["attention_mask"]]).to(device)
                }
                
                outputs = model(**inputs)
                predictions = torch.argmax(outputs.logits, dim=-1)[0].detach().cpu().numpy()
                labels = example["labels"]
                
                # Decode tokens
                tokens = tokenizer.convert_ids_to_tokens(example["input_ids"])
                
                # Find errors
                for j, (pred, label, token) in enumerate(zip(predictions, labels, tokens)):
                    if pred == 1 and label == 0:  # False positive
                        false_positives.append({
                            'token': token,
                            'position': j,
                            'example_id': i
                        })
                    elif pred == 0 and label == 1:  # False negative
                        false_negatives.append({
                            'token': token,
                            'position': j,
                            'example_id': i
                        })
        
        return {
            'false_positives': false_positives[:num_examples],
            'false_negatives': false_negatives[:num_examples],
            'total_false_positives': len(false_positives),
            'total_false_negatives': len(false_negatives)
        }
    
    def _save_results(self, metrics):
        """Save evaluation results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed metrics as JSON
        results_file = self.save_dir / f'evaluation_results_{timestamp}.json'
        
        # Convert numpy types to Python types for JSON serialization
        save_metrics = {
            'timestamp': timestamp,
            'accuracy': float(metrics['accuracy']),
            'precision': float(metrics['precision']),
            'recall': float(metrics['recall']),
            'f1': float(metrics['f1']),
            'specificity': float(metrics['specificity']),
            'balanced_accuracy': float(metrics['balanced_accuracy']),
            # 'mcc': float(metrics['mcc']),
            'token_stats': metrics['token_stats'],
            'confusion_matrix_values': metrics['confusion_matrix_values'],
            'detailed_report': metrics['detailed_report']
        }
        
        if 'error_analysis' in metrics:
            save_metrics['error_analysis'] = {
                'total_false_positives': metrics['error_analysis']['total_false_positives'],
                'total_false_negatives': metrics['error_analysis']['total_false_negatives'],
                'false_positive_examples': [fp['token'] for fp in metrics['error_analysis']['false_positives']],
                'false_negative_examples': [fn['token'] for fn in metrics['error_analysis']['false_negatives']]
            }
        
        with open(results_file, 'w') as f:
            json.dump(save_metrics, f, indent=2)
        
        print(f"Results saved to: {results_file}")
    
    def _print_summary(self, metrics):
        """Print evaluation summary."""
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)
        
        print(f"\nOverall Metrics:")
        print(f"  Accuracy:          {metrics['accuracy']:.4f}")
        print(f"  Precision:         {metrics['precision']:.4f}")
        print(f"  Recall:            {metrics['recall']:.4f}")
        print(f"  F1 Score:          {metrics['f1']:.4f}")
        print(f"  Specificity:       {metrics['specificity']:.4f}")
        print(f"  Balanced Accuracy: {metrics['balanced_accuracy']:.4f}")
        # print(f"  MCC:               {metrics['mcc']:.4f}")
        
        print(f"\nToken Statistics:")
        stats = metrics['token_stats']
        print(f"  Total tokens:        {stats['total']:,}")
        print(f"  Credential tokens:   {stats['credential']:,} ({stats['credential_percentage']:.2f}%)")
        print(f"  Non-credential:      {stats['non_credential']:,} ({100-stats['credential_percentage']:.2f}%)")
        
        if 'error_analysis' in metrics:
            print(f"\nError Analysis:")
            print(f"  False Positives: {metrics['error_analysis']['total_false_positives']}")
            print(f"  False Negatives: {metrics['error_analysis']['total_false_negatives']}")
        
        print("="*60)


# Convenience function to use in training loop
def evaluate_during_training(model, tokenizer, test_data, device="cpu", 
                           save_dir="./evaluation_results", epoch=None):
    """
    Convenience function to call from training loop.
    
    Args:
        model: The model being trained
        tokenizer: The tokenizer
        test_data: Test dataset or path to test data
        device: Device to run evaluation on
        save_dir: Directory to save results
        epoch: Current epoch number (optional, for naming)
    
    Returns:
        dict: Evaluation metrics
    """
    # Create evaluator
    if epoch is not None:
        save_dir = f"{save_dir}/epoch_{epoch}"
    
    evaluator = ModelEvaluator(save_dir=save_dir)
    
    # Run evaluation
    metrics = evaluator.evaluate_model(
        model=model,
        tokenizer=tokenizer,
        test_data=test_data,
        device=device,
        batch_size=8,
        save_results=True,
        plot_confusion_matrix=True,
        analyze_errors=True
    )
    
    return metrics


# Example usage in training script
if __name__ == "__main__":
    # This shows how to use it standalone
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    
    # Load model and tokenizer
    model_path = "./Model/version6.0-BERT/merged-model"
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    # Create evaluator
    evaluator = ModelEvaluator(save_dir="./evaluation_results")
    
    # Run evaluation
    metrics = evaluator.evaluate_model(
        model=model,
        tokenizer=tokenizer,
        test_data="./Dataset/test/test.json",
        device="cpu"
    )