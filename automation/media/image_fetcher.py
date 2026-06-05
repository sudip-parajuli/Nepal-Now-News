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

        # --- Tier 4: AI Generation via Pollinations.ai ---
        if len(paths) < 3:
            needed = 4 - len(paths)
            print(f"All image sources failed. Generating {needed} AI image(s) via Pollinations.ai...")
            ai_prompt = topic_context or (unique_queries[0] if unique_queries else "deep space cosmos")
            ai_paths = self._generate_pollinations_images(ai_prompt, base_filename, count=needed)
            paths.extend(ai_paths)

        # --- Tier 5: PIL Gradient (100% reliable, no network) ---
        if not paths:
            print("All network image sources failed. Generating gradient backgrounds locally...")
            gradient_paths = self._generate_gradient_backgrounds(base_filename, count=min(4, images_needed))
            paths.extend(gradient_paths)

        if not paths:
            print("CRITICAL: All image fetch tiers failed. Video will use solid color background.")

        return paths

    def _simplify_query(self, query: str, topic_context: str = None) -> str:
        """Strip down a verbose query to 2-3 core keywords for Wikimedia/NASA searches."""
        # Only use topic keywords as fallback if query is None or very short (under 5 chars)
        if not query or len(query.strip()) < 5:
            q = topic_context if topic_context else "science astronomy"
        else:
            q = query

        # Remove quality modifiers and news-speak
        noise = ["4k", "cinematic", "close up", "macro", "science photo", "photo",
                 "hd", "ultra", "high quality", "4 k", "detailed", "stunning", "-watermark", "-stock"]
        q = q.lower()
        for n in noise:
            q = q.replace(n, "")
        # Keep only meaningful words (length > 3 or digit)
        words = [w for w in q.split() if len(w) > 3 or w.isdigit()]
        # Reject literal 'none' keyword
        words = [w for w in words if w != "none"]
        if not words:
            fallback_src = topic_context or "science astronomy"
            words = [w for w in fallback_src.lower().split() if len(w) > 3 or w.isdigit()]

        return " ".join(words[:4])

    def _search_ddg_only(self, query: str, max_results: int = 20) -> list:
        """DDG-only search with clean short query, client-side filtering and score-based sorting."""
        # Clean and truncate query to 60 characters max, removing negative keyword suffix
        search_query = query[:60]

        for attempt in range(3):
            try:
                # Add 2-second sleep between retries
                if attempt > 0:
                    time.sleep(2)

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
                                     "interview", "talking", "portrait", "cartoon",
                                     "animation", "anime", "animated", "movie",
                                     "horse", "animal", "pet", "creature", "character"]
                        scored_results = []
                        for r in results:
                            url = r.get('image', '').lower()
                            title = r.get('title', '').lower()
                            
                            # Filter client-side
                            if any(f in url for f in forbidden) or any(f in title for f in forbidden):
                                continue
                            
                            # Reject images under 400x300
                            try:
                                w = int(r.get('width', 0))
                                h = int(r.get('height', 0))
                                if w > 0 and h > 0 and (w < 400 or h < 300):
                                    continue
                            except ValueError:
                                pass
                                
                            ext = url.split('.')[-1].split('?')[0]
                            if ext in ['jpg', 'jpeg', 'png', 'webp']:
                                # Score-based prioritizing
                                score = 0
                                prefer_keywords = ['nasa', 'esa', 'wikimedia', 'noaa', 'space', 'astronomy']
                                if any(pk in url for pk in prefer_keywords):
                                    score += 10
                                scored_results.append((score, r['image']))
                        
                        # Sort by score descending, keeping highest scored first
                        scored_results.sort(key=lambda x: x[0], reverse=True)
                        filtered = [item[1] for item in scored_results]
                        return filtered[:max_results]
                    return []
            except Exception as e:
                err_str = str(e)
                print(f"DDG Search error for '{query}' (Attempt {attempt+1}/3): {err_str[:200]}")
                if "403" in err_str or "429" in err_str or "ratelimit" in err_str.lower() or "forbidden" in err_str.lower():
                    print("DDG rate-limited. Skipping remaining retries for this query.")
                    return []
                time.sleep(3 * (attempt + 1))
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
        """Generate images via Pollinations.ai (free, no API key required).
        Tries two URL variants per image (flux-schnell model then default) to maximise
        the chance of success when one Pollinations endpoint is rate-limited.
        """
        paths = []
        clean_prompt = re.sub(r'[^a-zA-Z0-9 ]', ' ', prompt).strip()
        full_prompt = f"cinematic 4k photo of {clean_prompt}, deep space, photorealistic, no people"
        encoded = requests.utils.quote(full_prompt)
        for i in range(count):
            seed = random.randint(1000, 999999)
            filename = f"{base_filename}_{len(paths)}_ai.jpg"
            print(f"Generating AI image {i+1}/{count} via Pollinations.ai (seed={seed})...")
            # Try two URL variants — model=flux-schnell first (faster), then bare default
            candidate_urls = [
                f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&seed={seed}&nologo=true&model=flux-schnell",
                f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&seed={seed}&nologo=true",
            ]
            path = None
            for url in candidate_urls:
                path = self._download_image(url, filename)
                if path:
                    break
                time.sleep(1)
            if path:
                paths.append(path)
            else:
                print(f"Pollinations.ai image {i+1} download failed (both variants).")
            time.sleep(2)
        print(f"Pollinations.ai: generated {len(paths)}/{count} image(s).")
        return paths

    def _generate_gradient_backgrounds(self, base_filename: str, count: int = 4) -> list:
        """Generate cinematic gradient images using only PIL — no network required.
        This is the final guaranteed fallback so the video always has a real background.
        """
        from PIL import Image as PilImage, ImageDraw, ImageFilter
        paths = []
        # Science-themed colour palettes: (top, mid, bottom)
        palettes = [
            ((5, 0, 30),   (0, 30, 80),   (0, 80, 150)),   # Deep-space blue
            ((10, 0, 40),  (40, 0, 80),   (80, 20, 100)),   # Purple nebula
            ((0, 15, 30),  (0, 50, 80),   (0, 100, 120)),   # Teal ocean
            ((20, 5, 0),   (60, 20, 0),   (100, 40, 10)),   # Amber star
            ((0, 20, 20),  (0, 60, 60),   (0, 120, 100)),   # Emerald aurora
            ((15, 0, 20),  (50, 0, 60),   (90, 10, 80)),    # Magenta cosmos
        ]
        for i in range(count):
            top, mid, bot = palettes[i % len(palettes)]
            try:
                img = PilImage.new('RGB', (1280, 720))
                draw = ImageDraw.Draw(img)
                for y in range(720):
                    t = y / 719.0
                    if t < 0.5:
                        s = t / 0.5
                        r = int(top[0] + (mid[0] - top[0]) * s)
                        g = int(top[1] + (mid[1] - top[1]) * s)
                        b = int(top[2] + (mid[2] - top[2]) * s)
                    else:
                        s = (t - 0.5) / 0.5
                        r = int(mid[0] + (bot[0] - mid[0]) * s)
                        g = int(mid[1] + (bot[1] - mid[1]) * s)
                        b = int(mid[2] + (bot[2] - mid[2]) * s)
                    draw.line([(0, y), (1279, y)], fill=(r, g, b))
                # Slight blur for a soft cinematic feel
                img = img.filter(ImageFilter.GaussianBlur(radius=3))
                filename = f"{base_filename}_{i}_grad.jpg"
                save_path = os.path.join(self.download_dir, filename)
                img.save(save_path, "JPEG", quality=85)
                paths.append(save_path)
            except Exception as e:
                print(f"Gradient image {i+1} error: {e}")
        if paths:
            print(f"Generated {len(paths)} gradient background(s) locally.")
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
                "gsrsearch": f"filetype:bitmap -person -portrait -cartoon -animal -movie {clean_query}",
                "gsrlimit": max_results * 2,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
            }
            headers = {'User-Agent': 'ScienceFactsBot/1.0 (contact@example.com)'}
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            # Guard against empty/non-JSON response bodies
            raw = response.text.strip()
            if not raw:
                print(f"Wikimedia Search Error: empty response for '{clean_query}'")
                return []
            
            try:
                data = response.json()
            except Exception as json_err:
                print(f"Wikimedia Search Error: non-JSON response for '{clean_query}': {json_err}")
                return []

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
        """Download a single image URL and validate it with PIL.
        Key fixes vs. original:
        - Proper full Chrome User-Agent (Wikimedia / CDNs reject truncated UAs)
        - Wikimedia-specific Referer header (required by their CDN policy)
        - Explicit logging for non-200 responses (was silent before, hiding failures)
        """
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        is_wikimedia = "wikimedia.org" in url or "wikipedia.org" in url
        headers = {
            # Full, valid Chrome UA — truncated UAs are rejected by Wikimedia CDN
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
        }
        if is_wikimedia:
            # Wikimedia CDN requires a Referer from their own domain
            headers['Referer'] = 'https://commons.wikimedia.org/'
        try:
            # Pollinations.ai can take 30-90s to generate an image on first request
            dl_timeout = 90 if "pollinations.ai" in url else 25
            response = requests.get(url, timeout=dl_timeout, headers=headers)

            # ── Log non-200 responses explicitly (was silent before) ──────────
            if response.status_code != 200:
                short_url = url.encode('ascii', 'ignore').decode('ascii')[:90]
                print(f"Download HTTP {response.status_code}: {short_url}")
                return None

            if len(response.content) <= 1000:
                print(f"Download too small ({len(response.content)}B), skipping.")
                return None

            with open(save_path, 'wb') as f:
                f.write(response.content)

            # VALIDATE IMAGE
            try:
                from PIL import Image
                with Image.open(save_path) as img:
                    img.verify()  # Raises on corrupt/truncated files
                return save_path
            except Exception as e:
                clean_url = url.encode('ascii', 'ignore').decode('ascii')
                clean_e = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"Invalid image ({clean_url[:70]}): {clean_e}")
                try:
                    os.remove(save_path)
                except OSError:
                    pass
                return None
        except Exception as e:
            clean_url = url.encode('ascii', 'ignore').decode('ascii')
            clean_e = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"Download Error ({clean_url[:70]}): {clean_e}")
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
