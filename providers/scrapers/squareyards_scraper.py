"""
Simple SquareYards property scraper using Crawl4AI
"""
import os
import json
import re
from pathlib import Path
from typing import Tuple, Dict, Any
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai import JsonCssExtractionStrategy, LLMConfig
from models.scraping import PropertyDetails, PropertyAgent
from dotenv import load_dotenv

load_dotenv()


class SquareYardsScraper:
    """Simple SquareYards scraper"""

    SCHEMA_PATH = Path(__file__).parent / "schemas" / "squareyards_schema.json"

    # Sample HTML for schema generation (only used once)
    SAMPLE_HTML = """
<article class="listing-card single-box-conversion horizontal two-line-description" propertyid="9018132">
    <figure class="sm-arrow listing-img">
        <div class="single-image">
            <div class="item">
                <img class="img-responsive" src="https://img.squareyards.com/secondaryPortal/IN_638895852234012103-310725070023023.jpg" alt="5 BHK Independent House">
            </div>
        </div>
    </figure>
    <div class="listing-body">
        <h2 class="heading" data-href="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132">5 BHK House for Sale in Indiranagar, Bangalore</h2>
        <p class="location"><span>Indiranagar, Bangalore</span></p>
        <p class="listing-price"><strong>₹ 4.2 Cr</strong></p>
        <ul class="listing-information">
            <li><span>5 BHK + 5 Bath</span></li>
            <li class="unit-drop">
                <div class="unit-convert-box">
                    <span class="unit-value avail-area" data-sqft="1200">1200<span class="unit-label">Sq.Ft.</span></span>
                    <b>(Carpet Area)</b>
                </div>
            </li>
            <li><span>West Facing</span></li>
            <li><span>1 Covered + 1 Open</span></li>
            <li><span>Marble Flooring</span></li>
            <li><span>Unfurnished</span></li>
        </ul>
        <div class="description"><p>This spacious 5-bedroom, 5-bathroom independent house...</p></div>
    </div>
    <div class="listing-footer">
        <div class="listing-agent" data-href="https://www.squareyards.com/agent/Lakshminaryana-N/342520">
            <figure class="agent-img">
                <img src="https://img.squareyards.com/connect/profilepic/919019355095638163372242242136.jpg" alt="Agent">
            </figure>
            <strong class="agent-name">Lakshminaryana N<span class="rating">4.7</span></strong>
        </div>
    </div>
</article>
"""

    def __init__(self):
        """Initialize scraper"""
        self.schema = None

    async def _load_or_generate_schema(self):
        """Load existing schema or generate if not exists"""
        # Try to load existing schema
        if self.SCHEMA_PATH.exists():
            print("[SquareYards] Using existing schema")
            with open(self.SCHEMA_PATH, 'r') as f:
                self.schema = json.load(f)
            return

        # Generate schema (first time only)
        print("[SquareYards] Generating schema (first time)...")

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment")

        self.schema = JsonCssExtractionStrategy.generate_schema(
            html=self.SAMPLE_HTML,
            llm_config=LLMConfig(
                provider="gemini/gemini-2.5-flash-lite",
                api_token=api_key,
            ),
            query="Generate a JSON CSS extraction schema for from https://www.squareyards.com/ property listings. Use 'baseSelector' to target the repeating article elements, and 'fields' array to extract each property detail (title, price, location, bedrooms, bathrooms, area, facing, parking, flooring, furnishing, description, images, agent name, agent rating, etc.) using CSS selectors."
        )

        # Save schema
        self.SCHEMA_PATH.parent.mkdir(exist_ok=True)
        with open(self.SCHEMA_PATH, 'w') as f:
            json.dump(self.schema, f, indent=2)
        print(f"[SquareYards] Schema saved to {self.SCHEMA_PATH}")
        print("[SquareYards] Generated Schema:")
        print(json.dumps(self.schema, indent=2))

    async def scrape(self, url: str) -> Tuple[PropertyDetails, PropertyAgent]:
        """
        Scrape property from SquareYards URL

        Args:
            url: SquareYards property URL

        Returns:
            Tuple of (PropertyDetails, PropertyAgent)
        """
        print(f"[SquareYards] Starting scrape for: {url}")

        # Load or generate schema
        if not self.schema:
            print("[SquareYards] Schema not loaded, loading/generating...")
            await self._load_or_generate_schema()
        else:
            print("[SquareYards] Using cached schema")

        # Create extraction strategy
        extraction_strategy = JsonCssExtractionStrategy(self.schema)
        print("[SquareYards] Created extraction strategy")

        # Scrape the page
        print("[SquareYards] Starting crawler...")
        async with AsyncWebCrawler(config=BrowserConfig(
            headless=True,
            verbose=False
        )) as crawler:
            config = CrawlerRunConfig(extraction_strategy=extraction_strategy)
            results = await crawler.arun(url, config=config)
            print(f"[SquareYards] Crawler returned {len(results)} results")

            for result in results:
                if result.success:
                    print("[SquareYards] Extraction successful!")
                    print(f"[SquareYards] Raw extracted content: {result.extracted_content[:500]}...")
                    data = json.loads(result.extracted_content)
                    print(f"[SquareYards] Parsed data type: {type(data)}")
                    if isinstance(data, list):
                        print(f"[SquareYards] Data is list with {len(data)} items")
                    return self._parse_data(data, url)
                else:
                    error_msg = getattr(result, 'error_message', 'Unknown error')
                    print(f"[SquareYards] Extraction failed: {error_msg}")
                    raise Exception(f"Scraping failed: {error_msg}")

        raise Exception("No results from crawler")

    def _parse_data(self, data: Dict[str, Any], url: str) -> Tuple[PropertyDetails, PropertyAgent]:
        """Parse extracted data to models"""
        print("[SquareYards] Parsing extracted data to models...")
        # Handle list or dict
        item = data[0] if isinstance(data, list) and len(data) > 0 else data
        print(f"[SquareYards] Item keys: {list(item.keys()) if isinstance(item, dict) else 'Not a dict'}")

        # Extract values with fallbacks
        property_id = str(item.get('property_id', ''))
        title = item.get('title', '')
        price = item.get('price', '')
        location = item.get('location', '')
        bhk_bath = item.get('bhk_bath', '')
        area_sqft = item.get('area_sqft', '0')
        area_text = item.get('area_text', '')

        # Parse property details
        property_details = PropertyDetails(
            property_id=property_id,
            title=title,
            price=price,
            price_amount=self._parse_price(price),
            location=location,
            city=self._extract_city(location),
            sublocality=self._extract_sublocality(location),
            bedrooms=self._extract_bedrooms(bhk_bath),
            bathrooms=self._extract_bathrooms(bhk_bath),
            bhk=self._extract_bhk(bhk_bath),
            area=area_text or f"{area_sqft} Sq.Ft.",
            area_sqft=int(area_sqft) if str(area_sqft).isdigit() else 0,
            carpet_area=f"{area_text} (Carpet Area)" if area_text else "",
            property_type=item.get('property_type', 'House'),
            facing=item.get('facing'),
            parking=item.get('parking'),
            flooring=item.get('flooring'),
            furnishing=item.get('furnishing'),
            description=item.get('description', ''),
            url=item.get('url', url),
            image_url=item.get('image_url', '')
        )

        # Parse agent
        agent = PropertyAgent(
            name=item.get('agent_name', '').strip(),
            rating=self._parse_rating(item.get('agent_rating')),
            image_url=item.get('agent_image', ''),
            profile_url=item.get('agent_profile_url', ''),
            user_type="CP"
        )

        return property_details, agent

    # Helper parsing methods
    def _parse_price(self, price_str: str) -> int:
        """Convert '₹ 4.2 Cr' to 42000000"""
        if not price_str:
            return 0
        price_str = price_str.replace('₹', '').replace(',', '').strip()
        match = re.search(r'([\d.]+)\s*(Cr|Crore|Lac|Lakh)?', price_str, re.IGNORECASE)
        if not match:
            return 0
        number = float(match.group(1))
        unit = match.group(2)
        if unit and unit.lower() in ['cr', 'crore']:
            return int(number * 10000000)
        elif unit and unit.lower() in ['lac', 'lakh']:
            return int(number * 100000)
        return int(number)

    def _extract_city(self, location: str) -> str:
        """Extract 'Bangalore' from 'Indiranagar, Bangalore'"""
        parts = location.split(',')
        return parts[-1].strip() if parts else ""

    def _extract_sublocality(self, location: str) -> str:
        """Extract 'Indiranagar' from 'Indiranagar, Bangalore'"""
        parts = location.split(',')
        return parts[0].strip() if parts else ""

    def _extract_bedrooms(self, bhk_bath: str) -> int:
        """Extract 5 from '5 BHK + 5 Bath'"""
        match = re.search(r'(\d+)\s*BHK', bhk_bath, re.IGNORECASE)
        return int(match.group(1)) if match else 0

    def _extract_bathrooms(self, bhk_bath: str) -> int:
        """Extract 5 from '5 BHK + 5 Bath'"""
        match = re.search(r'(\d+)\s*Bath', bhk_bath, re.IGNORECASE)
        return int(match.group(1)) if match else 0

    def _extract_bhk(self, bhk_bath: str) -> str:
        """Extract '5 BHK' from '5 BHK + 5 Bath'"""
        match = re.search(r'(\d+\s*BHK)', bhk_bath, re.IGNORECASE)
        return match.group(1) if match else ""

    def _parse_rating(self, rating: Any) -> float:
        """Parse '4.7' to 4.7"""
        if not rating:
            return None
        match = re.search(r'([\d.]+)', str(rating))
        return float(match.group(1)) if match else None
