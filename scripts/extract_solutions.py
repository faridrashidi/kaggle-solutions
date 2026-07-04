import argparse
import html
import os
import re
import subprocess
import time
import urllib.request

import yaml
from bs4 import BeautifulSoup
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


DEFAULT_EXPORT_DIR = "~/Desktop/kaggle"


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


def normalize_path(path):
    """Expand user/home markers and return an absolute path."""
    if not path:
        return None
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def resolve_output_path(input_path, output_path):
    """
    Resolve the final output file path.
    If output_path points to a directory, reuse the input filename inside it.
    """
    if not output_path:
        return None

    output_path = normalize_path(output_path)

    if output_path.endswith(os.sep) or os.path.isdir(output_path):
        return os.path.join(output_path, os.path.basename(input_path))

    # Treat extensionless, non-existent paths as directories for convenience.
    if not os.path.exists(output_path):
        output_name = os.path.basename(output_path)
        if not os.path.splitext(output_name)[1]:
            return os.path.join(output_path, os.path.basename(input_path))

    return output_path


def create_driver():
    """Create a headless Chrome driver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    return driver


def is_browser_session_error(error):
    """Return True when Selenium lost the underlying browser session."""
    message = str(error).lower()
    return isinstance(error, InvalidSessionIdException) or any(
        text in message
        for text in [
            "invalid session id",
            "not connected to devtools",
            "chrome not reachable",
            "session deleted",
        ]
    )


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


def normalize_writeup_url(href):
    """Normalize Kaggle writeup links to the shorter /c/ URL format."""
    href = html.unescape(href).split("?", 1)[0].split("#", 1)[0]
    href = href.removeprefix("https://www.kaggle.com")
    return "https://www.kaggle.com" + href.replace("/competitions/", "/c/", 1)


def extract_rank_from_writeup_url(href):
    """Extract a rank from common Kaggle writeup URL title patterns."""
    rank_patterns = [
        r"(?:^|[-/])(\d+)(?:st|nd|rd|th)-private-place(?:[-/]|$)",
        r"(?:^|[-/])(\d+)(?:st|nd|rd|th)-place(?:[-/]|$)",
        r"(?:^|[-/])(\d+)(?:st|nd|rd|th)-(?:solution|writeup)(?:[-/]|$)",
        r"(?:^|[-/])lb-?(\d+)(?:[-/]|$)",
    ]

    for pattern in rank_patterns:
        rank_match = re.search(pattern, href, re.IGNORECASE)
        if rank_match:
            return str(int(rank_match.group(1)))

    return None


def extract_rank_from_leaderboard_row(link):
    """Extract the displayed leaderboard rank from the row containing a writeup link."""
    row = link.find_parent("li")
    if not row:
        return None

    first_text = next(row.stripped_strings, "")
    if not re.fullmatch(r"\d[\d,]*", first_text):
        return None

    return str(int(first_text.replace(",", "")))


def extract_solutions_from_page_source(page_source, competition_slug):
    """Extract writeup solution links and ranks from a Kaggle leaderboard page."""
    soup = BeautifulSoup(page_source, "html.parser")
    writeup_path_pattern = re.compile(
        rf"^(?:https://www\.kaggle\.com)?/competitions/{re.escape(competition_slug)}/writeups/[^?#]+"
    )

    seen = set()
    solutions = []

    for link in soup.find_all("a", href=writeup_path_pattern):
        full_url = normalize_writeup_url(link["href"])
        if full_url in seen:
            continue

        seen.add(full_url)
        rank = extract_rank_from_leaderboard_row(link)
        if rank is None:
            rank = extract_rank_from_writeup_url(full_url)

        solutions.append(
            {
                "rank": rank or "?",
                "link": full_url,
                "kind": "description",
            }
        )

    if not solutions:
        # Fallback for pages whose links are only visible in raw page data.
        writeup_pattern = (
            rf'href="(/competitions/{re.escape(competition_slug)}/writeups/[^"]+)"'
        )
        for href in re.findall(writeup_pattern, page_source):
            full_url = normalize_writeup_url(href)
            if full_url in seen:
                continue

            seen.add(full_url)
            rank = extract_rank_from_writeup_url(full_url)
            solutions.append(
                {
                    "rank": rank or "?",
                    "link": full_url,
                    "kind": "description",
                }
            )

    ranked_solutions = [
        solution for solution in solutions if re.fullmatch(r"\d+", solution["rank"])
    ]
    unranked_solutions = [
        solution for solution in solutions if not re.fullmatch(r"\d+", solution["rank"])
    ]
    ranked_solutions.sort(key=lambda solution: int(solution["rank"]))

    return ranked_solutions + unranked_solutions


def convert_png_images_to_webp(image_dir):
    """
    Convert downloaded PNG images to WebP with sharp, then delete PNGs whose
    matching WebP output was created successfully.
    """
    png_filenames = [
        filename
        for filename in os.listdir(image_dir)
        if os.path.isfile(os.path.join(image_dir, filename)) and filename.endswith(".png")
    ]

    if not png_filenames:
        print("No PNG images found to convert.")
        return

    print(f"Converting {len(png_filenames)} PNG images to WebP...")

    try:
        subprocess.run(
            [
                "sharp",
                "-i",
                "./*.png",
                "-o",
                "./{name}.webp",
                "-f",
                "webp",
                "-q",
                "75",
            ],
            cwd=image_dir,
            check=True,
        )
    except FileNotFoundError:
        print("Sharp CLI not found. PNG images were kept.")
        return
    except subprocess.CalledProcessError as e:
        print(f"Sharp conversion failed with exit code {e.returncode}. PNG images were kept.")
        return

    deleted_count = 0
    for filename in png_filenames:
        png_path = os.path.join(image_dir, filename)
        webp_path = os.path.join(
            image_dir, f"{os.path.splitext(filename)[0]}.webp"
        )

        if not os.path.exists(webp_path):
            print(f"  Keeping PNG without matching WebP: {filename}")
            continue

        try:
            os.remove(png_path)
            deleted_count += 1
        except OSError as e:
            print(f"  Could not delete PNG {filename}: {e}")

    print(f"Deleted {deleted_count} PNG images after WebP conversion.")


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

        # Get page source and extract writeup links from leaderboard rows.
        page_source = driver.page_source
        solutions = extract_solutions_from_page_source(page_source, competition_slug)
        print(f"  Found {len(solutions)} writeup links")
        print(f"  Extracted {len(solutions)} solutions")

    except Exception as e:
        if is_browser_session_error(e):
            raise

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

            solutions = []
            for attempt in range(2):
                try:
                    solutions = get_kaggle_solutions(driver, competition_slug)
                    break
                except WebDriverException as e:
                    if attempt == 0 and is_browser_session_error(e):
                        print("  Browser session lost; restarting and retrying.")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = create_driver()
                        continue

                    print(f"  Error: {e}")
                    import traceback

                    traceback.print_exc()
                    break

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

    if image_dir:
        convert_png_images_to_webp(image_dir)

    # Format output using custom YAML formatter
    output_lines = []
    for comp in competitions:
        output_lines.append(format_competition_yaml(comp))

    indented_yaml = "\n".join(output_lines)

    if output_path:
        output_path = resolve_output_path(input_path, output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
        help="Path to save the output file or directory. Defaults to ~/Desktop/kaggle using the input filename.",
    )
    parser.add_argument(
        "--images",
        metavar="DIR",
        help="Extract competition images to the specified directory. Defaults to ~/Desktop/kaggle.",
    )
    args = parser.parse_args()

    if args.input_file:
        output_path = args.output if args.output else DEFAULT_EXPORT_DIR
        image_dir = normalize_path(args.images) if args.images else normalize_path(DEFAULT_EXPORT_DIR)
        process_yaml_file(args.input_file, output_path, image_dir)
    else:
        parser.print_help()
