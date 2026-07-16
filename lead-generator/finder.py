"""
Lead Generator — Business Finder
Uses Playwright directly to scrape Google Maps search results.
Extracts multiple businesses with name, rating, reviews, website, phone, address.
"""

import asyncio
import csv
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus

from playwright.async_api import async_playwright


def search_google_maps(city, business_type, limit=50):
    """
    Search Google Maps for businesses using Playwright.
    """
    query = f"{business_type} in {city}"
    print(f"[Finder] Searching Google Maps: {query}")
    print(f"[Finder] Launching headless Chromium...")
    
    businesses = asyncio.run(_scrape_async(query, limit))
    
    print(f"[Finder] Found {len(businesses)} businesses")
    return businesses


async def _scrape_async(query, limit=50):
    """Async scraping with Playwright."""
    businesses = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
        )
        
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        await context.add_cookies([{"name": "CONSENT", "value": "YES+cb.20240101-01-p0.en+FX+430", "domain": ".google.com", "path": "/"}])
        
        page = await context.new_page()
        
        search_url = f"https://www.google.com/maps/search/{quote_plus(query)}"
        print(f"[Finder] Navigating to: {search_url}")
        
        try:
            await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            
            await _scroll_results(page, limit)
            
            # Step 1: Get basic info + place URLs from search results
            businesses = await _extract_from_feed(page, limit)
            
            # Step 2: Click each place to get review count + details
            if businesses:
                businesses = await _enrich_with_details(page, businesses, limit)
            
        except Exception as e:
            print(f"[Finder] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
    
    return businesses


async def _scroll_results(page, target_count):
    """Scroll the results feed to load more businesses."""
    print("[Finder] Scrolling to load results...")
    
    feed = await page.query_selector('div[role="feed"]')
    if not feed:
        print("[Finder] No feed found")
        return
    
    prev_count = 0
    max_scrolls = 20
    
    for i in range(max_scrolls):
        current_count = await page.evaluate("""
            () => {
                const feed = document.querySelector('div[role="feed"]');
                if (!feed) return 0;
                return feed.querySelectorAll('div.Nv2PK').length;
            }
        """)
        
        if current_count >= target_count:
            print(f"[Finder] Loaded {current_count} results")
            break
        
        if current_count == prev_count and i > 3:
            print(f"[Finder] No more results after {i} scrolls (total: {current_count})")
            break
        
        prev_count = current_count
        await feed.evaluate("el => el.scrollTop = el.scrollHeight")
        await page.wait_for_timeout(2000)
        
        if (i + 1) % 5 == 0:
            print(f"[Finder] Scroll {i+1}, loaded {current_count} results")
    
    print(f"[Finder] Finished scrolling. Total: {prev_count}")


async def _extract_from_feed(page, limit):
    """Extract basic business data from the search results feed."""
    print("[Finder] Extracting business data from feed...")
    
    js_extract = r"""() => {
        const results = [];
        const feed = document.querySelector('div[role="feed"]');
        if (!feed) return results;
        
        const items = feed.querySelectorAll('div.Nv2PK');
        
        for (const item of items) {
            try {
                const biz = {};
                
                // Name + URL from the main link
                const nameLink = item.querySelector('a.hfpxzc');
                if (nameLink) {
                    biz.name = nameLink.getAttribute('aria-label') || '';
                    biz.google_url = nameLink.href || '';
                }
                
                // Rating from ZkP5Je span
                const ratingSpan = item.querySelector('span.ZkP5Je');
                if (ratingSpan) {
                    const ariaLabel = ratingSpan.getAttribute('aria-label') || '';
                    // Match "4.9 stars" or "4,9 étoiles" etc
                    const ratingMatch = ariaLabel.match(/([0-9]+[.,][0-9]+)/);
                    if (ratingMatch) {
                        biz.rating = parseFloat(ratingMatch[1].replace(',', '.'));
                    }
                }
                
                // Category from W4Efsd section
                const w4 = item.querySelectorAll('div.W4Efsd');
                for (const w of w4) {
                    const spans = w.querySelectorAll('span');
                    for (const sp of spans) {
                        const text = (sp.textContent || '').trim();
                        if (text && !text.startsWith('·') && !text.match(/^[0-9]/) && text.length > 2 && text.length < 50) {
                            if (!biz.category && !text.includes('·')) {
                                biz.category = text;
                                break;
                            }
                        }
                    }
                    if (biz.category) break;
                }
                
                // Review count - look for spans with numbers in parentheses
                // In the feed view, review count often shows as "(123)"
                const allSpans = item.querySelectorAll('span');
                for (const sp of allSpans) {
                    const text = (sp.textContent || '').trim();
                    // Match "(123)" or "123"
                    const reviewMatch = text.match(/^\(?([0-9,]+)\)?$/);
                    if (reviewMatch) {
                        const num = parseInt(reviewMatch[1].replace(/,/g, ''));
                        if (num > 0 && num < 100000) {
                            biz.review_count = num;
                            break;
                        }
                    }
                }
                
                // Defaults
                biz.name = biz.name || '';
                biz.rating = biz.rating || 0;
                biz.review_count = biz.review_count || 0;
                biz.google_url = biz.google_url || '';
                biz.category = biz.category || '';
                biz.address = '';
                biz.phone = '';
                biz.website = '';
                biz.place_id = '';
                
                if (biz.name && biz.google_url) {
                    results.push(biz);
                }
            } catch (e) {
                continue;
            }
        }
        
        return results;
    }"""
    
    businesses = await page.evaluate(js_extract)
    businesses = businesses[:limit]
    
    for i, biz in enumerate(businesses[:5]):
        print(f"[Finder] {i+1}. {biz['name']} - {biz['rating']} ({biz['review_count']} reviews)")
    if len(businesses) > 5:
        print(f"[Finder] ... and {len(businesses) - 5} more")
    
    return businesses


async def _enrich_with_details(page, businesses, max_detail=10):
    """Click into each place to get review count, website, phone, address."""
    print(f"[Finder] Enriching top {min(max_detail, len(businesses))} businesses with details...")
    
    enriched = []
    
    for i, biz in enumerate(businesses[:max_detail]):
        url = biz.get('google_url', '')
        if not url:
            enriched.append(biz)
            continue
        
        print(f"[Finder] [{i+1}/{min(max_detail, len(businesses))}] Opening: {biz['name']}")
        
        try:
            # Navigate to the place page
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Extract details from the place page
            details = await page.evaluate(r"""() => {
                const result = {};
                
                // Review count from F7nice or aria-label
                const f7 = document.querySelector('div.F7nice');
                if (f7) {
                    const text = f7.innerText || '';
                    const match = text.match(/\(?([0-9,]+)\)?/);
                    if (match) {
                        result.review_count = parseInt(match[1].replace(/,/g, ''));
                    }
                }
                
                // Also check aria-labels on buttons
                if (!result.review_count) {
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const aria = btn.getAttribute('aria-label') || '';
                        if (aria.includes('review') || aria.includes(' avis')) {
                            const m = aria.match(/([0-9,]+)\s*(?:review|avis)/i);
                            if (m) {
                                result.review_count = parseInt(m[1].replace(/,/g, ''));
                                break;
                            }
                        }
                    }
                }
                
                // Phone
                const phoneBtn = document.querySelector('button[data-item-id*="phone"] div.Io6YTe');
                if (phoneBtn) {
                    result.phone = phoneBtn.textContent || '';
                }
                if (!result.phone) {
                    const phoneSel = document.querySelector('button[data-item-id*="phone"]');
                    if (phoneSel) {
                        result.phone = phoneSel.textContent || '';
                    }
                }
                
                // Website
                const websiteBtn = document.querySelector('a[data-item-id*="authority"] div.Io6YTe');
                if (websiteBtn) {
                    result.website = websiteBtn.textContent || '';
                }
                if (!result.website) {
                    const webLink = document.querySelector('a[data-item-id*="authority"]');
                    if (webLink) {
                        result.website = webLink.href || '';
                    }
                }
                
                // Address
                const addrBtn = document.querySelector('button[data-item-id*="address"] div.Io6YTe');
                if (addrBtn) {
                    result.address = addrBtn.textContent || '';
                }
                if (!result.address) {
                    const addrSel = document.querySelector('div.Io6YTe[data-tooltip*="address"]');
                    if (addrSel) {
                        result.address = addrSel.textContent || '';
                    }
                }
                
                return result;
            }""")
            
            # Update business with details
            if details.get('review_count'):
                biz['review_count'] = details['review_count']
            if details.get('phone'):
                biz['phone'] = details['phone']
            if details.get('website'):
                biz['website'] = details['website']
            if details.get('address'):
                biz['address'] = details['address']
            
            print(f"[Finder]   -> Reviews: {biz['review_count']}, Phone: {biz.get('phone', 'N/A')}, Website: {bool(biz.get('website'))}")
            
        except Exception as e:
            print(f"[Finder]   -> Error: {e}")
        
        enriched.append(biz)
        
        # Add remaining businesses without enrichment
        for remaining in businesses[max_detail:]:
            enriched.append(remaining)
        
        # Avoid duplicate remaining
        if i == max_detail - 1:
            break
    
    # Deduplicate by name
    seen = set()
    unique = []
    for b in enriched:
        if b['name'] not in seen:
            seen.add(b['name'])
            unique.append(b)
    
    return unique


def find_businesses(city, business_type, limit=50, api_key=None):
    """Main entry point."""
    return search_google_maps(city, business_type, limit)


if __name__ == "__main__":
    results = find_businesses("Dubai", "dental clinic", 10)
    print(f"\nResults: {len(results)}")
    for r in results:
        print(f"  - {r['name']} ({r['rating']}, {r['review_count']} reviews)")
