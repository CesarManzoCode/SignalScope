import asyncio

from config.user_config import load_user_config

from infrastructure.sources.registry import get_all_sources
from modules.llm.llm_selector import get_llm_client

from modules.source_selector.source_selector import select_sources
from modules.research.research import run_research
from modules.filter.filter import filter_items
from modules.llm.llm import process_items


async def main():
    # 1. Load user config
    config = load_user_config()

    # 2. Get all available sources
    sources = get_all_sources()

    # 3. Select sources based on config
    selected_sources = select_sources(sources, config)

    print(f"Selected sources: {[s.name for s in selected_sources]}")

    # 4. Run research (fetch data)
    raw_items = await run_research(selected_sources)

    print(f"Fetched items: {len(raw_items)}")

    # 5. Filter items
    filtered_items = filter_items(raw_items, config)

    print(f"Filtered items: {len(filtered_items)}")

    # 6. Initialize LLM client
    llm_client = get_llm_client(config)

    # 7. Process with LLM
    results = await process_items(filtered_items, llm_client)

    # 8. Output results (simple print for MVP)
    print("\n=== RESULTS ===\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {result}\n{'-' * 40}")


if __name__ == "__main__":
    asyncio.run(main())