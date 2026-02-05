import argparse
import re
import time

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def get_competition_slug(link):
    """Extract competition slug from Kaggle URL."""
    match = re.search(r"kaggle\.com/(?:competitions|c)/([^/]+)", link)
    if match:
        return match.group(1)
    return None


def create_driver():
    """Create a headless Chrome driver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    return driver


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


def process_yaml_file(input_path, output_path=None):
    """
    Process a YAML file containing Kaggle competitions and fill in solutions.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        competitions = yaml.safe_load(f)

    if not competitions:
        print("No competitions found in the input file.")
        return

    print(f"Found {len(competitions)} competitions to process.\n")

    # Create driver once for all competitions
    print("Starting browser...")
    driver = create_driver()

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
                print(f"  Found {len(solutions)} solutions.\n")
            else:
                comp["solutions"] = []
                print("  No solutions found.\n")

    finally:
        driver.quit()
        print("Browser closed.")

    output_yaml = yaml.dump(
        competitions,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        default_style='"',
        width=1000,
    )

    # Add 2-space indentation for easy copy-paste into parent YAML
    indented_yaml = "\n".join("  " + line for line in output_yaml.splitlines())

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
        help="Path to the input YAML file (e.g., kaggle-2026-01-01.txt)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to save the output file. If not specified, prints to stdout.",
    )
    args = parser.parse_args()
    process_yaml_file(args.input_file, args.output)
