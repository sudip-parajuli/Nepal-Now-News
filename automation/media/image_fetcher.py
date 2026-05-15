import os
import requests
from duckduckgo_search import DDGS
import random
import time
import re

class ImageFetcher:
    def __init__(self, download_dir="automation/storage/temp_images"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_multi_images(self, queries: list, base_filename: str, topic_context: str = None) -> list:
        paths = []
        # Flatten and deduplicate queries
        flat_queries = []
        for q in queries:
            if isinstance(q, list): flat_queries.extend(q)
            else: flat_queries.append(q)
        unique_queries = list(dict.fromkeys(flat_queries))
        images_needed = max(len(queries), 4)  # Always try to get at least 4 images
        images_per_search = 4 if len(unique_queries) > 1 else images_needed

        # --- Tier 1: DDG (try up to 5 queries, not just 3) ---
        ddg_failed_count = 0
        for i, q in enumerate(unique_queries[:5]):
            refined_q = (q if "photo" in q.lower() else f"{q} science photo") + " -watermark -stock"
            print(f"Searching images for: {refined_q}...")
            results = self._search_ddg_only(refined_q, max_results=15)

            if results:
                ddg_failed_count = 0  # reset on success
                count = 0
                for img_url in results:
                    # Watermark filtering: skip known stock sites in URL
                    stock_sites = ["shutterstock.com", "alamy.com", "gettyimages.com", "dreamstime.com", "123rf.com", "depositphotos.com", "istockphoto.com", "vectorstock.com"]
                    if any(site in img_url.lower() for site in stock_sites):
                        continue

                    filename = f"{base_filename}_{len(paths)}.jpg"
                    path = self._download_image(img_url, filename)
                    if path:
                        paths.append(path)
                        count += 1
                    if count >= images_per_search or len(paths) >= images_needed:
                        break
            else:
                ddg_failed_count += 1
                # If DDG keeps failing (rate-limited), stop hammering it
                if ddg_failed_count >= 2:
                    print("DDG rate-limited on multiple queries. Skipping remaining DDG attempts.")
                    break

            if len(paths) >= images_needed:
                break
            time.sleep(3)  # slightly longer sleep to avoid rate limits

        # --- Tier 2: Wikimedia fallback for any shortfall ---
        if len(paths) < images_needed and unique_queries:
            # Use simplified queries (first 2 meaningful words) for Wikimedia
            wm_query = self._simplify_query(unique_queries[0], topic_context)
            print(f"Wikimedia fallback search: '{wm_query}'...")
            wm_results = self._search_wikimedia(wm_query, max_results=20)
            for img_url in wm_results:
                if len(paths) >= images_needed:
                    break
                filename = f"{base_filename}_{len(paths)}_wm.jpg"
                path = self._download_image(img_url, filename)
                if path:
                    paths.append(path)

        # --- Tier 3: NASA Image API fallback ---
        if len(paths) < images_needed and topic_context:
            print(f"NASA Image API fallback for topic: '{topic_context}'...")
            nasa_paths = self._fetch_nasa_images(
                topic_context,
                base_filename,
                count=images_needed - len(paths)
            )
            paths.extend(nasa_paths)

        # --- Tier 4: AI Generation via Pollinations.ai (GUARANTEED fallback) ---
        if len(paths) < 3:
            needed = 4 - len(paths)
            print(f"All image sources failed. Generating {needed} AI image(s) via Pollinations.ai...")
            # Use the topic or first query as the prompt
            ai_prompt = topic_context or (unique_queries[0] if unique_queries else "deep space cosmos")
            ai_paths = self._generate_pollinations_images(ai_prompt, base_filename, count=needed)
            paths.extend(ai_paths)

        if not paths:
            print("CRITICAL: All image fetch tiers failed. Video will use solid color background.")

        return paths

    def _simplify_query(self, query: str, topic_context: str = None) -> str:
        """Strip down a verbose query to 2-3 core keywords for Wikimedia/NASA searches."""
        # Remove quality modifiers and news-speak
        noise = ["4k", "cinematic", "close up", "macro", "science photo", "photo",
                 "hd", "ultra", "high quality", "4 k", "detailed", "stunning"]
        q = query.lower()
        for n in noise:
            q = q.replace(n, "")
        # Keep only meaningful words (length > 3)
        words = [w for w in q.split() if len(w) > 3]
        # Prioritize topic_context words if provided
        if topic_context:
            topic_words = [w for w in topic_context.lower().split() if len(w) > 3][:2]
            combined = topic_words + [w for w in words if w not in topic_words]
            return " ".join(combined[:3])
        return " ".join(words[:3])

    def _search_ddg_only(self, query: str, max_results: int = 20) -> list:
        """DDG-only search (no Wikimedia fallback here — handled by caller tier logic)."""
        negative_filters = "-person -face -human -man -woman -portrait -interview -talking -host -adult -child -people -character -characters -diagram -chart -graph -map -vector -text -logo"
        search_query = f"{query} {negative_filters}"

        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = ddgs.images(
                        keywords=search_query,
                        region="wt-wt",
                        safesearch="on",
                        size="large",
                        type_image="photo"
                    )
                    if results:
                        forbidden = ["diagram", "chart", "graph", "vector", "drawing",
                                     "illustration", "map", "infographic", "logo",
                                     "person", "face", "human", "man", "woman",
                                     "interview", "talking", "portrait"]
                        filtered = []
                        for r in results:
                            url = r['image'].lower()
                            title = r.get('title', '').lower()
                            if any(f in url for f in forbidden) or any(f in title for f in forbidden):
                                continue
                            if url.split('.')[-1].split('?')[0] in ['jpg', 'jpeg', 'png', 'webp']:
                                filtered.append(r['image'])
                        random.shuffle(filtered)
                        return filtered[:max_results]
                    return []
            except Exception as e:
                err_str = str(e)
                print(f"DDG Search error for '{query}' (Attempt {attempt+1}/3): {err_str[:200]}")
                if "403" in err_str or "Ratelimit" in err_str:
                    # Rate-limited — wait longer and give up sooner
                    time.sleep(10 * (attempt + 1))
                else:
                    time.sleep(5 * (attempt + 1))
                continue
        return []

    def _search_ddg(self, query: str, max_results: int = 20, topic_context: str = None) -> list:
        """Legacy wrapper: DDG with Wikimedia fallback (kept for fetch_image compatibility)."""
        results = self._search_ddg_only(query, max_results)
        if not results:
            print(f"DDG failed for '{query}'. Trying Wikimedia Fallback...")
            simplified = self._simplify_query(query, topic_context)
            return self._search_wikimedia(simplified, max_results)
        return results

    def _fetch_nasa_images(self, topic: str, base_filename: str, count: int = 3) -> list:
        """Fetch images (not videos) from NASA Image Library API."""
        paths = []
        try:
            # Use a short, simplified query
            simplified = self._simplify_query(topic)
            search_url = "https://images-api.nasa.gov/search"
            params = {"q": simplified, "media_type": "image"}
            resp = requests.get(search_url, params=params, timeout=15)
            if resp.status_code != 200:
                print(f"NASA Image API returned {resp.status_code}")
                return []
            items = resp.json().get("collection", {}).get("items", [])
            random.shuffle(items)
            for item in items:
                if len(paths) >= count:
                    break
                links = item.get("links", [])
                for link in links:
                    href = link.get("href", "")
                    if href.lower().endswith((".jpg", ".jpeg", ".png")):
                        filename = f"{base_filename}_{len(paths)}_nasa.jpg"
                        path = self._download_image(href, filename)
                        if path:
                            paths.append(path)
                            break
            print(f"NASA Image API: fetched {len(paths)} image(s) for '{simplified}'.")
        except Exception as e:
            print(f"NASA Image API error: {e}")
        return paths

    def _generate_pollinations_images(self, prompt: str, base_filename: str, count: int = 4) -> list:
        """Generate images via Pollinations.ai (free, no API key required)."""
        paths = []
        # Clean the prompt for URL safety
        clean_prompt = re.sub(r'[^a-zA-Z0-9 ]', ' ', prompt).strip()
        # Make it cinematic/scientific
        full_prompt = f"cinematic 4k photo of {clean_prompt}, deep space, photorealistic, no people"
        encoded = requests.utils.quote(full_prompt)
        for i in range(count):
            seed = random.randint(1000, 999999)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&seed={seed}&nologo=true"
            filename = f"{base_filename}_{len(paths)}_ai.jpg"
            try:
                print(f"Generating AI image {i+1}/{count} via Pollinations.ai (seed={seed})...")
                path = self._download_image(url, filename)
                if path:
                    paths.append(path)
                else:
                    print(f"Pollinations.ai image {i+1} download failed.")
                time.sleep(2)  # Be polite to the free API
            except Exception as e:
                print(f"Pollinations.ai error for image {i+1}: {e}")
        print(f"Pollinations.ai: generated {len(paths)}/{count} image(s).")
        return paths

    def _search_wikimedia(self, query: str, max_results: int = 20) -> list:
        """Search Wikimedia Commons. Always use short, simplified queries (2-3 words)."""
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            # Wikimedia needs clean, short queries — strip quality modifiers first
            clean_query = self._simplify_query(query) if len(query.split()) > 3 else query
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6,  # File namespace
                "gsrsearch": f"filetype:bitmap -person -portrait {clean_query}",
                "gsrlimit": max_results * 2,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
            }
            headers = {'User-Agent': 'ScienceFactsBot/1.0 (contact@example.com)'}
            response = requests.get(url, params=params, headers=headers, timeout=12)
            data = response.json()

            image_urls = []
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if "imageinfo" in page:
                    img_url = page["imageinfo"][0]["url"]
                    ext = img_url.lower().split('?')[0].split('.')[-1]
                    if ext in ('jpg', 'jpeg', 'png', 'webp'):
                        image_urls.append(img_url)

            random.shuffle(image_urls)
            print(f"Wikimedia found {len(image_urls)} images for '{clean_query}'.")
            return image_urls[:max_results]
        except Exception as e:
            print(f"Wikimedia Search Error: {e}")
            return []

    def _download_image(self, url: str, filename: str) -> str:
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) UserAgent'}
            # Pollinations.ai can take 30-60s to generate an image on first request
            dl_timeout = 90 if "pollinations.ai" in url else 20
            response = requests.get(url, timeout=dl_timeout, headers=headers)
            if response.status_code == 200 and len(response.content) > 1000: # Lowered min size slightly
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                # VALIDATE IMAGE
                try:
                    from PIL import Image
                    with Image.open(save_path) as img:
                        img.verify() # Check for corruption
                    return save_path
                except Exception as e:
                    print(f"Invalid image downloaded ({url}): {e}")
                    os.remove(save_path)
                    return None
        except Exception as e:
            print(f"Download Error ({url}): {e}")
        return None

    def fetch_image(self, query: str, filename: str) -> str:
        # Hybrid search
        results = self._search_ddg(query)
        # If DDG fails (and returns empty despite fallback logic above, which shouldn't happen but safe to keep)
        if not results:
             results = self._search_wikimedia(query)

        for url in results:
            path = self._download_image(url, filename)
            if path: return path
        return None
