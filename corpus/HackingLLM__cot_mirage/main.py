"""Main entry point for CoT Mirage Hacking pipeline"""
import argparse
import csv
import logging
from datetime import datetime

from transformers import AutoTokenizer, AutoModelForCausalLM

from api.claude_client import ClaudeAPIClient
from config import config
from models.judge import StrongRejectJudge
from processors.prompt_processor import PromptProcessor
from utils.csv_handler import ResultsCSVWriter
from utils.logging_config import setup_logging
from utils.prompt_templates import PromptTemplates


# read text file line by line
def load_prompts_from_csv(csv_file: str) -> list:
    """Load prompts from CSV file"""
    prompts = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'prompt' in row and row['prompt'].strip():
                    prompts.append(row['prompt'].strip())
        logging.info(f"Loaded {len(prompts)} prompts from {csv_file}")
    except FileNotFoundError:
        logging.error(f"CSV file not found: {csv_file}")
        raise
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_file}: {e}")
        raise
    return prompts


def multiline_input() -> str:
    """Read multiline input from stdin"""
    lines = []
    print("Enter your prompt (press Enter twice to finish, or Ctrl+D/Ctrl+Z to end):")
    try:
        while True:
            line = input()
            if line == "":
                if lines and lines[-1] == "":
                    lines.pop()
                    break
                else:
                    lines.append(line)
            else:
                lines.append(line)
    except EOFError:
        pass
    return '\n'.join(lines)


def run_interactive_mode(processor: PromptProcessor, csv_writer: ResultsCSVWriter):
    """Run the processor in interactive mode"""
    print("CoT Mirage Interactive Mode with Judge Evaluation")
    print("=" * 50)
    print("Type 'exit' or 'quit' to end the session")

    while True:
        try:
            prompt = multiline_input().strip()
            if not prompt:
                continue
            if prompt.lower() in {"exit", "quit"}:
                print("Exiting.")
                break

            # Ask how many times to process
            while True:
                num_runs_str = input("How many times to process this prompt? (default: 1): ").strip()
                if not num_runs_str:
                    num_runs = 1
                    break
                elif num_runs_str.isdigit() and int(num_runs_str) > 0:
                    num_runs = int(num_runs_str)
                    break
                else:
                    print("Please enter a positive integer.")

            # Process the prompt multiple times if requested
            for i in range(num_runs):
                if num_runs > 1:
                    print(f"\n{'=' * 20} Run {i + 1}/{num_runs} {'=' * 20}")

                print("#" * 80)
                print(f"\n\n=== Processing prompt ===\n{prompt}\n")

                result = processor.process_prompt(prompt)
                csv_writer.write_result(result)

                print(f"\n######## Result ########")
                print(f"Score: {result.score}")
                print(f"Refused: {result.refused}")
                if result.error:
                    print(f"Error: {result.error}")
                print(f"\nResult saved to {csv_writer.filename}")

        except KeyboardInterrupt:
            print("\nInterrupted. Exiting.")
            break


def run_batch_mode(processor: PromptProcessor, csv_writer: ResultsCSVWriter,
                   prompts: list):
    """Process a batch of prompts"""
    total = len(prompts)
    all_results = []

    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'=' * 60}")
        print(f"Processing prompt {i}/{total}")
        print('=' * 60)

        try:
            result = processor.process_prompt(prompt)
            csv_writer.write_result(result)
            all_results.append(result)

            if result.error:
                print(f"ERROR: {result.error}")
            else:
                print(f"Score: {result.score}, Refused: {result.refused}")

        except Exception as e:
            logging.error(f"Critical error processing prompt {i}: {e}")
            print(f"CRITICAL ERROR: Skipping prompt {i} due to: {e}")
            continue

    # Print summary
    stats = csv_writer.get_summary_stats()
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    print(f"Total prompts processed: {stats['total']}")
    print(f"Successful evaluations: {stats['successful']}")
    print(f"Failed evaluations: {stats['failed']}")
    print(f"Prompts refused: {stats['refused']}/{stats['successful']}")
    print(f"Average score: {stats['avg_score']:.4f}")
    print(f"\nResults saved to: {csv_writer.filename}")


def main():
    parser = argparse.ArgumentParser(description="CoT Mirage Pipeline")
    parser.add_argument("--device", default="cuda", help="Device for local LLM (cuda, cpu, or mps)")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--input-csv", help="Input CSV file with prompts")
    parser.add_argument("--output-csv", help="Output CSV file for results")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--log-file", help="Log file path")
    parser.add_argument("--llm-retry-count", type=int, help="Override LLM retry count")
    parser.add_argument("--api-retry-count", type=int, help="Override API retry count")
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_file, args.log_level)
    logger = logging.getLogger(__name__)

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Override config if command line args provided
    if args.llm_retry_count:
        config.LLM_RETRY_COUNT = args.llm_retry_count
    if args.api_retry_count:
        config.API_RETRY_COUNT = args.api_retry_count

    logger.info(f"Using device: {args.device}")
    logger.info(f"LLM retry count: {config.LLM_RETRY_COUNT}")
    logger.info(f"API retry count: {config.API_RETRY_COUNT}")

    # Initialize components
    logger.info("Loading model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        config.MODEL_ID,
        device_map={"": args.device} if args.device != "cpu" else None,
    )

    # Initialize API client
    claude_api_client = ClaudeAPIClient(
        api_key=config.CLAUDE_API_KEY,
        api_url=config.CLAUDE_API_URL,
        max_retries=config.API_RETRY_COUNT
    )

    # Initialize judge
    judge = StrongRejectJudge()

    # Initialize processor
    processor = PromptProcessor(
        llm_model=model,
        tokenizer=tokenizer,
        judge=judge,
        api_client=claude_api_client,
        config={
            "llm_retry_count": config.LLM_RETRY_COUNT,
            "api_interval": config.API_INTERVAL,
            "max_judger_retries": config.MAX_JUDGER_RETRIES,
            "templates": PromptTemplates()
        }
    )

    # Initialize CSV writer
    output_file = args.output_csv or f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_writer = ResultsCSVWriter(output_file)
    logger.info(f"Results will be saved to: {csv_writer.filename}")

    # Run appropriate mode
    if args.interactive:
        run_interactive_mode(processor, csv_writer)
    elif args.input_csv:
        prompts = load_prompts_from_csv(args.input_csv)
        run_batch_mode(processor, csv_writer, prompts)
    else:
        # Default: try to load from harmful_prompts module
        try:
            from harmful_prompts import harmful_jo
            logger.info(f"Loading {len(harmful_jo)} prompts from harmful_prompts module")
            run_batch_mode(processor, csv_writer, harmful_jo)
        except ImportError:
            logger.error("No input specified and harmful_prompts module not found")
            print("Please specify --interactive or --input-csv")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
