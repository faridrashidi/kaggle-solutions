import os
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver


def download_images_in_a_page(page):
    url = f"https://www.kaggle.com/competitions?sortOption=recentlyClosed&page={page}"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)
    html_content = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html_content, "html.parser")
    img_tags = soup.find_all("img")
    for img in img_tags:
        src = img.get("src")
        if "https://storage.googleapis.com/kaggle-competitions/kaggle" in src:
            image_url = src
            image_name = src.split("/")[5] + ".png"
            image_path = os.path.join("/Users/farid/Desktop/kaggle", image_name)
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                with open(image_path, "wb") as f:
                    f.write(image_response.content)
            else:
                print(f"Failed to download image: {image_url}")


for page in range(3):
    download_images_in_a_page(page)
