/**
 * Area Intelligence Service
 * Uses AI (Google Gemini) to research and extract structured area data
 * Based on 13 Q&A format for comprehensive area profiling
 */

import { GoogleGenerativeAI } from '@google/generative-ai'
import {
    AreaIntelligenceResult,
    VibeAndLifestyle,
    MarketData,
    Infrastructure,
    LocalAmenities,
    BuyerIntelligence,
    AreaNarratives
} from '@/lib/types/area-intelligence'
import { fetchAndUploadAreaImages } from '@/lib/services/area-image-service'
import { generateAreaSlug } from '@/lib/utils/area-helpers'

export class AreaIntelligenceService {
    private searchId: string
    private gemini: GoogleGenerativeAI

    constructor() {
        this.searchId = `area-${Date.now()}-${Math.random().toString(36).substring(7)}`

        const apiKey = process.env.GOOGLE_AI_API_KEY
        if (!apiKey) throw new Error('GOOGLE_AI_API_KEY not configured')
        this.gemini = new GoogleGenerativeAI(apiKey)

        console.log(`[AreaIntelligence:${this.searchId}] 🚀 Initialized with Google Gemini`)
    }

    /**
     * Main method: Research area intelligence using AI
     */
    async researchArea(areaName: string, cityName: string): Promise<Partial<AreaIntelligenceResult>> {
        console.log(`[AreaIntelligence:${this.searchId}] 🔍 Researching: ${areaName}, ${cityName}`)

        try {
            const prompt = this.buildResearchPrompt(areaName, cityName)
            const aiResponse = await this.geminiSearch(prompt, areaName, cityName)
            const parsed = this.parseAIResponse(aiResponse)

            // Fetch and upload area images
            console.log(`[AreaIntelligence:${this.searchId}] 🖼️ Fetching area images...`)
            const slug = generateAreaSlug(areaName, cityName)
            let areaImages: string[] = []

            try {
                areaImages = await fetchAndUploadAreaImages(areaName, cityName, slug, 8)
                if (areaImages.length > 0) {
                    console.log(`[AreaIntelligence:${this.searchId}] ✅ Added ${areaImages.length} images`)
                } else {
                    console.log(`[AreaIntelligence:${this.searchId}] ⚠️ No images fetched`)
                }
            } catch (imageError: any) {
                console.error(`[AreaIntelligence:${this.searchId}] ❌ Image fetch failed (non-blocking):`, imageError.message)
                // Continue without images - non-blocking failure
            }

            return {
                area: areaName,
                description: parsed.description,
                overview: parsed.overview,
                vibeAndLifestyle: parsed.vibeAndLifestyle,
                marketData: parsed.marketData,
                infrastructure: parsed.infrastructure,
                localAmenities: parsed.localAmenities,
                buyerIntelligence: parsed.buyerIntelligence,
                narratives: parsed.narratives,
                areaImages: areaImages.length > 0 ? areaImages : undefined,
                confidenceScore: this.calculateConfidence(parsed),
                lastAnalyzed: new Date().toISOString(),
                dataSource: 'gemini_search'
            }

        } catch (error: any) {
            console.error(`[AreaIntelligence:${this.searchId}] ❌ Error:`, error.message)
            throw error
        }
    }

    /**
     * Build structured prompt for AI
     */
    private buildResearchPrompt(areaName: string, cityName: string): string {
        return `You are a real estate market research analyst. Research and provide comprehensive, factual information about **${areaName}, ${cityName}** in India.

Answer ALL of the following questions with specific, accurate data. Use current market data (2024-2025). Format your response as valid JSON.

**VIBE & LIFESTYLE:**
Q1. What is the unique local vibe of ${areaName}, and which demographic is it best suited for (families, young professionals, retirees, students)?
Q2. Where are the main local parks, community shopping centers, and leisure spots around ${areaName}?

**MARKET DATA & INVESTMENT:**
Q3. What is the average capital value (price per sq. ft.) for 2/3 BHK flats in ${areaName}, and what is the annual appreciation rate?
Q4. What is the current rental yield in ${areaName}, and typical rental ranges for 2BHK and 3BHK units?
Q5. What are the stamp duty and registration costs in ${cityName}, and how does the Guidance Value affect buyers in ${areaName}?

**INFRASTRUCTURE & COMMUTE:**
Q6. How reliable is the water supply and sewage infrastructure in ${areaName}?
Q7. What are typical commute times from ${areaName} to major hubs like airport, IT corridors, business districts?
Q8. What major infrastructure projects are improving connectivity in ${areaName} (Metro, highways, flyovers)?

**LOCAL AMENITIES:**
Q9. Which top-rated hospitals and schools are near ${areaName}?
Q10. What are the top 5-7 premium gated communities or apartment projects in ${areaName}?

**BUYER STRATEGY & TIPS:**
Q11. What is the estimated total hidden cost (registration, taxes, amenities, etc.) when purchasing property in ${areaName}?
Q12. Is it better to buy ready-to-move-in or under-construction apartments in ${areaName}, and why?
Q13. What is a common mistake or insider tip for new buyers in ${areaName}?

Return your response as a JSON object with the following structure:

{
  "description": "1-2 line summary of the area",
  "overview": "2-3 paragraph detailed overview",
  "vibeAndLifestyle": {
    "uniqueVibe": "string",
    "bestSuitedFor": ["families", "young_professionals", "retirees", "students"],
    "localParks": ["park names"],
    "shoppingCenters": ["mall names"],
    "leisureSpots": ["leisure venue names"],
    "diningAndSocial": ["restaurant/cafe names"]
  },
  "marketData": {
    "avgPricePerSqft": number,
    "priceCurrency": "INR",
    "appreciationRate": number,
    "rentalYieldMin": number,
    "rentalYieldMax": number,
    "rental2bhkMin": number,
    "rental2bhkMax": number,
    "rental3bhkMin": number,
    "rental3bhkMax": number,
    "investmentRating": "rental_income | capital_appreciation | balanced",
    "stampDutyPercentage": number,
    "registrationCostsNote": "string"
  },
  "infrastructure": {
    "waterSupplyReliability": "excellent | good | mixed | poor",
    "sewageInfrastructure": "string",
    "bwssbAccess": boolean,
    "borewellsCommon": boolean,
    "commuteTimes": [
      {"destination": "Airport", "minMinutes": number, "maxMinutes": number},
      {"destination": "Whitefield", "minMinutes": number, "maxMinutes": number}
    ],
    "upcomingProjects": ["project descriptions"],
    "metroConnectivity": {
      "line": "string",
      "status": "operational | under_construction | planned",
      "nearestStation": "string"
    }
  },
  "localAmenities": {
    "topHospitals": [
      {"name": "string", "distanceKm": number, "specialty": "string"}
    ],
    "topSchools": [
      {"name": "string", "type": "international | cbse | icse | state_board", "distanceKm": number}
    ],
    "premiumCommunities": ["community names"],
    "shoppingMalls": ["mall names"],
    "entertainmentVenues": ["venue names"]
  },
  "buyerIntelligence": {
    "hiddenCostsPercentage": number,
    "hiddenCostsBreakdown": ["cost item descriptions"],
    "rtmVsUcRecommendation": "string with advice",
    "insiderTips": ["tip strings"],
    "commonMistakes": ["mistake strings"],
    "bestForProfile": "end_user | investor | family | bachelor | any"
  },
  "narratives": {
    "vibeNarrative": "2-3 paragraphs about vibe and lifestyle",
    "marketNarrative": "2-3 paragraphs about market dynamics",
    "connectivityNarrative": "2-3 paragraphs about connectivity",
    "amenitiesNarrative": "2-3 paragraphs about amenities",
    "investmentNarrative": "2-3 paragraphs about investment potential"
  }
}

IMPORTANT:
- Provide REAL, FACTUAL data. Do not make up numbers.
- If specific data is unavailable, use "N/A" or omit the field.
- Focus on ${areaName}, ${cityName} specifically.
- Use current market data (2024-2025).
- Return ONLY valid JSON, no additional text.`
    }

    /**
     * Google Gemini Search implementation
     */
    private async geminiSearch(prompt: string, areaName: string, cityName: string): Promise<string> {
        console.log(`[AreaIntelligence:${this.searchId}] 🌐 Using Google Gemini Search`)

        const model = this.gemini.getGenerativeModel({
            model: 'gemini-2.0-flash-exp',
            tools: [{ googleSearch: {} }] as any
        })

        const result = await model.generateContent(prompt)
        return result.response.text()
    }

    /**
     * Parse AI response and extract structured data
     */
    private parseAIResponse(aiResponse: string): any {
        try {
            // Extract JSON from response (might have markdown code blocks)
            const jsonMatch = aiResponse.match(/```json\n([\s\S]*?)\n```/) ||
                aiResponse.match(/```\n([\s\S]*?)\n```/) ||
                aiResponse.match(/\{[\s\S]*\}/)

            if (!jsonMatch) {
                throw new Error('No JSON found in AI response')
            }

            const jsonString = jsonMatch[1] || jsonMatch[0]
            return JSON.parse(jsonString)

        } catch (error) {
            console.error(`[AreaIntelligence:${this.searchId}] ❌ Failed to parse JSON:`, error)
            throw new Error('Failed to parse AI response as JSON')
        }
    }

    /**
     * Calculate confidence score based on data completeness
     */
    private calculateConfidence(parsed: any): number {
        let score = 0
        const weights = {
            description: 5,
            overview: 5,
            vibeAndLifestyle: 15,
            marketData: 20,
            infrastructure: 20,
            localAmenities: 15,
            buyerIntelligence: 15,
            narratives: 5
        }

        for (const [key, weight] of Object.entries(weights)) {
            if (parsed[key]) {
                // Check if object has meaningful data
                if (typeof parsed[key] === 'object') {
                    const fieldCount = Object.keys(parsed[key]).length
                    if (fieldCount > 0) {
                        score += weight
                    }
                } else if (typeof parsed[key] === 'string' && parsed[key].length > 10) {
                    score += weight
                }
            }
        }

        return Math.min(100, score)
    }
}
