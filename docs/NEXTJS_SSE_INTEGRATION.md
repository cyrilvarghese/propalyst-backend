# Next.js SSE Integration Guide

Complete guide for integrating the property scraping API with Server-Sent Events (SSE) in Next.js.

## Table of Contents
- [Quick Start](#quick-start)
- [Understanding the API](#understanding-the-api)
- [React Hook Implementation](#react-hook-implementation)
- [Component Examples](#component-examples)
- [TypeScript Types](#typescript-types)
- [Error Handling](#error-handling)
- [Testing](#testing)

---

## Quick Start

### 1. Install Dependencies (Optional)
```bash
# No dependencies required! SSE is built into the browser via EventSource API
# Optional: For better TypeScript support
npm install @types/eventsource
```

### 2. Basic Usage

```typescript
'use client';

import { useState, useEffect } from 'react';

export default function PropertySearch() {
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Build API URL
    const apiUrl = 'http://localhost:8000/api/get_listing_details?' +
      new URLSearchParams({
        url: 'https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore',
        orig_query: '2 bhk with east facing and 2 car parking'
      });

    // Connect to SSE stream
    const eventSource = new EventSource(apiUrl);

    // Listen for property events
    eventSource.addEventListener('property', (event) => {
      const property = JSON.parse(event.data);
      setProperties(prev => [...prev, property]);
    });

    // Listen for completion
    eventSource.addEventListener('complete', (event) => {
      const summary = JSON.parse(event.data);
      console.log(`Received ${summary.count} properties in ${summary.api_calls_made} API calls`);
      setIsLoading(false);
      eventSource.close();
    });

    // Handle errors
    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      setIsLoading(false);
      eventSource.close();
    };

    // Cleanup on unmount
    return () => eventSource.close();
  }, []);

  return (
    <div>
      {properties.map((prop, idx) => (
        <PropertyCard key={idx} property={prop} />
      ))}
      {isLoading && <p>Loading properties...</p>}
    </div>
  );
}
```

---

## Understanding the API

### API Endpoint
```
GET http://localhost:8000/api/get_listing_details
```

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | SquareYards property listing URL |
| `orig_query` | string | Yes | User's search query (e.g., "2 bhk east facing") |

### Response Format

The API uses **Server-Sent Events (SSE)** to stream properties as they are scored.

#### Event Types

**1. `property` Event** (Fires multiple times - once per property)
```json
{
  "title": "5 BHK House for Sale in Indiranagar",
  "location": "Indiranagar, Bangalore",
  "price": "₹ 4.2 Cr",
  "price_crore": "₹ 4.2 Cr",
  "bedrooms": "5 BHK + 5 Bath",
  "bathrooms": "5 BHK + 5 Bath",
  "area": "1200Sq.Ft.",
  "facing": "West Facing",
  "parking": "1 Covered + 1 Open",
  "furnishing": "Unfurnished",
  "property_type": "Independent House",
  "property_url": "https://www.squareyards.com/...",
  "image_url": "https://img.squareyards.com/...",
  "description": "This spacious 5-bedroom...",
  "agent_name": "Lakshminaryana N",
  "agent_rating": "4.7",
  "city": "Bangalore",
  "sublocality": "Indiranagar",
  "unit_type": "5 BHK",
  "relevance_score": 2,
  "relevance_reason": "Mismatches: BHK (5 instead of 2), Facing (West instead of East)."
}
```

**2. `complete` Event** (Fires once at the end)
```json
{
  "count": 15,
  "source": "squareyards",
  "scraped_at": "2025-11-13T16:45:46.397188",
  "api_calls_made": 2
}
```

**3. `error` Event** (Fires if error occurs)
```json
{
  "error": "Error message here"
}
```

---

## React Hook Implementation

### Custom Hook: `usePropertyStream`

Create a reusable hook for property streaming:

```typescript
// hooks/usePropertyStream.ts
'use client';

import { useState, useEffect, useCallback } from 'react';

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

interface StreamSummary {
  count: number;
  source: string;
  scraped_at: string;
  api_calls_made: number;
}

interface UsePropertyStreamResult {
  properties: Property[];
  isLoading: boolean;
  error: string | null;
  summary: StreamSummary | null;
  startStream: (listingUrl: string, query: string) => void;
  stopStream: () => void;
}

export function usePropertyStream(): UsePropertyStreamResult {
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<StreamSummary | null>(null);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  const stopStream = useCallback(() => {
    if (eventSource) {
      eventSource.close();
      setEventSource(null);
    }
    setIsLoading(false);
  }, [eventSource]);

  const startStream = useCallback((listingUrl: string, query: string) => {
    // Reset state
    setProperties([]);
    setError(null);
    setSummary(null);
    setIsLoading(true);

    // Build API URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${apiUrl}/api/get_listing_details?` +
      new URLSearchParams({
        url: listingUrl,
        orig_query: query
      });

    // Create EventSource
    const source = new EventSource(url);

    // Handle property events
    source.addEventListener('property', (event) => {
      try {
        const property = JSON.parse(event.data);
        setProperties(prev => [...prev, property]);
      } catch (err) {
        console.error('Failed to parse property:', err);
      }
    });

    // Handle completion
    source.addEventListener('complete', (event) => {
      try {
        const completionData = JSON.parse(event.data);
        setSummary(completionData);
        setIsLoading(false);
        source.close();
      } catch (err) {
        console.error('Failed to parse completion:', err);
      }
    });

    // Handle errors
    source.addEventListener('error', (event) => {
      try {
        const errorData = JSON.parse((event as any).data);
        setError(errorData.error);
      } catch {
        setError('Connection error occurred');
      }
      setIsLoading(false);
      source.close();
    });

    // Generic error handler
    source.onerror = () => {
      setError('Failed to connect to server');
      setIsLoading(false);
      source.close();
    };

    setEventSource(source);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [eventSource]);

  return {
    properties,
    isLoading,
    error,
    summary,
    startStream,
    stopStream
  };
}
```

---

## Component Examples

### Example 1: Basic Property List

```typescript
// components/PropertyList.tsx
'use client';

import { usePropertyStream } from '@/hooks/usePropertyStream';
import { useEffect } from 'react';

export default function PropertyList() {
  const { properties, isLoading, error, summary, startStream } = usePropertyStream();

  useEffect(() => {
    // Start streaming on mount
    startStream(
      'https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore',
      '2 bhk with east facing and 2 car parking'
    );
  }, [startStream]);

  if (error) {
    return (
      <div className="error">
        <h3>Error</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="property-list">
      <h2>Property Search Results</h2>

      {isLoading && properties.length === 0 && (
        <p>Loading properties...</p>
      )}

      <div className="properties-grid">
        {properties.map((property, idx) => (
          <div key={idx} className="property-card">
            <img src={property.image_url} alt={property.title} />
            <h3>{property.title}</h3>
            <p className="location">{property.location}</p>
            <p className="price">{property.price}</p>
            <p className="details">
              {property.bedrooms} | {property.area}
            </p>
            <div className="relevance">
              <span className="score">Score: {property.relevance_score}/10</span>
              <p className="reason">{property.relevance_reason}</p>
            </div>
            <a href={property.property_url} target="_blank">View Details</a>
          </div>
        ))}
      </div>

      {isLoading && properties.length > 0 && (
        <p>Loading more properties... ({properties.length} received)</p>
      )}

      {summary && (
        <div className="summary">
          <p>✓ Loaded {summary.count} properties</p>
          <p>Made {summary.api_calls_made} API calls (85% reduction!)</p>
        </div>
      )}
    </div>
  );
}
```

### Example 2: Search Form with Streaming

```typescript
// components/PropertySearch.tsx
'use client';

import { useState } from 'react';
import { usePropertyStream } from '@/hooks/usePropertyStream';

export default function PropertySearch() {
  const [listingUrl, setListingUrl] = useState('');
  const [query, setQuery] = useState('');
  const { properties, isLoading, error, summary, startStream, stopStream } = usePropertyStream();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (listingUrl && query) {
      startStream(listingUrl, query);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Listing URL:</label>
          <input
            type="url"
            value={listingUrl}
            onChange={(e) => setListingUrl(e.target.value)}
            placeholder="https://www.squareyards.com/..."
            required
          />
        </div>

        <div>
          <label>Search Query:</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="2 bhk east facing 2 car parking"
            required
          />
        </div>

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Searching...' : 'Search Properties'}
        </button>

        {isLoading && (
          <button type="button" onClick={stopStream}>
            Stop
          </button>
        )}
      </form>

      {error && <div className="error">{error}</div>}

      <div className="results">
        <h3>Results ({properties.length})</h3>
        {properties.map((property, idx) => (
          <PropertyCard key={idx} property={property} />
        ))}
      </div>

      {summary && (
        <div className="summary">
          Total: {summary.count} properties | API calls: {summary.api_calls_made}
        </div>
      )}
    </div>
  );
}
```

### Example 3: Progressive Rendering with Animation

```typescript
// components/AnimatedPropertyList.tsx
'use client';

import { usePropertyStream } from '@/hooks/usePropertyStream';
import { AnimatePresence, motion } from 'framer-motion';

export default function AnimatedPropertyList() {
  const { properties, isLoading, startStream } = usePropertyStream();

  return (
    <div className="property-list">
      <AnimatePresence>
        {properties.map((property, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="property-card"
          >
            <h3>{property.title}</h3>
            <p>{property.location}</p>
            <div className="score-badge">
              {property.relevance_score}/10
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {isLoading && (
        <div className="loading-indicator">
          <span>Loading properties...</span>
          <span>{properties.length} received</span>
        </div>
      )}
    </div>
  );
}
```

---

## TypeScript Types

```typescript
// types/property.ts

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

export interface StreamSummary {
  count: number;
  source: string;
  scraped_at: string;
  api_calls_made: number;
}

export interface SSEPropertyEvent {
  type: 'property';
  data: Property;
}

export interface SSECompleteEvent {
  type: 'complete';
  data: StreamSummary;
}

export interface SSEErrorEvent {
  type: 'error';
  data: {
    error: string;
  };
}

export type SSEEvent = SSEPropertyEvent | SSECompleteEvent | SSEErrorEvent;
```

---

## Error Handling

### Comprehensive Error Handling

```typescript
import { usePropertyStream } from '@/hooks/usePropertyStream';
import { useEffect } from 'react';

export default function PropertyListWithErrorHandling() {
  const { properties, isLoading, error, startStream } = usePropertyStream();

  useEffect(() => {
    try {
      startStream(
        'https://www.squareyards.com/sale/5-bhk-for-sale-in-indiranagar-bangalore',
        '2 bhk with east facing'
      );
    } catch (err) {
      console.error('Failed to start stream:', err);
    }
  }, [startStream]);

  // Handle different error types
  if (error) {
    if (error.includes('connect')) {
      return <div>Cannot connect to server. Please check your connection.</div>;
    }
    if (error.includes('timeout')) {
      return <div>Request timed out. Please try again.</div>;
    }
    return <div>Error: {error}</div>;
  }

  return (
    <div>
      {properties.map((prop, idx) => (
        <PropertyCard key={idx} property={prop} />
      ))}
    </div>
  );
}
```

---

## Testing

### Test with Jest and React Testing Library

```typescript
// __tests__/usePropertyStream.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { usePropertyStream } from '@/hooks/usePropertyStream';

// Mock EventSource
global.EventSource = jest.fn(() => ({
  addEventListener: jest.fn(),
  close: jest.fn(),
  onerror: null,
}));

describe('usePropertyStream', () => {
  it('should start streaming properties', async () => {
    const { result } = renderHook(() => usePropertyStream());

    result.current.startStream(
      'https://example.com/listings',
      'test query'
    );

    expect(result.current.isLoading).toBe(true);
  });

  it('should handle completion', async () => {
    const { result } = renderHook(() => usePropertyStream());

    result.current.startStream(
      'https://example.com/listings',
      'test query'
    );

    // Simulate completion
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });
});
```

---

## Best Practices

1. **Always close EventSource on unmount**
   ```typescript
   useEffect(() => {
     return () => eventSource?.close();
   }, [eventSource]);
   ```

2. **Handle connection errors gracefully**
   ```typescript
   source.onerror = () => {
     setError('Connection failed');
     source.close();
   };
   ```

3. **Use environment variables for API URL**
   ```typescript
   const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
   ```

4. **Implement retry logic for failed connections**
   ```typescript
   const [retryCount, setRetryCount] = useState(0);

   source.onerror = () => {
     if (retryCount < 3) {
       setTimeout(() => startStream(url, query), 1000 * (retryCount + 1));
       setRetryCount(prev => prev + 1);
     }
   };
   ```

5. **Show progressive loading state**
   ```typescript
   {isLoading && (
     <p>Loading... {properties.length} of ~15 properties received</p>
   )}
   ```

---

## FAQ

### Q: Why use SSE instead of WebSockets?
**A:** SSE is simpler, unidirectional (server→client), and perfect for streaming results. No need for bidirectional communication.

### Q: How many API calls are made?
**A:** For 15 properties: **2 API calls** (batch of 10 + batch of 5), instead of 15 individual calls. That's an **85% reduction**!

### Q: Can I cancel the stream?
**A:** Yes! Call `eventSource.close()` or use the `stopStream()` method from the hook.

### Q: Does this work in Next.js App Router?
**A:** Yes! Just use `'use client'` directive at the top of your component.

### Q: What if the connection drops?
**A:** Implement retry logic (see Best Practices section) or show an error message to the user.

---

## Support

For issues or questions:
- Check server logs at `/home/propalyst/propalyst-backend/`
- Test endpoint directly: `curl -N http://localhost:8000/api/get_listing_details?url=...`
- Review API documentation at `/docs/API.md`
