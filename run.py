import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from src.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())