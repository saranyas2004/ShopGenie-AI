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
# GEMINI SETUP
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)

MODEL = "gemini-3.5-flash"


# ============================================================
# SEARCH PRODUCT IMAGES USING SERPER
# ============================================================

def get_product_images(product_name):

    url = "https://google.serper.dev/images"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": f'"{product_name}" official product',
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

        image_urls = []

        # Avoid irrelevant images
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

            combined_text = title + " " + source

            # Skip irrelevant images
            if any(
                word in combined_text
                for word in bad_words
            ):
                continue

            # Add main image
            if image_url:

                if image_url not in image_urls:
                    image_urls.append(image_url)

            # Add thumbnail
            if thumbnail_url:

                if thumbnail_url not in image_urls:
                    image_urls.append(thumbnail_url)

            # Maximum 6 images
            if len(image_urls) >= 6:
                break

        print(
            f"Found {len(image_urls)} images for {product_name}"
        )

        return image_urls

    except Exception as e:

        print(
            "Image search error:",
            e
        )

        return []


# ============================================================
# SEARCH PRODUCT LINK USING SERPER
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

    # Preferred shopping / official websites
    preferred_domains = [
        "amazon.in",
        "flipkart.com",
        "croma.com",
        "reliancedigital.in",
        "vijaysales.com",
        "lenovo.com",
        "hp.com",
        "acer.com",
        "asus.com",
        "dell.com",
        "samsung.com",
        "boat-lifestyle.com",
        "jbl.com"
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

        # ----------------------------------------------------
        # Prefer shopping websites
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Fallback to first Google result
        # ----------------------------------------------------

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
# GENERATE AI RECOMMENDATIONS
# ============================================================

def generate_recommendations(
    prompt,
    category,
    budget
):

    ai_prompt = f"""
You are ShopGenie, an AI shopping recommendation assistant.

USER REQUIREMENT:
{prompt}

CATEGORY:
{category}

MAXIMUM BUDGET:
₹{budget}

Recommend exactly 3 REAL products.

IMPORTANT RULES:

1. Products must actually exist.
2. Give specific product model names.
3. Respect the user's maximum budget.
4. Prefer products available in India.
5. Do not invent product names.
6. Do not recommend unrelated products.
7. Return exactly 3 products.
8. Match score must be between 0 and 100.
9. Keep descriptions short.
10. Keep the reason short.
11. Use realistic Indian prices.
12. The product should match the user's category and requirements.

Return ONLY valid JSON.

Do not use markdown.
Do not use ```json.
Do not add explanations outside the JSON.

Use this exact structure:

{{
    "recommendations": [
        {{
            "name": "Real product model",
            "price": "₹59,990",
            "description": "Short product description",
            "why": "Why ShopGenie recommends this product",
            "match": 95
        }},
        {{
            "name": "Real product model",
            "price": "₹61,990",
            "description": "Short product description",
            "why": "Why ShopGenie recommends this product",
            "match": 92
        }},
        {{
            "name": "Real product model",
            "price": "₹54,990",
            "description": "Short product description",
            "why": "Why ShopGenie recommends this product",
            "match": 89
        }}
    ]
}}
"""

    # Try Gemini up to 3 times
    for attempt in range(3):

        try:

            print(
                f"Calling Gemini... attempt {attempt + 1}"
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=ai_prompt
            )

            text = response.text.strip()

            # ------------------------------------------------
            # Remove Markdown code fences if Gemini adds them
            # ------------------------------------------------

            if text.startswith("```"):

                text = (
                    text
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            # ------------------------------------------------
            # Convert JSON text into Python dictionary
            # ------------------------------------------------

            data = json.loads(text)

            recommendations = data.get(
                "recommendations",
                []
            )

            # ------------------------------------------------
            # Make sure we received 3 products
            # ------------------------------------------------

            if len(recommendations) >= 3:

                return recommendations[:3]

            raise ValueError(
                "Gemini did not return 3 products."
            )

        except Exception as e:

            print(
                f"Gemini attempt {attempt + 1} failed:",
                e
            )

            if attempt < 2:

                time.sleep(3)

    raise Exception(
        "Gemini could not generate recommendations."
    )


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# RECOMMENDATION PAGE
# ============================================================

@app.route(
    "/recommend",
    methods=["POST"]
)
def recommend():

    # --------------------------------------------------------
    # Get form values
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Validate prompt
    # --------------------------------------------------------

    if not prompt:

        return render_template(
            "results.html",
            products=[],
            prompt="",
            category=category,
            budget=budget,
            error="Please describe what you are looking for."
        )


    # --------------------------------------------------------
    # Validate budget
    # --------------------------------------------------------

    if not budget:

        budget = "70000"


    # Remove commas from budget
    clean_budget = budget.replace(
        ",",
        ""
    )


    # --------------------------------------------------------
    # Generate recommendations
    # --------------------------------------------------------

    try:

        products = generate_recommendations(
            prompt,
            category,
            clean_budget
        )


        # ====================================================
        # GET IMAGES AND PRODUCT LINKS
        # ====================================================

        for product in products:

            product_name = product.get(
                "name",
                ""
            ).strip()

            print(
                "\nProcessing:",
                product_name
            )


            # ------------------------------------------------
            # IMAGE SEARCH
            # ------------------------------------------------

            image_urls = get_product_images(
                product_name
            )

            if image_urls:

                product["image"] = image_urls[0]

                # Store all images
                product["image_urls"] = image_urls

            else:

                product["image"] = None

                product["image_urls"] = []


            # ------------------------------------------------
            # PRODUCT LINK
            # ------------------------------------------------

            product["url"] = get_product_link(
                product_name
            )


            # ------------------------------------------------
            # FALLBACK PRODUCT LINK
            # ------------------------------------------------

            if not product["url"]:

                product["url"] = (
                    "https://www.google.com/search?q="
                    + requests.utils.quote(
                        product_name + " buy India"
                    )
                )


            # ------------------------------------------------
            # MATCH SCORE
            # ------------------------------------------------

            if "match" not in product:

                if "match_score" in product:

                    product["match"] = product[
                        "match_score"
                    ]

                else:

                    product["match"] = 0


            # ------------------------------------------------
            # Make sure match is a valid number
            # ------------------------------------------------

            try:

                product["match"] = int(
                    product["match"]
                )

            except:

                product["match"] = 0


            # Keep match between 0 and 100

            product["match"] = max(
                0,
                min(
                    100,
                    product["match"]
                )
            )


        # ====================================================
        # DISPLAY RESULTS
        # ====================================================

        return render_template(
            "results.html",
            products=products,
            prompt=prompt,
            category=category,
            budget=budget,
            error=None
        )


    # ========================================================
    # ERROR HANDLING
    # ========================================================

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
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )