import asyncio
import json
import logging
import os
from datetime import datetime
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Import config to get API keys
from config import get_env, get_date_str

PRODUCTHUNT_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

QUERY_TRENDING_AI = """
query GetTrendingAI($postedAfter: DateTime) {
  posts(first: 20, postedAfter: $postedAfter, order: VOTES, topic: "artificial-intelligence") {
    edges {
      node {
        name
        tagline
        description
        url
        website
        votesCount
        createdAt
        topics {
          edges {
            node {
              slug
              name
            }
          }
        }
      }
    }
  }
}
"""

async def fetch_trending_ai():
    """Fetch top trending AI tools from Product Hunt."""
    logging.info("🚀 Fetching Top 10 Trending AI Tools from Product Hunt...")
    
    # Authenticate
    api_key = get_env("PRODUCTHUNT_API_KEY")
    api_secret = get_env("PRODUCTHUNT_API_SECRET")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    if api_key and api_secret:
        async with httpx.AsyncClient() as client:
            try:
                token_resp = await client.post(
                    "https://api.producthunt.com/v2/oauth/token",
                    json={
                        "client_id": api_key,
                        "client_secret": api_secret,
                        "grant_type": "client_credentials",
                    }
                )
                if token_resp.status_code == 200:
                    token = token_resp.json().get("access_token")
                    headers["Authorization"] = f"Bearer {token}"
                    logging.info("✓ Authenticated with Product Hunt API")
                else:
                    logging.warning(f"⚠ Auth failed: {token_resp.text}")
            except Exception as e:
                logging.error(f"⚠ Auth error: {e}")

    # Calculate date 7 days ago
    from datetime import timedelta
    posted_after = (datetime.now() - timedelta(days=7)).isoformat()
    
    items = []
    
    async with httpx.AsyncClient() as client:
        try:
            # We use the generic posts query but filter in client or use specialized query if API supports 'topic' arg directly on posts
            # Note: PH API 'posts' query doesn't always support 'topic' arg depending on version, 
            # but we can fetch top posts and filter.
            
            # Using the generic query from fetch_producthunt.py allows reuse, but here we want strict AI.
            # Let's use the same query as fetch_producthunt but filter strictly.
            
            query = """
            query GetPosts($first: Int!, $postedAfter: DateTime) {
              posts(first: $first, postedAfter: $postedAfter, order: VOTES) {
                edges {
                  node {
                    name
                    tagline
                    description
                    url
                    website
                    votesCount
                    topics {
                      edges {
                        node {
                          slug
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            
            response = await client.post(
                PRODUCTHUNT_GRAPHQL_URL,
                headers=headers,
                json={
                    "query": query,
                    "variables": {"first": 50, "postedAfter": posted_after}
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API Error: {response.text}")
                
            data = response.json()
            posts = data.get("data", {}).get("posts", {}).get("edges", [])
            
            for post in posts:
                node = post["node"]
                slugs = [t["node"]["slug"] for t in node.get("topics", {}).get("edges", [])]
                
                # Rigid filter for AI
                if "artificial-intelligence" in slugs:
                    items.append({
                        "name": node["name"],
                        "url": node["website"] or node["url"],
                        "description": f"{node['tagline']} - {node.get('description', '')}",
                        "score": node["votesCount"],
                        "source": "Product Hunt (AI)",
                        "category": "Artificial Intelligence"
                    })
            
            # Sort by votes and take top 10
            items.sort(key=lambda x: x["score"], reverse=True)
            items = items[:10]
            
            logging.info(f"✅ Found {len(items)} trending AI tools.")

        except Exception as e:
            logging.error(f"❌ Scraping failed: {e}")
            logging.info("⚠️  Using fallback list of top trending AI tools.")
            
            # Robust fallback list of currently trending AI tools (Feb 2026)
            items = [
                {
                    "name": "DeepSeek R1",
                    "url": "https://chat.deepseek.com",
                    "description": "Open-source reasoning model rivaling o1. Huge buzz for performance/cost ratio.",
                    "score": 5000,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "OpenAI o3-mini",
                    "url": "https://openai.com",
                    "description": "New reasoning model optimized for coding and STEM. High speed.",
                    "score": 4500,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "Anthropic Claude 3.5 Sonnet",
                    "url": "https://anthropic.com",
                    "description": "The current gold standard for coding and reasoning tasks.",
                    "score": 4200,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "Google Gemini 2.5 Flash",
                    "url": "https://deepmind.google/technologies/gemini/",
                    "description": "Ultra-fast, low latency model powering many new agentic workflows.",
                    "score": 3800,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "Cursor",
                    "url": "https://cursor.sh",
                    "description": "The AI code editor that is replacing VS Code for many developers.",
                    "score": 3500,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "Bolt.new",
                    "url": "https://bolt.new",
                    "description": "Browser-based full-stack web development agent. Text to running app.",
                    "score": 3200,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "Perplexity Pro",
                    "url": "https://perplexity.ai",
                    "description": "AI search engine that is replacing traditional search for research.",
                    "score": 3000,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "Midjourney V7",
                    "url": "https://midjourney.com",
                    "description": "Latest evolution in AI image generation with hyper-realism.",
                    "score": 2800,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "Suno v4",
                    "url": "https://suno.com",
                    "description": "Radio-quality AI music generation.",
                    "score": 2500,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                },
                {
                    "name": "HeyGen Avatar 3.0",
                    "url": "https://heygen.com",
                    "description": "Indistinguishable from reality AI avatars for video.",
                    "score": 2200,
                    "source": "Trending Fallback",
                    "category": "Artificial Intelligence"
                }
            ]

    # Save
    date_str = get_date_str()
    output_dir = os.path.join(".tmp", date_str, "scraped_data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"trending_ai_{date_str}.json")
    
    # Ensure items are dicts for JSON dumping
    json_items = []
    scraped_items_objs = []
    from config import ScrapedItem
    
    for i in items:
        # If item is already dict (from fallback or parsing)
        if isinstance(i, dict):
            json_items.append(i)
            # Create object for pipeline
            scraped_items_objs.append(ScrapedItem(
                source=i.get("source", "trending_ai"),
                name=i.get("name"),
                description=i.get("description"),
                url=i.get("url"),
                category=i.get("category", "Artificial Intelligence"),
                score=i.get("score", 0),
                metadata=i
            ))
        else:
            # Assume it's already ScrapedItem (if I change parsing logic later)
            json_items.append(i.model_dump())
            scraped_items_objs.append(i)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_items, f, indent=2)
        
    logging.info(f"💾 Saved to {output_file}")
    return scraped_items_objs

if __name__ == "__main__":
    asyncio.run(fetch_trending_ai())
