import time

import yaml  # Used for clean printing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def get_kaggle_solutions(leaderboard_url, max_rank=50):
    """
    Scrapes a Kaggle competition leaderboard to extract solution links using Selenium
    to handle dynamically loaded content.

    Args:
        leaderboard_url (str): The full URL of the Kaggle leaderboard.
        max_rank (int): The maximum rank to scrape for solutions.

    Returns:
        list: A list of dictionaries, where each dictionary contains the
              rank, link, and kind of solution. Returns an empty list
              if the page cannot be fetched or parsed.
    """
    solutions = []
    # Setup Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument(
        "--headless"
    )  # Ensures the browser window doesn't pop up
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    driver = None
    try:
        # Step 1: Initialize the Selenium WebDriver
        # Selenium 4.6.0 and newer can manage the driver automatically.
        # This removes the need for webdriver-manager and is more reliable.
        print("Initializing browser (Selenium will automatically manage the driver)...")
        driver = webdriver.Chrome(options=chrome_options)

        # Step 2: Fetch the page
        print(f"Fetching leaderboard from: {leaderboard_url}")
        driver.get(leaderboard_url)

        # Step 3: Wait for the dynamic content (the table body) to load
        print("Waiting for leaderboard table to load...")
        wait = WebDriverWait(driver, 20)  # Wait for a maximum of 20 seconds
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
        print("Successfully loaded page content.")

        # Give it an extra moment for all rows to render, just in case
        time.sleep(2)

        # Step 4: Get the page source after JavaScript has run and parse it
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")

        leaderboard_table_body = soup.find("tbody")

        if not leaderboard_table_body:
            print(
                "Error: Could not find the leaderboard table body (tbody) even after waiting."
            )
            return []

        # Step 5: Iterate through each row in the table body
        rows = leaderboard_table_body.find_all("tr")
        print(
            f"Found {len(rows)} rows in the table. Processing up to rank {max_rank}..."
        )

        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue

            try:
                rank_str = cells[0].get_text(strip=True)
                if not rank_str.isdigit():
                    continue
                rank = int(rank_str)
            except (IndexError, ValueError):
                continue

            if rank > max_rank:
                print(f"Reached rank {rank}, stopping scrape.")
                break

            solution_link = None
            # The solution link is in the last cell
            link_cell = cells[-1]
            link_tag = link_cell.find(
                "a", href=lambda href: href and "discussion" in href
            )
            if link_tag:
                base_url = "https://www.kaggle.com"
                # Ensure we handle both relative and absolute URLs
                href = link_tag["href"]
                solution_link = href if href.startswith("http") else base_url + href

            if solution_link:
                solutions.append(
                    {"rank": str(rank), "link": solution_link, "kind": "description"}
                )

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
    finally:
        # Step 6: Always close the browser
        if driver:
            print("Closing browser.")
            driver.quit()

    return solutions


if __name__ == "__main__":
    url = "https://www.kaggle.com/c/birdclef-2025/leaderboard"
    extracted_solutions = get_kaggle_solutions(url, max_rank=50)

    if extracted_solutions:
        print("\n--- Extracted Solutions ---")
        print(yaml.dump(extracted_solutions, sort_keys=False, allow_unicode=True))
    else:
        print(
            "\nNo solutions were extracted. Please check the URL or try increasing the wait time."
        )
