import argparse
import html
import os
import re
import time
import urllib.request

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def get_competition_slug(link):
    """Extract competition slug from Kaggle URL."""
    match = re.search(r"kaggle\.com/(?:competitions|c)/([^/]+)", link)
    if match:
        return match.group(1)
    return None


def format_yaml_value(value):
    """Format a value with double quotes."""
    if value is None:
        return ""
    return f'"{value}"'


def format_competition_yaml(comp, indent="  "):
    """Format a competition entry with custom YAML style (unquoted keys, quoted values)."""
    lines = []

    # Add "- number:" as first field with list syntax
    if "number" in comp:
        lines.append(f"{indent}- number: {format_yaml_value(comp['number'])}")
        field_indent = indent + "  "  # Extra indent for subsequent fields
    else:
        field_indent = indent

    # Add all other simple fields in order
    for key in [
        "title",
        "desc",
        "kind",
        "prize",
        "team",
        "metric",
        "link",
        "image",
        "year",
        "isHot",
        "done",
    ]:
        if key in comp:
            lines.append(f"{field_indent}{key}: {format_yaml_value(comp[key])}")

    # Add solutions
    if "solutions" in comp:
        if comp["solutions"]:
            lines.append(f"{field_indent}solutions:")
            for sol in comp["solutions"]:
                lines.append(
                    f"{field_indent}  - rank: {format_yaml_value(sol.get('rank', ''))}"
                )
                lines.append(
                    f"{field_indent}    link: {format_yaml_value(sol.get('link', ''))}"
                )
                lines.append(
                    f"{field_indent}    kind: {format_yaml_value(sol.get('kind', ''))}"
                )
        else:
            lines.append(f"{field_indent}solutions:")

    return "\n".join(lines)


def create_driver():
    """Create a headless Chrome driver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    return driver


def build_competition_image_mapping(driver):
    """
    Visit the competitions listing page and build a mapping of slug -> (image_url, comp_id).
    """
    url = "https://www.kaggle.com/competitions?listOption=completed"
    print(f"  Building image mapping from: {url}")
    driver.get(url)
    time.sleep(5)

    # Scroll to load more competitions
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    page_source = driver.page_source

    # Split by competition links and find nearby image URLs
    chunks = re.split(r'href="/competitions/', page_source)
    mapping = {}

    for chunk in chunks[1:]:  # Skip first chunk (before first competition)
        slug_match = re.match(r"([a-z0-9-]+)\"", chunk)
        if slug_match:
            slug = slug_match.group(1)
            # Look for image URL in nearby content (within same card/container)
            img_match = re.search(
                r'src="(https://storage\.googleapis\.com/kaggle-competitions/kaggle/(\d+)/logos/[^"]+)"',
                chunk[:3000],
            )
            if img_match:
                img_url = img_match.group(1)
                comp_id = img_match.group(2)
                if slug not in mapping:  # Keep first match for each slug
                    mapping[slug] = (html.unescape(img_url), comp_id)

    print(f"  Found {len(mapping)} competition image mappings")
    return mapping


def download_competition_image(competition_slug, output_dir, image_mapping):
    """
    Download the image for a single competition using the pre-built mapping.
    Returns the filename if successful, None otherwise.
    """
    if competition_slug not in image_mapping:
        print(f"  No image mapping found for: {competition_slug}")
        return None

    img_url, comp_id = image_mapping[competition_slug]

    try:
        # Get file extension
        ext_match = re.search(r"\.(png|jpg|jpeg|gif|svg|webp)", img_url.lower())
        ext = ext_match.group(1) if ext_match else "png"

        filename = f"{comp_id}.{ext}"
        filepath = os.path.join(output_dir, filename)

        if not os.path.exists(filepath):
            print(f"  Downloading image: {filename}")
            urllib.request.urlretrieve(img_url, filepath)
            return filename
        else:
            print(f"  Image exists: {filename}")
            return filename
    except Exception as e:
        print(f"  Error downloading image: {e}")

    return None


def get_kaggle_solutions(driver, competition_slug):
    """
    Fetch leaderboard page with Selenium and extract solution links.
    """
    solutions = []
    url = f"https://www.kaggle.com/competitions/{competition_slug}/leaderboard"

    try:
        print(f"  Loading: {url}")
        driver.get(url)

        # Wait for page to fully load
        time.sleep(10)

        # Get page source and find writeup links using regex
        page_source = driver.page_source
        writeup_pattern = (
            rf'href="(/competitions/{re.escape(competition_slug)}/writeups/[^"]+)"'
        )
        writeup_matches = re.findall(writeup_pattern, page_source)

        # Get unique writeups preserving order
        seen = set()
        unique_writeups = []
        for href in writeup_matches:
            # Use shorter /c/ URL format
            full_url = "https://www.kaggle.com" + href.replace("/competitions/", "/c/")
            if full_url not in seen:
                seen.add(full_url)
                unique_writeups.append(full_url)

        print(f"  Found {len(unique_writeups)} writeup links")

        # Extract rank from URL (e.g., "1st-place", "2nd-place")
        # Include all writeups, using URL order for those without rank pattern
        ranked_solutions = []
        unranked_solutions = []

        for href in unique_writeups:
            rank_match = re.search(r"(\d+)(?:st|nd|rd|th)-place", href)
            if rank_match:
                rank = int(rank_match.group(1))
                ranked_solutions.append(
                    {
                        "rank": str(rank),
                        "link": href,
                        "kind": "description",
                    }
                )
            else:
                unranked_solutions.append(
                    {
                        "rank": "?",
                        "link": href,
                        "kind": "description",
                    }
                )

        # Sort ranked solutions by rank
        ranked_solutions.sort(key=lambda x: int(x["rank"]))

        # Add all solutions (ranked first, then unranked)
        solutions = ranked_solutions + unranked_solutions
        print(f"  Extracted {len(solutions)} solutions")

    except Exception as e:
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()

    return solutions


def process_yaml_file(input_path, output_path=None, image_dir=None):
    """
    Process a YAML file containing Kaggle competitions and fill in solutions.
    Optionally download competition images if image_dir is provided.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        competitions = yaml.safe_load(f)

    if not competitions:
        print("No competitions found in the input file.")
        return

    print(f"Found {len(competitions)} competitions to process.\n")

    if image_dir:
        os.makedirs(image_dir, exist_ok=True)
        print(f"Images will be saved to: {image_dir}\n")

    # Create driver once for all competitions
    print("Starting browser...")
    driver = create_driver()

    # Build image mapping if we need to download images
    image_mapping = {}
    if image_dir:
        image_mapping = build_competition_image_mapping(driver)

    try:
        for i, comp in enumerate(competitions):
            title = comp.get("title", "Unknown")
            link = comp.get("link", "")
            done = comp.get("done", "false")

            print(f"[{i + 1}/{len(competitions)}] {title}")

            if done == "true":
                print("  Skipping (already done).\n")
                continue

            if not link:
                print("  Skipping (no link).\n")
                continue

            competition_slug = get_competition_slug(link)
            if not competition_slug:
                print(f"  Could not extract competition slug from: {link}\n")
                continue

            solutions = get_kaggle_solutions(driver, competition_slug)

            if solutions:
                comp["solutions"] = solutions
                comp["done"] = "true"
                print(f"  Found {len(solutions)} solutions.")
            else:
                comp["solutions"] = []
                print("  No solutions found.")

            # Download image if image_dir is provided
            if image_dir:
                download_competition_image(competition_slug, image_dir, image_mapping)

            print()  # Empty line between competitions

    finally:
        driver.quit()
        print("Browser closed.")

    # Format output using custom YAML formatter
    output_lines = []
    for comp in competitions:
        output_lines.append(format_competition_yaml(comp))

    indented_yaml = "\n".join(output_lines)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(indented_yaml)
        print(f"\nOutput saved to: {output_path}")
    else:
        print("\n--- Output YAML ---")
        print(indented_yaml)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Kaggle competition solutions from a YAML file."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Path to the input YAML file (e.g., kaggle-2026-01-01.txt)",
    )
    parser.add_argument(
        "--output",
        metavar="OUTPUT",
        help="Path to save the output file. If not specified, prints to stdout.",
    )
    parser.add_argument(
        "--images",
        metavar="DIR",
        help="Extract competition images to the specified directory (e.g., ~/Desktop/images)",
    )
    args = parser.parse_args()

    if args.input_file:
        output_path = os.path.expanduser(args.output) if args.output else None
        image_dir = os.path.expanduser(args.images) if args.images else None
        process_yaml_file(args.input_file, output_path, image_dir)
    else:
        parser.print_help()
