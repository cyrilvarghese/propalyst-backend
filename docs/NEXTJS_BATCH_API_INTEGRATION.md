# Next.js Batch API Integration Guide

Complete guide for integrating the **non-streaming** batch property scraping API in Next.js.

## Table of Contents
- [Quick Start](#quick-start)
- [Understanding the API](#understanding-the-api)
- [React Hook Implementation](#react-hook-implementation)
- [Component Examples](#component-examples)
- [TypeScript Types](#typescript-types)
- [Error Handling](#error-handling)
- [Comparison: Batch vs Streaming](#comparison-batch-vs-streaming)

---

## Quick Start

### 1. Basic Usage

```typescript
'use client';

import { useState } from 'react';

export default function PropertySearch() {
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const searchProperties = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        'http://localhost:8000/api/get_listing_details_batch?' +
        new URLSearchParams({
          url: 'https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore',
          orig_query: '2 bhk with east facing and 2 car parking',
          batch_size: '10'  // Optional: defaults to 10
        })
      );

      const data = await response.json();

      if (data.success) {
        setProperties(data.properties);
        console.log(`Received ${data.count} properties`);
        console.log(`API calls made: ${data.api_calls_made}`);
      } else {
        setError(data.error || 'Failed to fetch properties');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <button onClick={searchProperties} disabled={isLoading}>
        {isLoading ? 'Loading...' : 'Search Properties'}
      </button>

      {error && <div className="error">{error}</div>}

      <div className="properties-grid">
        {properties.map((property, idx) => (
          <PropertyCard key={idx} property={property} />
        ))}
      </div>
    </div>
  );
}
```

---

## Understanding the API

### API Endpoint
```
GET http://localhost:8000/api/get_listing_details_batch
```

### Query Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | **Yes** | - | SquareYards property listing URL |
| `orig_query` | string | **Yes** | - | User's search query (e.g., "2 bhk east facing") |
| `batch_size` | integer | No | 10 | Number of properties to score per API call |

### Example Request
```
GET /api/get_listing_details_batch?url=https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore&orig_query=2%20bhk%20with%20east%20facing&batch_size=10
```

### Response Format

**Success Response:**
```json
{
  "success": true,
  "properties": [
    {
      "title": "5 BHK House for Sale in Indiranagar",
      "location": "Indiranagar, Bangalore",
      "price": "₹ 4.2 Cr",
      "price_crore": "₹ 4.2 Cr",
      "bedrooms": "5 BHK + 5 Bath",
      "area": "1200Sq.Ft.",
      "facing": "West Facing",
      "parking": "1 Covered + 1 Open",
      "property_type": "Independent House",
      "property_url": "https://www.squareyards.com/...",
      "image_url": "https://img.squareyards.com/...",
      "relevance_score": 2,
      "relevance_reason": "Mismatches: BHK (5 instead of 2), Facing (West instead of East)."
    }
    // ... more properties
  ],
  "count": 15,
  "source": "squareyards",
  "scraped_at": "2025-11-13T16:45:46.397188",
  "api_calls_made": 2
}
```

**Error Response:**
```json
{
  "success": false,
  "properties": [],
  "count": 0,
  "source": "squareyards",
  "scraped_at": "2025-11-13T16:45:46.397188",
  "error": "Error message here"
}
```

---

## React Hook Implementation

### Custom Hook: `usePropertyBatchSearch`

Create a reusable hook for batch property search:

```typescript
// hooks/usePropertyBatchSearch.ts
'use client';

import { useState, useCallback } from 'react';

interface Property {
  title: string;
  location: string;
  price: string;
  price_crore: string;
  bedrooms: string;
  area: string;
  facing: string;
  parking: string;
  property_type: string;
  property_url: string;
  image_url: string;
  description: string;
  relevance_score: number;
  relevance_reason: string;
  [key: string]: any;
}

interface SearchResponse {
  success: boolean;
  properties: Property[];
  count: number;
  source: string;
  scraped_at: string;
  api_calls_made: number;
  error?: string;
}

interface UsePropertyBatchSearchResult {
  properties: Property[];
  isLoading: boolean;
  error: string | null;
  apiCallsMade: number | null;
  searchProperties: (listingUrl: string, query: string, batchSize?: number) => Promise<void>;
  clearResults: () => void;
}

export function usePropertyBatchSearch(): UsePropertyBatchSearchResult {
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiCallsMade, setApiCallsMade] = useState<number | null>(null);

  const searchProperties = useCallback(
    async (listingUrl: string, query: string, batchSize: number = 10) => {
      setIsLoading(true);
      setError(null);
      setProperties([]);
      setApiCallsMade(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/get_listing_details_batch?` +
          new URLSearchParams({
            url: listingUrl,
            orig_query: query,
            batch_size: batchSize.toString()
          });

        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: SearchResponse = await response.json();

        if (data.success) {
          setProperties(data.properties);
          setApiCallsMade(data.api_calls_made);
        } else {
          setError(data.error || 'Failed to fetch properties');
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(errorMessage);
        console.error('Search error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const clearResults = useCallback(() => {
    setProperties([]);
    setError(null);
    setApiCallsMade(null);
  }, []);

  return {
    properties,
    isLoading,
    error,
    apiCallsMade,
    searchProperties,
    clearResults,
  };
}
```

---

## Component Examples

### Example 1: Simple Search Form

```typescript
// components/PropertyBatchSearch.tsx
'use client';

import { useState } from 'react';
import { usePropertyBatchSearch } from '@/hooks/usePropertyBatchSearch';

export default function PropertyBatchSearch() {
  const [listingUrl, setListingUrl] = useState('');
  const [query, setQuery] = useState('');
  const {
    properties,
    isLoading,
    error,
    apiCallsMade,
    searchProperties,
    clearResults
  } = usePropertyBatchSearch();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (listingUrl && query) {
      await searchProperties(listingUrl, query);
    }
  };

  return (
    <div className="container">
      <h1>Property Search</h1>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Listing URL:</label>
          <input
            type="url"
            value={listingUrl}
            onChange={(e) => setListingUrl(e.target.value)}
            placeholder="https://www.squareyards.com/..."
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-group">
          <label>Search Query:</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="2 bhk east facing 2 car parking"
            required
            disabled={isLoading}
          />
        </div>

        <div className="button-group">
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Searching...' : 'Search Properties'}
          </button>
          {properties.length > 0 && (
            <button type="button" onClick={clearResults} disabled={isLoading}>
              Clear Results
            </button>
          )}
        </div>
      </form>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {properties.length > 0 && (
        <div className="results-info">
          <p>Found {properties.length} properties</p>
          {apiCallsMade && (
            <p className="api-info">
              Made {apiCallsMade} API calls (
              {Math.round((1 - apiCallsMade / properties.length) * 100)}% reduction)
            </p>
          )}
        </div>
      )}

      <div className="properties-grid">
        {properties.map((property, idx) => (
          <PropertyCard key={idx} property={property} />
        ))}
      </div>

      {isLoading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Searching properties...</p>
        </div>
      )}
    </div>
  );
}
```

### Example 2: Advanced Search with Filters

```typescript
// components/AdvancedPropertySearch.tsx
'use client';

import { useState } from 'react';
import { usePropertyBatchSearch } from '@/hooks/usePropertyBatchSearch';

export default function AdvancedPropertySearch() {
  const [listingUrl, setListingUrl] = useState('');
  const [query, setQuery] = useState('');
  const [batchSize, setBatchSize] = useState(10);
  const [sortBy, setSortBy] = useState<'score' | 'price'>('score');

  const { properties, isLoading, error, apiCallsMade, searchProperties } =
    usePropertyBatchSearch();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await searchProperties(listingUrl, query, batchSize);
  };

  // Sort properties
  const sortedProperties = [...properties].sort((a, b) => {
    if (sortBy === 'score') {
      return b.relevance_score - a.relevance_score;
    }
    // Sort by price (convert from string like "₹ 4.2 Cr")
    const priceA = parseFloat(a.price_crore?.replace(/[^\d.]/g, '') || '0');
    const priceB = parseFloat(b.price_crore?.replace(/[^\d.]/g, '') || '0');
    return priceA - priceB;
  });

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          type="url"
          value={listingUrl}
          onChange={(e) => setListingUrl(e.target.value)}
          placeholder="Listing URL"
          required
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search query"
          required
        />
        <select value={batchSize} onChange={(e) => setBatchSize(Number(e.target.value))}>
          <option value={5}>5 per batch</option>
          <option value={10}>10 per batch</option>
          <option value={15}>15 per batch</option>
        </select>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {properties.length > 0 && (
        <div className="filters">
          <label>Sort by:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
            <option value="score">Relevance Score</option>
            <option value="price">Price (Low to High)</option>
          </select>
          <span className="info">
            {properties.length} properties | {apiCallsMade} API calls
          </span>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      <div className="properties">
        {sortedProperties.map((property, idx) => (
          <PropertyCard key={idx} property={property} rank={idx + 1} />
        ))}
      </div>
    </div>
  );
}
```

### Example 3: Property Card Component

```typescript
// components/PropertyCard.tsx
interface PropertyCardProps {
  property: any;
  rank?: number;
}

export function PropertyCard({ property, rank }: PropertyCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    if (score >= 4) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="property-card">
      {rank && <div className="rank-badge">#{rank}</div>}

      <div className="image-container">
        <img
          src={property.image_url}
          alt={property.title}
          className="property-image"
        />
        <div className={`score-badge ${getScoreColor(property.relevance_score)}`}>
          {property.relevance_score}/10
        </div>
      </div>

      <div className="property-content">
        <h3 className="property-title">{property.title}</h3>
        <p className="property-location">📍 {property.location}</p>
        <p className="property-price">💰 {property.price}</p>

        <div className="property-details">
          <span>🛏️ {property.bedrooms}</span>
          <span>📐 {property.area}</span>
          {property.facing && <span>🧭 {property.facing}</span>}
          {property.parking && <span>🚗 {property.parking}</span>}
        </div>

        <div className="relevance-info">
          <p className="reason">{property.relevance_reason}</p>
        </div>

        <div className="property-footer">
          <span className="agent">👤 {property.agent_name}</span>
          <a
            href={property.property_url}
            target="_blank"
            rel="noopener noreferrer"
            className="view-button"
          >
            View Details →
          </a>
        </div>
      </div>
    </div>
  );
}
```

---

## TypeScript Types

```typescript
// types/property-batch.ts

export interface Property {
  title: string;
  location: string;
  price: string;
  price_crore: string;
  bedrooms: string;
  bathrooms: string;
  area: string;
  facing: string;
  parking: string;
  flooring?: string;
  furnishing: string;
  description: string;
  image_url: string;
  agent_name: string;
  agent_rating: string;
  property_url: string;
  city: string;
  sublocality: string;
  unit_type: string;
  property_type: string;
  relevance_score: number;
  relevance_reason: string;
}

export interface BatchSearchResponse {
  success: boolean;
  properties: Property[];
  count: number;
  source: string;
  scraped_at: string;
  api_calls_made: number;
  error?: string;
}

export interface SearchParams {
  url: string;
  orig_query: string;
  batch_size?: number;
}
```

---

## Error Handling

### Comprehensive Error Handling

```typescript
import { usePropertyBatchSearch } from '@/hooks/usePropertyBatchSearch';

export default function PropertySearchWithErrorHandling() {
  const { properties, isLoading, error, searchProperties } = usePropertyBatchSearch();

  const handleSearch = async () => {
    try {
      await searchProperties(
        'https://www.squareyards.com/...',
        '2 bhk east facing'
      );
    } catch (err) {
      console.error('Search failed:', err);
      // Error is already handled in the hook
    }
  };

  // Render different error messages
  const renderError = () => {
    if (!error) return null;

    if (error.includes('HTTP error! status: 500')) {
      return (
        <div className="error">
          Server error. Please try again later.
        </div>
      );
    }

    if (error.includes('Failed to fetch')) {
      return (
        <div className="error">
          Network error. Check your connection.
        </div>
      );
    }

    return (
      <div className="error">
        {error}
        <button onClick={handleSearch}>Retry</button>
      </div>
    );
  };

  return (
    <div>
      {renderError()}
      {/* Rest of component */}
    </div>
  );
}
```

### Timeout Handling

```typescript
async function searchWithTimeout(
  listingUrl: string,
  query: string,
  timeoutMs: number = 30000
) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw error;
  }
}
```

---

## Comparison: Batch vs Streaming

| Feature | Batch API (`get_listing_details_batch`) | Streaming API (`get_listing_details`) |
|---------|----------------------------------------|--------------------------------------|
| **Response Type** | Single JSON response | Server-Sent Events (SSE) stream |
| **Progressive Rendering** | ❌ No - all at once | ✅ Yes - see results as they come |
| **Implementation** | Simple `fetch()` | EventSource API |
| **Loading State** | Binary (loading/done) | Progressive (shows count) |
| **API Calls** | 2 for 15 properties | 2 for 15 properties |
| **Best For** | Simple dashboards, exports | Real-time UIs, live search |
| **Complexity** | Low | Medium |
| **Browser Support** | All browsers | Modern browsers (IE11+) |

### When to Use Batch API:
- ✅ Simple search forms
- ✅ Export/download features
- ✅ Server-side rendering
- ✅ Mobile apps (native fetch)
- ✅ Simpler implementation needed

### When to Use Streaming API:
- ✅ Real-time search results
- ✅ Live dashboards
- ✅ Better UX with progressive rendering
- ✅ Long-running searches

---

## Best Practices

1. **Use Environment Variables**
   ```typescript
   const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
   ```

2. **Add Loading States**
   ```typescript
   {isLoading && <div className="loading-spinner">Searching...</div>}
   ```

3. **Implement Retry Logic**
   ```typescript
   const maxRetries = 3;
   for (let i = 0; i < maxRetries; i++) {
     try {
       return await searchProperties(url, query);
     } catch (err) {
       if (i === maxRetries - 1) throw err;
       await new Promise(r => setTimeout(r, 1000 * (i + 1)));
     }
   }
   ```

4. **Cache Results (Optional)**
   ```typescript
   const [cache, setCache] = useState<Map<string, Property[]>>(new Map());

   const getCacheKey = (url: string, query: string) => `${url}:${query}`;

   // Check cache before fetching
   const cacheKey = getCacheKey(listingUrl, query);
   if (cache.has(cacheKey)) {
     setProperties(cache.get(cacheKey)!);
     return;
   }
   ```

5. **Show API Efficiency**
   ```typescript
   {apiCallsMade && (
     <p>
       Made {apiCallsMade} API calls for {properties.length} properties
       ({Math.round((1 - apiCallsMade / properties.length) * 100)}% reduction!)
     </p>
   )}
   ```

---

## Complete Example

Here's a complete, production-ready implementation:

```typescript
// app/properties/page.tsx
'use client';

import { useState } from 'react';
import { usePropertyBatchSearch } from '@/hooks/usePropertyBatchSearch';
import { PropertyCard } from '@/components/PropertyCard';

export default function PropertiesPage() {
  const [listingUrl, setListingUrl] = useState('');
  const [query, setQuery] = useState('');

  const {
    properties,
    isLoading,
    error,
    apiCallsMade,
    searchProperties,
    clearResults
  } = usePropertyBatchSearch();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await searchProperties(listingUrl, query, 10);
  };

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Property Search</h1>

      <form onSubmit={handleSubmit} className="mb-8 space-y-4">
        <div>
          <label className="block mb-2 font-medium">Listing URL</label>
          <input
            type="url"
            value={listingUrl}
            onChange={(e) => setListingUrl(e.target.value)}
            className="w-full p-2 border rounded"
            placeholder="https://www.squareyards.com/..."
            required
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block mb-2 font-medium">Search Query</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full p-2 border rounded"
            placeholder="2 bhk east facing 2 car parking"
            required
            disabled={isLoading}
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
          {properties.length > 0 && (
            <button
              type="button"
              onClick={clearResults}
              disabled={isLoading}
              className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Clear
            </button>
          )}
        </div>
      </form>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {properties.length > 0 && (
        <div className="mb-4 p-4 bg-blue-50 rounded">
          <p className="font-medium">
            Found {properties.length} properties
          </p>
          {apiCallsMade && (
            <p className="text-sm text-gray-600">
              Made {apiCallsMade} API calls (
              {Math.round((1 - apiCallsMade / properties.length) * 100)}% reduction)
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {properties.map((property, idx) => (
          <PropertyCard key={idx} property={property} />
        ))}
      </div>

      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-8 rounded-lg text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p>Searching properties...</p>
          </div>
        </div>
      )}
    </main>
  );
}
```

---

## Support

- **API Documentation**: See `/docs/API.md`
- **Streaming Version**: See `/docs/NEXTJS_SSE_INTEGRATION.md`
- **Test Endpoint**: `curl http://localhost:8000/api/get_listing_details_batch?url=...`
