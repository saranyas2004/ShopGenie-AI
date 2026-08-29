import os
import json
import time
import requests

from flask import Flask, render_template, request
from dotenv import load_dotenv
from google import genai


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env")

if not SERPER_API_KEY:
    raise ValueError("SERPER_API_KEY is not set in .env")


# ============================================================
# GEMINI
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)

# This is the model that worked in your test
MODEL = "gemini-3.5-flash"


# ============================================================
# SEARCH PRODUCT IMAGES
# ============================================================

def get_product_images(product_name):

    url = "https://google.serper.dev/images"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    # Search specifically for the exact product
    search_query = (
        f'"{product_name}" '
        f'official product laptop'
    )

    payload = {
        "q": search_query,
        "num": 10
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        images = data.get("images", [])

        if not images:
            print(
                "No images found for:",
                product_name
            )
            return []


        # Words that usually indicate unrelated images
        bad_words = [
            "cat",
            "kitten",
            "dog",
            "animal",
            "meme",
            "wallpaper",
            "drawing",
            "sketch",
            "cartoon",
            "anime",
            "person",
            "people"
        ]


        image_urls = []


        for image in images:

            image_url = image.get(
                "imageUrl",
                ""
            )

            thumbnail_url = image.get(
                "thumbnailUrl",
                ""
            )

            title = image.get(
                "title",
                ""
            ).lower()

            source = image.get(
                "source",
                ""
            ).lower()


            # Skip obvious unrelated results
            combined_text = (
                title + " " + source
            )

            if any(
                word in combined_text
                for word in bad_words
            ):
                continue


            # Prefer full image URL
            if image_url:

                if image_url not in image_urls:

                    image_urls.append(
                        image_url
                    )


            # Also collect thumbnail as fallback
            if thumbnail_url:

                if thumbnail_url not in image_urls:

                    image_urls.append(
                        thumbnail_url
                    )


            # We only need a few fallbacks
            if len(image_urls) >= 6:
                break


        print(
            f"Found {len(image_urls)} image candidates "
            f"for {product_name}"
        )

        return image_urls


    except Exception as e:

        print(
            "Image search error:",
            e
        )

        return []


# ============================================================
# SEARCH PRODUCT LINK
# ============================================================

def get_product_link(product_name):

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": f'"{product_name}" buy India',
        "num": 10
    }


    preferred_domains = [
        "amazon.in",
        "flipkart.com",
        "croma.com",
        "reliancedigital.in",
        "vijaysales.com",
        "lenovo.com",
        "hp.com",
        "acer.com",
        "asus.com"
    ]


    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        results = data.get(
            "organic",
            []
        )


        # First preference:
        # shopping sites and official brands

        for result in results:

            link = result.get(
                "link",
                ""
            )

            if not link:
                continue


            for domain in preferred_domains:

                if domain in link.lower():

                    return link


        # Fallback
        if results:

            return results[0].get(
                "link"
            )


    except Exception as e:

        print(
            "Product link search error:",
            e
        )


    return None


# ============================================================
# GENERATE GEMINI RECOMMENDATIONS
# ============================================================

def generate_recommendations(
    prompt,
    category,
    budget
):

    ai_prompt = f"""
You are ShopGenie, an intelligent AI shopping
recommendation agent.

USER REQUIREMENT:
{prompt}

CATEGORY:
{category}

MAXIMUM BUDGET:
₹{budget}

Recommend exactly 3 realistic products.

IMPORTANT RULES:

1. Recommend REAL products that actually exist.
2. Respect the user's maximum budget.
3. Consider the user's requirements carefully.
4. Prefer products available in India.
5. Do not invent unrealistic product models.
6. Give specific product names.
7. Return exactly 3 products.
8. Match score must be between 0 and 100.
9. Keep descriptions short.
10. Keep the reason short.
11. If the category is laptops, recommend REAL laptop models.

Return ONLY valid JSON.

Do not use markdown.
Do not use ```json.
Do not add explanations outside the JSON.

Use exactly this structure:

{{
    "recommendations": [
        {{
            "name": "Exact real product name",
            "price": "₹60,990",
            "description": "Short product description.",
            "why": "Why this product matches.",
            "match_score": 95
        }},
        {{
            "name": "Exact real product name",
            "price": "₹65,990",
            "description": "Short product description.",
            "why": "Why this product matches.",
            "match_score": 92
        }},
        {{
            "name": "Exact real product name",
            "price": "₹59,990",
            "description": "Short product description.",
            "why": "Why this product matches.",
            "match_score": 88
        }}
    ]
}}
"""


    # ========================================================
    # GEMINI RETRY
    # ========================================================

    for attempt in range(3):

        try:

            print(
                f"Calling Gemini... "
                f"attempt {attempt + 1}"
            )


            response = client.models.generate_content(
                model=MODEL,
                contents=ai_prompt
            )


            text = response.text.strip()


            # Remove markdown if Gemini adds it
            if text.startswith("```"):

                text = (
                    text
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )


            data = json.loads(text)


            recommendations = data.get(
                "recommendations",
                []
            )


            if len(recommendations) >= 3:

                return recommendations[:3]


            raise ValueError(
                "Gemini did not return 3 products."
            )


        except Exception as e:

            print(
                f"Gemini attempt "
                f"{attempt + 1} failed:",
                e
            )


            if attempt < 2:

                time.sleep(3)


    raise Exception(
        "Gemini could not generate recommendations."
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# RECOMMEND
# ============================================================

@app.route(
    "/recommend",
    methods=["POST"]
)
def recommend():

    prompt = request.form.get(
        "prompt",
        ""
    ).strip()


    category = request.form.get(
        "category",
        "any"
    ).strip()


    budget = request.form.get(
        "budget",
        ""
    ).strip()


    # ========================================================
    # VALIDATION
    # ========================================================

    if not prompt:

        return render_template(
            "results.html",
            products=[],
            prompt="",
            category=category,
            budget=budget,
            error=(
                "Please describe what "
                "you are looking for."
            )
        )


    # ========================================================
    # GENERATE PRODUCTS
    # ========================================================

    try:

        products = generate_recommendations(
            prompt,
            category,
            budget
        )


        # ====================================================
        # IMAGES + PRODUCT LINKS
        # ====================================================

        for product in products:

            product_name = product.get(
                "name",
                ""
            ).strip()


            if product_name:

                print(
                    "\nSearching images for:",
                    product_name
                )


                # Multiple image candidates
                product["image_urls"] = (
                    get_product_images(
                        product_name
                    )
                )


                # First image
                if product["image_urls"]:

                    product["image_url"] = (
                        product["image_urls"][0]
                    )

                else:

                    product["image_url"] = None


                # Product link
                print(
                    "Searching product link for:",
                    product_name
                )


                product["product_url"] = (
                    get_product_link(
                        product_name
                    )
                )


            else:

                product["image_urls"] = []
                product["image_url"] = None
                product["product_url"] = None


        # ====================================================
        # RESULTS PAGE
        # ====================================================

        return render_template(
            "results.html",
            products=products,
            prompt=prompt,
            category=category,
            budget=budget,
            error=None
        )


    except Exception as e:

        print(
            "\nShopGenie Error:",
            e
        )


        return render_template(
            "results.html",
            products=[],
            prompt=prompt,
            category=category,
            budget=budget,
            error=(
                "Unable to generate recommendations. "
                "Please try again."
            )
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )