import time
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from job.keyword import extract_keywords


def linkedin_job_scraper(keywords, location, LINKEDIN_EMAIL, LINKEDIN_PASSWORD, max_jobs=10):
    options = uc.ChromeOptions()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options)

    try:
        # 1️⃣ Login
        driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
        driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        print("✅ Login successful")
        time.sleep(3)
        

        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
        driver.get(search_url)
        print(f"🔍 Searching: {keywords} in {location}")
        time.sleep(3)

        jobs=[]
        wait = WebDriverWait(driver, 10)
        try:
                job_cards = wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".jobs-search__results-list li")
                ))
                print(f"✅ Found {len(job_cards)} job cards")
        except TimeoutException:
                print("⚠️ No job cards found → either LinkedIn blocked us, or no results.")
                return []
        for index, card in enumerate(job_cards[:max_jobs]):
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", card)
                time.sleep(0.5)

                try:
                    card.click()
                except:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                    card.click()
                time.sleep(1.5)

                retries = 3
                for attempt in range(retries):
                    try:
                        print(f"🔄 Attempt {attempt+1} to fetch job details for job {index+1}")
                        title = driver.find_element(By.CSS_SELECTOR, ".topcard__title").text.strip()
                        company = driver.find_element(By.CSS_SELECTOR, ".topcard__org-name-link, .topcard__flavor").text.strip()
                        location_text = driver.find_element(By.CSS_SELECTOR, ".topcard__flavor--bullet").text.strip()
                        if title and company and location_text:
                            break
                    except:
                        time.sleep(1)
                else:
                    print(f"⚠️ Skipping job {index+1}: incomplete data")
                    continue

                try:
                    print(f"📖 Fetching full description for job {index+1}")
                    show_more_button = driver.find_element(By.CSS_SELECTOR, ".show-more-less-html__button")
                    driver.execute_script("arguments[0].click();", show_more_button)
                    time.sleep(1)
                except:
                    pass
                apply_link = None
                try:
                    apply_btn = driver.find_element(By.CSS_SELECTOR, ".jobs-apply-button a")
                    apply_link = apply_btn.get_attribute("href")
                except:
                    try:
                        apply_btn = driver.find_element(By.CSS_SELECTOR, ".jobs-apply-button button")
                        apply_link = driver.current_url  
                    except:
                        pass

                about = driver.find_element(By.CSS_SELECTOR, ".description__text, .show-more-less-html__markup").text.strip()
                url = card.find_element(By.TAG_NAME, "a").get_attribute("href")

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "about": about,
                    "url": url,
                    "apply_link": apply_link
                })
                print(f"✅ Parsed job {index+1}: {title} at {company}")

            except Exception as e:
                print(f"⚠️ Error parsing job {index+1}: {e}")

        return jobs

    finally:
        driver.quit()


