"""Local LLM wrapper for consistent interface"""
import logging

import torch


class LLMWrapper:
    """Wrapper for local LLM model with consistent interface"""

    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.device = model.device
        self.logger = logging.getLogger(__name__)

    def generate(self,
                 prompt: str,
                 wrap_prompt: bool = True,
                 max_new_tokens: int = 512,
                 temperature: float = 0.7,
                 top_p: float = 0.9,
                 top_k: int = 50) -> str:
        """Generate text from prompt"""

        if wrap_prompt:
            prompt = f"<|start|>user<|message|>{prompt}<|end|>"

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=True,
                )

            output_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=False)
            return output_text

        except Exception as e:
            self.logger.error(f"Error generating text: {e}")
            raise
