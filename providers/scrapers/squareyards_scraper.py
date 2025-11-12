"""
Simple SquareYards property scraper using Crawl4AI
"""
import os
import json
import re
from pathlib import Path
from typing import Tuple, Dict, Any, List
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai import JsonCssExtractionStrategy, LLMConfig
from models.scraping import PropertyDetails, PropertyAgent
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(filename=".env"))


class SquareYardsScraper:
    """Simple SquareYards scraper"""

    SCHEMA_PATH = Path(__file__).parent / "schemas" / "squareyards_schema.json"

    # Sample HTML for schema generation (only used once)
    SAMPLE_HTML = """
 <article class="listing-card single-box-conversion horizontal two-line-description" propertyid="9018132">
        <figure class="sm-arrow listing-img">
            
            <ul class="property-label" data-href="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" data-target="_blank">
                
                
                       
                
                
            </ul>
            
                <div class="favorite-btn shortlistcontainerlink1" data-price="42000000" data-city="Bangalore" data-sublocalityname="Indiranagar" data-unittype="5 BHK" data-name="5 BHK Independent House For Sale in Ln Prapertey " data-cityid="N/A" data-sublocalityid="64805" data-locality="Indiranagar, Bangalore" data-propertyid="9018132" data-url="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" data-image="https://img.squareyards.com/secondaryPortal/IN_638895852234012103-310725070023023.jpg" data-type="resale" data-propstatus="N/A" data-propname="5 BHK Independent House for Sale in Indiranagar" data-area="1200 Sq.Ft." data-projectname="" data-user="342520" data-location="Bangalore" data-user-type="CP" data-property-title="5 BHK Independent House For Sale in Ln Prapertey " data-propertylink="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" data-urlslug="Lakshminaryana-N" data-username="Lakshminaryana N " data-brokerimagepath="https://img.squareyards.com/connect/profilepic/919019355095638163372242242136.jpg" data-agentpremium="0" data-agentrating="4.7" data-brokerlocation="Bangalore" data-agentexperience="7" data-mobilenumber="+91901XXXXXXX" data-totalprice="₹ 4.2 Cr" data-pricedurationname="" data-propertytype="Independent House" data-translatedpropname="" data-translatedprojectname="">
                    <em class="icon-heart-line"></em>
                </div>
            
                <div class="single-image">
                
                    <div class="item" data-href="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" data-target="_blank">
                        <img class="img-responsive" loading="eager" fetchpriority="high" width="360" height="250" src="https://img.squareyards.com/secondaryPortal/IN_638895852234012103-310725070023023.jpg?aio=w-360;h-250;crop;" alt="5 BHK Independent House For Sale in Indiranagar">
                    </div>
            
        </div>
        </figure>
        <div class="listing-body" data-url="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" data-target="_blank">
            
            <h2 class="heading" data-href="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" data-target="_blank">5 BHK House for Sale in Indiranagar, Bangalore</h2>
            
                <p class="location">
                    <em class="icon-pin"></em>
                    <span>
                        Indiranagar, Bangalore
                    </span>
                </p>
            
            
            <p class="listing-price">
                
                    <strong>₹ 4.2 Cr</strong>
                    
                
                
            </p>
            <ul class="listing-information">
                
                
                
                
                    <li> <em class="icon-bed"></em> <span>5 BHK + 5 Bath</span> </li>
                
                
                    <li class="unit-drop">
                        <em class="icon-unit-size"></em>
                        <div class="unit-convert-box">
                            <span class="unit-value avail-area" data-sqft="1200">
                            1200 
                                <div class="sqft-dropdown-box" data-unittype="Independent House">
                                        <span class="unit-label" data-unit="Sq.Ft.">Sq.Ft.</span>
                                </div>
                            </span>
                        
                            <b>(Carpet Area)</b>
                        </div>
                    </li>
                
                
                
                
                
                    <li> <em class="icon-remedies"></em> <span> West Facing</span> </li>
                
                
                
                    <li> <em class="icon-parking"></em> <span>1 Covered + 1 Open</span> </li>
                
                
                    <li> <em class="icon-floor"></em> <span>Marble Flooring</span> </li>
                
                
                
                    <li>
                        <em class="icon-semi-furnished"></em>
                        <span>Unfurnished</span>
                    </li>
                
                
            </ul>
            
                <div class="description redirectReadMore" data-url="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" data-target="_blank">
                    <p>This spacious 5-bedroom, 5-bathroom independent house in Bangalore popular Indiranagar locality is now available for sale at 4.2 crore.Spread across 1200 square feet of living space, this unfurnished home offers a fantastic canvas for you to design your dream interiors. Located on a road-facing plot, you'll appreciate the easy access and pleasant views. With a property age of over 10</p>
                     
                        <div class="btn btn-link read-more"><span>Read More</span></div>
                    
                </div>
            
            
        </div>
        <div class="listing-footer">
            
                <div class="listing-agent" data-href="https://www.squareyards.com/agent/Lakshminaryana-N/342520" data-target="_blank">
            
                <figure class="agent-img">
                    
                        <img class="img-responsive" loading="lazy" width="32" height="32" src="https://img.squareyards.com/connect/profilepic/919019355095638163372242242136.jpg?aio=w-32;h-32;crop;" alt="Lakshminaryana N  profile picture">
                    
                </figure>
                <strong class="agent-name">
                    
                        Lakshminaryana N
                    
                    
                        <span class="rating"><em class="icon-star"></em>4.7</span>
                    
                </strong>
                
            </div>
            <div class="lead-box">
                
                    <button class="btn btn-primary-o openCommonLeadForm" usertype="CP" urlslug="Lakshminaryana-N" createdby="342520" username="Lakshminaryana N " brokerimagepath="https://img.squareyards.com/connect/profilepic/919019355095638163372242242136.jpg" agentpremium="0" agentrating="4.7" experience="" propertyid="9018132" propertytitle="5 BHK 1200 Sq.Ft. Independent House in Ln Prapertey " cityname="Bangalore" cityid="" sublocalityid="64805" location="Indiranagar, Bangalore" totalprice="42000000" propertytype="Independent House" unittype="5 BHK" priceamount="42000000" sublocalityname="Indiranagar" projectname="" area="1200 Sq.Ft." listingtype="Sale" propertylink="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" agenttags="" formtype="LISTING" pagecategory="LISTING" brokerplan="" data-button="view-number">
                       <em class="icon-phone-book"></em>  View Number</button>
                
                <div class="btn btn-primary openCommonLeadForm" usertype="CP" urlslug="Lakshminaryana-N" createdby="342520" username="Lakshminaryana N " brokerimagepath="https://img.squareyards.com/connect/profilepic/919019355095638163372242242136.jpg" agentpremium="0" agentrating="4.7" experience="" propertyid="9018132" propertytitle="5 BHK 1200 Sq.Ft. Independent House in Ln Prapertey " cityname="Bangalore" cityid="" sublocalityid="64805" location="Indiranagar, Bangalore" totalprice="42000000" propertytype="Independent House" unittype="5 BHK" priceamount="42000000" sublocalityname="Indiranagar" projectname="" area="1200 Sq.Ft." listingtype="Sale" propertylink="https://www.squareyards.com/resale-5-bhk-1200-sq-ft-independent-house-in-ln-prapertey/9018132" agenttags="" formtype="LISTING" pagecategory="LISTING" brokerplan="" data-button="contact">
                    <em class="icon-call-b"></em>
                    
                        <span>Contact Agent</span>
                    
                </div>
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

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_AI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GEMINI_AI_API_KEY not found in environment")

        self.schema = JsonCssExtractionStrategy.generate_schema(
            html=self.SAMPLE_HTML,
            llm_config=LLMConfig(
                provider="gemini/gemini-2.5-flash-lite",
                api_token=api_key,
            ),
            query="Generate a JSON CSS extraction schema for from https://www.squareyards.com/ property listings. Use 'baseSelector' to target the repeating article elements, and 'fields' array to extract each property detail (title, price, location, bedrooms, bathrooms, area, facing, parking, flooring, furnishing, description, images, agent name, agent rating, etc.) using CSS selectors. look for teh icon to get the correct value for the field. for eg if the icon-clasbeds  is a bed, then the value should be the number of bedrooms."
        )

        # Save schema
        self.SCHEMA_PATH.parent.mkdir(exist_ok=True)
        with open(self.SCHEMA_PATH, 'w') as f:
            json.dump(self.schema, f, indent=2)
        print(f"[SquareYards] Schema saved to {self.SCHEMA_PATH}")
        print("[SquareYards] Generated Schema:")
        print(json.dumps(self.schema, indent=2))

    async def scrape(self, url: str) -> List[Tuple[PropertyDetails, PropertyAgent]]:
        """
        Scrape properties from SquareYards URL (can return multiple properties for search results)

        Args:
            url: SquareYards property URL or search results URL

        Returns:
            List of Tuples of (PropertyDetails, PropertyAgent)
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
                        print(f"[SquareYARDS] Data: {json.dumps(data[0], indent=2)}")
                        # Return data as-is for now - schema already parsed it correctly
                        return data
                    else:
                        # Single property
                        return [data]
                else:
                    error_msg = getattr(result, 'error_message', 'Unknown error')
                    print(f"[SquareYards] Extraction failed: {error_msg}")
                    raise Exception(f"Scraping failed: {error_msg}")

        raise Exception("No results from crawler")

    # COMMENTED OUT - Schema already returns data in correct format
    # def _parse_all_properties(self, data: List[Dict[str, Any]], url: str) -> List[Tuple[PropertyDetails, PropertyAgent]]:
    #     """Parse all properties from list"""
    #     print(f"[SquareYards] Parsing {len(data)} properties...")
    #     results = []
    #     for i, item in enumerate(data):
    #         try:
    #             print(f"[SquareYards] Parsing property {i + 1}/{len(data)}")
    #             property_details, agent = self._parse_single_property(item, url)
    #             results.append((property_details, agent))
    #         except Exception as e:
    #             print(f"[SquareYards] Error parsing property {i + 1}: {e}")
    #             continue
    #     print(f"[SquareYards] Successfully parsed {len(results)} properties")
    #     return results

    # def _parse_single_property(self, item: Dict[str, Any], url: str) -> Tuple[PropertyDetails, PropertyAgent]:
    #     """Parse single property data to models - data is already well-structured from schema"""
    #     print(f"[SquareYards] Item keys: {list(item.keys()) if isinstance(item, dict) else 'Not a dict'}")

    #     # Data is already parsed correctly by the schema, just map to models
    #     bedrooms_str = item.get('bedrooms', '')
    #     area = item.get('area', '')

    #     # Parse property details - schema already extracts most fields correctly
    #     property_details = PropertyDetails(
    #         property_id=str(item.get('property_id', '')),
    #         title=item.get('title', ''),
    #         price=item.get('price', ''),
    #         price_amount=self._parse_price_crore(item.get('price_crore', '')),
    #         location=item.get('location', ''),
    #         city=self._extract_city(item.get('location', '')),
    #         sublocality=self._extract_sublocality(item.get('location', '')),
    #         bedrooms=self._extract_bedrooms(bedrooms_str),
    #         bathrooms=self._extract_bathrooms(bedrooms_str),
    #         bhk=self._extract_bhk(bedrooms_str),
    #         area=area,
    #         area_sqft=int(re.search(r'(\d+)', area).group(1)) if re.search(r'(\d+)', area) else 0,
    #         carpet_area=area,
    #         property_type='House',
    #         facing=item.get('facing'),
    #         parking=item.get('parking'),
    #         flooring=item.get('flooring'),
    #         furnishing=item.get('furnishing'),
    #         description=item.get('description', ''),
    #         url=item.get('property_url', url),
    #         image_url=item.get('image_url', '')
    #     )

    #     # Parse agent - schema already extracts agent data correctly
    #     agent = PropertyAgent(
    #         name=item.get('agent_name', '').strip(),
    #         rating=float(item.get('agent_rating', 0)) if item.get('agent_rating') else None,
    #         image_url='',
    #         profile_url='',
    #         user_type="CP"
    #     )

    #     return property_details, agent

    # Helper parsing methods (kept for future use if needed)
    def _parse_price_crore(self, price_crore: str) -> int:
        """Convert '\u20b9 4.2 Cr' to 42000000"""
        if not price_crore:
            return 0
        # Remove currency symbols and extract number
        price_str = price_crore.replace('\u20b9', '').replace('₹', '').replace(',', '').strip()
        match = re.search(r'([\d.]+)', price_str)
        if match:
            number = float(match.group(1))
            # Assuming value is in Crores
            return int(number * 10000000)
        return 0

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
