"""Main prompt processing pipeline"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from models.llm import LLMWrapper
from processors.text_replacer import TextReplacer


@dataclass
class ProcessingResult:
    """Data class for processing results"""
    prompt: str
    harmful_cot_output: Optional[str] = None
    score: Optional[float] = None
    refused: Optional[bool] = None
    error: Optional[str] = None


class PromptProcessor:
    """Main processor for prompt & CoT transformation pipeline"""

    def __init__(self,
                 llm_model,
                 tokenizer,
                 judge,
                 api_client,
                 config: Dict[str, Any]):
        self.llm = LLMWrapper(llm_model, tokenizer)
        self.judge = judge
        self.api_client = api_client
        self.config = config
        self.text_replacer = TextReplacer()
        self.logger = logging.getLogger(__name__)
        self.templates = config.get('templates')

    def process_prompt(self, prompt: str) -> ProcessingResult:
        """Process a single prompt through the pipeline"""

        max_retries = self.config.get('llm_retry_count', 3)
        max_judge_retries = self.config.get('max_judger_retries', 10)

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Processing prompt (attempt {attempt + 1}/{max_retries})")

                # Step 1: Generate harmful CoT
                self.logger.debug("Generating harmful CoT...")
                harmful_cot = self.llm.generate(prompt, wrap_prompt=True)

                # Step 2: Get safe replacements
                self.logger.debug("Getting safe replacements...")
                replacements = self.api_client.get_safe_equivalents(
                    prompt, harmful_cot, self.templates.PAIR_FINDING_TEMPLATE
                )
                if not replacements:
                    self.logger.warning("Failed to get safe replacements")
                    continue

                # Step 3: Create safe prompt
                safe_prompt = self.text_replacer.apply_replacements(prompt, replacements)
                self.logger.debug(f"Safe prompt created: {safe_prompt[:100]}...")

                # Step 4: Generate and truncate safe CoT
                safe_cot = self.llm.generate(safe_prompt, wrap_prompt=True)
                truncated_safe_cot = self.api_client.truncate_cot(
                    safe_cot, self.templates.TRUNCATE_TEMPLATE
                )

                # Step 5: Get CoT-specific replacements
                cot_replacements = self.api_client.get_cot_safe_equivalents(
                    prompt, safe_prompt, truncated_safe_cot,
                    self.templates.COT_PAIR_FINDING_TEMPLATE
                )

                # Step 6: Transform back to harmful context
                all_replacements = self.text_replacer.merge_replacements(
                    replacements, cot_replacements
                )
                final_cot = self.text_replacer.apply_replacements(
                    truncated_safe_cot, all_replacements, reverse=True
                )

                # Step 7: Generate output with judge retry logic
                for judge_attempt in range(max_judge_retries):
                    output = self.llm.generate(final_cot, wrap_prompt=False, max_new_tokens=2048)
                    score = self.judge.evaluate(prompt, output)
                    refused = (score == 0) if score is not None else None

                    if not refused or judge_attempt == max_judge_retries - 1:
                        return ProcessingResult(
                            prompt=prompt,
                            harmful_cot_output=output,
                            score=score,
                            refused=refused
                        )

                    self.logger.info(f"Judge refused output, retrying ({judge_attempt + 1}/{max_judge_retries})")

            except Exception as e:
                self.logger.error(f"Error in attempt {attempt + 1}: {e}", exc_info=True)
                if attempt == max_retries - 1:
                    return ProcessingResult(
                        prompt=prompt,
                        error=str(e)
                    )

        return ProcessingResult(prompt=prompt, error="Max retries exceeded")
