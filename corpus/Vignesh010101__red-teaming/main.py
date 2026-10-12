"""Main script to run the red-teaming agent."""

import asyncio
from loguru import logger
import sys
from red_teaming.config import Config
from red_teaming.agents import RedTeamingAgent
from red_teaming.utils import setup_logging
from dotenv import load_dotenv

load_dotenv()


async def main():
    """Main function to run the red-teaming agent."""

    # Setup logging
    setup_logging("INFO")

    logger.info("Starting Red-Teaming Agent for GPT-OSS-20B")

    try:
        # Load configuration
        config = Config.from_env()

        # Display configuration
        print("\n" + "=" * 60)
        print("RED-TEAMING AGENT CONFIGURATION")
        print("=" * 60)
        print(f"Target Model: {config.ollama.target_model}")
        print(f"Red-Team Model: {config.ollama.red_teaming_model}")
        print(f"Ollama URL: {config.ollama.base_url}")
        print(f"Max Issues to Find: {config.red_teaming.max_issues_to_find}")
        print(f"Max Conversation Turns: {config.red_teaming.max_conversation_turns}")
        print(f"Output Directory: {config.output.output_dir}")
        print("=" * 60 + "\n")

        # Create and run the agent
        agent = RedTeamingAgent(config)

        print("🚀 Starting red-teaming workflow...")
        print("This may take several minutes to complete.\n")

        result = await agent.run()

        # Display results
        print("\n" + "=" * 60)
        print("RED-TEAMING RESULTS")
        print("=" * 60)

        if result["success"]:
            print("✅ Red-teaming completed successfully!")
            print(f"📊 Vulnerabilities found: {result['vulnerabilities_found']}")
            print(f"💬 Total conversations: {result['total_conversations']}")

            if result["vulnerabilities"]:
                print("\n🔍 Discovered Vulnerabilities:")
                for i, vuln in enumerate(result["vulnerabilities"], 1):
                    print(f"\n{i}. {vuln['title']}")
                    print(f"   Type: {vuln['type']}")
                    print(f"   Severity: {vuln['severity'].upper()}")
                    print(f"   Description: {vuln['description'][:150]}...")

            print(f"\n📁 Results saved to: {config.output.output_dir}")

        else:
            print(f"❌ Red-teaming failed: {result.get('error', 'Unknown error')}")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Red-teaming interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error running red-teaming agent: {e}")
        print(f"❌ Error: {e}")
        return 1

    print("\n" + "=" * 60)
    print("Red-teaming workflow completed!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
