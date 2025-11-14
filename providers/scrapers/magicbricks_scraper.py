"""
MagicBricks property scraper using Crawl4AI
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai import JsonCssExtractionStrategy , JsonXPathExtractionStrategy, LLMConfig
 
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(filename=".env"))


class MagicBricksScraper:
    """MagicBricks property scraper"""

    SCHEMA_PATH = Path(__file__).parent / "schemas" / "magicbricks_schema.json"
    SAMPLE_HTML_PATH = Path(__file__).parent / "sample_html" / "magicbricks_residential_sale_sample.html"
    SCHEMA_PROMPT_PATH = Path(__file__).parent / "prompts" / "magicbricks_schema_generation_prompt.txt"

    def __init__(self):
        """Initialize scraper"""
        self.schema = None

    async def _load_or_generate_schema(self):
        """Load existing schema or generate if not exists"""
        # Try to load existing schema
        if self.SCHEMA_PATH.exists():
            print("[MagicBricks] Using existing schema")
            with open(self.SCHEMA_PATH, 'r') as f:
                self.schema = json.load(f)
            return

        # Generate schema (first time only)
        print("[MagicBricks] Generating schema (first time)...")

        # Load sample HTML from file
        if not self.SAMPLE_HTML_PATH.exists():
            raise FileNotFoundError(f"Sample HTML file not found: {self.SAMPLE_HTML_PATH}")

        with open(self.SAMPLE_HTML_PATH, 'r', encoding='utf-8') as f:
            sample_html = f.read()

        # Load schema generation prompt from file
        if not self.SCHEMA_PROMPT_PATH.exists():
            raise FileNotFoundError(f"Schema prompt file not found: {self.SCHEMA_PROMPT_PATH}")

        with open(self.SCHEMA_PROMPT_PATH, 'r', encoding='utf-8') as f:
            schema_prompt = f.read().strip()

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_AI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GEMINI_AI_API_KEY not found in environment")

        # self.schema = JsonCssExtractionStrategy.generate_schema(
        #     html=sample_html,
        #     llm_config=LLMConfig(
        #         provider="gemini/gemini-2.5-flash",
        #         api_token=api_key,
        #     ),
        #     query=schema_prompt
        # )
        # Option 1: Using OpenAI (requires API token)
        self.schema= JsonXPathExtractionStrategy.generate_schema(
            html=sample_html,
            schema_type="xpath",
            llm_config = LLMConfig(provider="openai/gpt-4o",api_token=os.getenv("OPENAI_API_KEY"))
        )
        # Save schema
        self.SCHEMA_PATH.parent.mkdir(exist_ok=True)
        with open(self.SCHEMA_PATH, 'w') as f:
            json.dump(self.schema, f, indent=2)
        print(f"[MagicBricks] Schema saved to {self.SCHEMA_PATH}")
        print("[MagicBricks] Generated Schema:")
        print(json.dumps(self.schema, indent=2))

    async def scrape(self, url: str) -> List[Dict[str, Any]]:
        """
        Scrape properties from MagicBricks URL (can return multiple properties for search results)

        Args:
            url: MagicBricks property URL or search results URL

        Returns:
            List of property dictionaries (raw data from schema)
        """
        print(f"[MagicBricks] Starting scrape for: {url}")

        # Load or generate schema
        if not self.schema:
            print("[MagicBricks] Schema not loaded, loading/generating...")
            await self._load_or_generate_schema()
        else:
            print("[MagicBricks] Using cached schema")

        # Create extraction strategy
        extraction_strategy = JsonXPathExtractionStrategy(self.schema)
        print("[MagicBricks] Created extraction strategy")

        # Scrape the page
        print("[MagicBricks] Starting crawler...")
        async with AsyncWebCrawler(config=BrowserConfig(
            headless=True,
            verbose=False
        )) as crawler:
            config = CrawlerRunConfig(extraction_strategy=extraction_strategy)
            results = await crawler.arun(url, config=config)
            print(f"[MagicBricks] Crawler returned {len(results)} results")

            for result in results:
                if result.success:
                    print("[MagicBricks] Extraction successful!")
                    print(f"[MagicBricks] Raw extracted content: {result.extracted_content[:500]}...")
                    data = json.loads(result.extracted_content)
                    print(f"[MagicBricks] Parsed data type: {type(data)}")

                    # Handle different response formats
                    if isinstance(data, dict) and "property_data_array" in data:
                        # Response wrapped in object
                        properties = data["property_data_array"]
                        print(f"[MagicBricks] Data is dict with property_data_array containing {len(properties)} items")
                        return properties
                    elif isinstance(data, list):
                        # Direct array response
                        print(f"[MagicBricks] Data is list with {len(data)} items")
                        return data
                    else:
                        # Single property
                        print("[MagicBricks] Data is single property object")
                        return [data]
                else:
                    error_msg = getattr(result, 'error_message', 'Unknown error')
                    print(f"[MagicBricks] Extraction failed: {error_msg}")
                    raise Exception(f"Scraping failed: {error_msg}")

        raise Exception("No results from crawler")
