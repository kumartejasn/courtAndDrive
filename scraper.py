import asyncio
from playwright.async_api import async_playwright
import base64


CAPTCHA_IMAGE_SELECTOR = "captcha_image"
CASE_TYPE_SELECTOR = "#case_type_code"
CASE_NUMBER_SELECTOR = "#search_case_no"
CASE_YEAR_SELECTOR = "#search_case_year"
CAPTCHA_TEXT_SELECTOR = "#captcha"
SUBMIT_BUTTON_SELECTOR = "#search_button_top"
RESULT_TABLE_SELECTOR = ".result_table" 

async def get_captcha_and_session():
   
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    
    
    await page.goto("https://districts.ecourts.gov.in/faridabad/case-status")

    
    await page.wait_for_selector(CAPTCHA_IMAGE_SELECTOR, state="visible")
    captcha_element = await page.query_selector(CAPTCHA_IMAGE_SELECTOR)
    
    
    captcha_screenshot_bytes = await captcha_element.screenshot()
    captcha_base64 = base64.b64encode(captcha_screenshot_bytes).decode('utf-8')
    
    return {"page": page, "browser": browser, "playwright": playwright, "captcha_image": captcha_base64}


async def fetch_case_data(page, case_details):
    """
    Fills the form with case details and the user-provided CAPTCHA, then scrapes the results.
    """
    try:
        
        await page.select_option(CASE_TYPE_SELECTOR, value=case_details["type"])
        await page.fill(CASE_NUMBER_SELECTOR, case_details["number"])
        await page.select_option(CASE_YEAR_SELECTOR, value=case_details["year"])
        await page.fill(CAPTCHA_TEXT_SELECTOR, case_details["captcha_text"])

        
        await page.click(SUBMIT_BUTTON_SELECTOR)

        
        await page.wait_for_selector(f"{RESULT_TABLE_SELECTOR}, .error_msg", timeout=15000) # 15-second timeout

        
        error_element = await page.query_selector(".error_msg")
        if error_element:
            error_text = await error_element.inner_text()
            if "invalid captcha" in error_text.lower():
                return {"error": "Invalid CAPTCHA. Please try again."}
            return {"error": error_text}

        
        raw_html = await page.content()
        
        
        petitioner = await page.locator("text=Petitioner and Advocate").first.inner_text()
        respondent = await page.locator("text=Respondent and Advocate").first.inner_text()
        next_hearing = await page.locator("text=Next Hearing Date").first.inner_text()
        
        parsed_data = {
            "parties": f"{petitioner} vs {respondent}",
            "next_hearing_date": next_hearing.split(':')[-1].strip(),
            "filing_date": "Example: 01-01-2023", 
            "pdf_links": ["https://districts.ecourts.gov.in/some-order.pdf"] 
        }
        
        return {"data": parsed_data, "html": raw_html}

    except asyncio.TimeoutError:
        return {"error": "Page timeout. The court website might be slow or down."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": "An unexpected error occurred during scraping."}