import logging
import urllib3
import os
import sys
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from RPA.Browser.Selenium import Selenium

# Logger configuration.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test variables.

searchPhrase = 'Biden'
newsCategory = 'Politics'
numberOfMonths = 2

# Classes definition.

class BrowserControl:
    # The class that controls the browser actions.

    def __init__(self):
        # Initialize Selenium.
        self.browser = Selenium()

    def open_browser_and_navigate(self):
        # Open the Chrome browser and navigate to the news site.
        logger.info("Opening Chrome Browser")
        self.browser.open_browser("https://www.latimes.com", 'Chrome')
        self.browser.maximize_browser_window()
        logger.info("Opened Browser successfully")

    def search_phrase(self, textToSearch):
        # Find searchbar and type the searchPhrase.
        logger.info(f"Searching for: {textToSearch}")
        self.browser.click_button_when_visible("xpath:/html/body/ps-header/header/div[2]/button")
        self.browser.input_text_when_element_is_visible("xpath:/html/body/ps-header/header/div[2]/div[2]/form/label/input", textToSearch)
        self.browser.click_button_when_visible("xpath:/html/body/ps-header/header/div[2]/div[2]/form/button")

        # Sort by Newest news.
        logger.info("Sorting by Newest")
        self.browser.select_from_list_by_label("css:.select-input", 'Newest')
        logger.info("Search finished")

    def check_if_no_news(self):
        # Check if there is results for the search.
        logger.info("Looking for results of the search")
        self.browser.reload_page()
        result = True
        try:
            self.browser.wait_until_element_is_visible("css:.promo-wrapper",20)
        except Exception as e:
            logger.info("No results for the search")
            result = False
        finally:
            if result == True:
                logger.info("Found results for the search")

        return result

    def set_category(self, category):
        # Click See All and get the categories list.
        logger.info(f"Getting all available categories and adding into to the categoryList")
        self.browser.click_button_when_visible("css:.button.see-all-button")
        categoryList = self.browser.find_elements("css:.checkbox-input")

        # Search for the category on the categories list.
        logger.info(f"Starting category search for: {category.upper()}")
        for item in categoryList:
            itemText = item.text.upper().strip()
            categoryFound = False

            logger.info(f"Comparing with category: {itemText}")

            # If is the right item, select it.
            if itemText == category.upper().strip():
                logger.info(f"Category found")
                item.click()
                categoryFound = True
                break
            elif itemText == '' or itemText == None:
                logger.info(f"End of category list")
                break
            else:
                logger.info(f"Wrong category")

        # If not found, continue without it.
        if categoryFound == False:
            logger.info(f"No items for the {category} category, ignoring category selection")

    def get_news_list(self, endDate, searchPhrase):
        # Get all news and add it to an list of objects.
        newsObjectList = []

        # Iteration through the page.
        pageCounter = 0
        while True:
            # Get list of news from the page
            logger.info(f"Getting news from page {pageCounter}")
            self.browser.reload_page()
            self.browser.wait_until_element_is_visible("css:.search-results-module-results-menu")
            newsOnPage = self.browser.find_elements("css:.promo-wrapper")

            # Iteration through the newsOnPage length.
            newsCounter = 0
            while newsCounter < len(newsOnPage):
                # Check if date is valid.
                logger.info(f"Checking if the date is within the parameters")
                dateElement = self.browser.find_elements("css:.promo-timestamp")[newsCounter]
                newsDate = int(self.browser.get_element_attribute(dateElement, "data-timestamp"))
                newsDate = datetime.fromtimestamp(newsDate / 1000)
                logger.info(f"Date of current News: {newsDate}")
                logger.info(f"Date of search: {endDate}")
                if endDate <= newsDate:
                    logger.info(f"Date within parameters")
                    validNews = True
                else:
                    logger.info(f"Date out of the parameters")
                    validNews = False
                    break

                # Get values.
                logger.info(f"Getting info from news {newsCounter}")
                newsTitle = self.browser.find_elements("css:.promo-title")[newsCounter].text
                logger.info(f"News Title: {newsTitle}")
                newsDescription = self.browser.find_elements("css:.promo-description")[newsCounter].text
                logger.info(f"News Description: {newsDescription}")

                # Get image values and download it.
                newsImageURL = self.browser.find_elements("css:.image")[newsCounter]
                newsImageName = "NewsImagePG" +str(pageCounter) + "P" + str(newsCounter)
                logger.info(f"News Image Name: {newsImageName}")
                newsImageURL = self.browser.get_element_attribute(newsImageURL, "src")
                self.download_image(newsImageURL, newsImageName)

                # Count how many times the search appears on the title and description.
                searchCount = 0
                countTitle = newsTitle.upper().count(searchPhrase.upper())
                countDescription = newsDescription.upper().count(searchPhrase.upper())
                searchCount = countTitle + countDescription
                logger.info(f"News have {searchCount} times the search phrase on it")

                # Check if currency on title and description using regex.
                CurrencyPattern = r'\$\d{1,3}(,\d{3})*(\.\d{1,2})?|\b\d{1,3}( dollars| USD)\b'
                hasCurrency = False
                match = re.search(CurrencyPattern, newsTitle)
                if match:
                    hasCurrency = True
                    logger.info(f"News have currency on its Title or description")
                match = re.search(CurrencyPattern, newsDescription)
                if match:
                    hasCurrency = True
                    logger.info(f"News have currency on its Title or description")
                if hasCurrency == False:
                    logger.info(f"News do not have currency on its Title or description")

                # Create news object and append to list.
                logger.info("Creating News Object and appending to list")
                newsObject = News(newsTitle, newsDescription, newsDate, newsImageName, searchCount, hasCurrency)
                print(newsObject)
                newsObjectList.append(newsObject)

                logger.info(f"Finished getting information from News: {newsCounter}")
                newsCounter = newsCounter + 1

            # Checking if should search other pages.
            if validNews == False:
                logger.info("No more News to get")
                break

            # Click next page to search other pages.
            pageCounter = pageCounter + 1
            nextPageCounter = str(pageCounter + 1)
            try:
                nextPage = self.browser.find_elements(f"xpath://a[@rel='nofollow' and contains(@href, 'search?') and contains(@href, {nextPageCounter})]")
                self.browser.click_element(nextPage)
            except:
                logger.info("Could not click on next page.")
                break

        return newsObjectList

    def download_image(self, imageURL, imageName):
        # Download image from the news.
        folderPath = os.path.dirname(os.path.dirname(sys.executable)) + "\output\\" + imageName + '.png'
        print(folderPath)
        http = urllib3.PoolManager()
        response = http.request('GET', imageURL)
        with open(folderPath, 'wb') as file:
            file.write(response.data)
        logger.info(f"Image saved successfully")
        http.clear()

    def calculate_date(self, months):
        # Calculate the date for the search by months (if zero, set to 1).
        if months == 0:
            months = months +1

        currentDate = datetime.now()
        calculatedDate = currentDate - relativedelta(months=months)

        return calculatedDate

    def close_browser(self):
        # Close the browser.
        logger.info("Closing the browser")
        self.browser.close_browser()

class News:
    def __init__(self, title, description, date, imageName, countSearchPhrase, containsCurrency):
        self.title = title
        self.description = description
        self.date = date
        self.imageName = imageName
        self.countSearchPhrase = countSearchPhrase
        self.containsCurrency = containsCurrency

    def __str__(self):
        return f"Title: {self.title}\nDescription: {self.description}\nDate: {self.date}\nImage Name: {self.imageName}\nNumber of Search Phrase on info: {self.countSearchPhrase}\nContains Currency: {self.containsCurrency}"

class ExcelControl:
    def save_news_to_file(self, newsList):
        # Save the News List to the Excel file
        logger.info("Saving news to Excel file")
        data = [
            {'Title': obj.title, 'Description': obj.description, 'Date': obj.date, 'Image Name': obj.imageName, 'Number of Search Phrase on info': obj.countSearchPhrase, 'Contains Currency': obj.containsCurrency}
            for obj in newsList
        ]
        df = pd.DataFrame(data)
        df.to_excel("output\FreshNews.xlsx", index=False)
        logger.info("Saved Excel file as FreshNews.xlsx")

def main():
    # Main function to perform the news scraping task.
    scraper = BrowserControl()
    try:
        scraper.open_browser_and_navigate()
        scraper.search_phrase(searchPhrase)

        # Check if there is news for the search.
        newsFound = scraper.check_if_no_news()
        if newsFound == False:
            raise Exception(f"No news found for the searchPhrase {searchPhrase}")

        # If category is blank, continue without selecting.
        if newsCategory != '':
            scraper.set_category(newsCategory)
        else:
            logger.info("No category requested, following without selection")

        limitDate = scraper.calculate_date(numberOfMonths)
        newsList = scraper.get_news_list(limitDate, searchPhrase)

        excel = ExcelControl()
        excel.save_news_to_file(newsList)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logger.info("Finished execution")
        scraper.close_browser()

if __name__ == "__main__":
    main()