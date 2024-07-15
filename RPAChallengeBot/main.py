import logging
import urllib3
import os
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from RPA.Browser.Selenium import Selenium
from robocorp.tasks import task
from RPA.Robocorp.WorkItems import WorkItems

# Classes definition.

class BrowserControl:
    # The class that controls the browser actions.

    def __init__(self):
        # Initialize Selenium.
        self.browser = Selenium()

    def open_browser_and_navigate(self):
        # Open the Chrome browser and navigate to the news site.
        logging.info("Opening Chrome Browser")
        self.browser.open_available_browser("https://www.latimes.com", browser_selection="chrome", maximized=True)
        logging.info("Opened Browser successfully")

    def search_phrase(self, textToSearch):
        # Find searchbar and type the searchPhrase.
        logging.info(f"Searching for: {textToSearch}")
        self.browser.click_button_when_visible("xpath:/html/body/ps-header/header/div[2]/button")
        self.browser.input_text_when_element_is_visible("xpath:/html/body/ps-header/header/div[2]/div[2]/form/label/input", textToSearch)
        self.browser.click_button_when_visible("xpath:/html/body/ps-header/header/div[2]/div[2]/form/button")

        # Sort by Newest news.
        logging.info("Sorting by Newest")
        self.browser.select_from_list_by_label("css:.select-input", 'Newest')
        logging.info("Search finished")

    def check_if_no_news(self):
        # Check if there is results for the search.
        logging.info("Looking for results of the search")
        self.browser.reload_page()
        result = True
        try:
            self.browser.wait_until_element_is_visible("css:.promo-wrapper",20)
        except Exception as e:
            logging.info("No results for the search")
            result = False
        finally:
            if result == True:
                logging.info("Found results for the search")

        return result

    def set_category(self, category):
        # Click See All and get the categories list.
        logging.info(f"Getting all available categories and adding into to the categoryList")
        self.browser.click_button_when_visible("css:.button.see-all-button")
        categoryList = self.browser.find_elements("css:.checkbox-input")

        # Search for the category on the categories list.
        logging.info(f"Starting category search for: {category.upper()}")
        for item in categoryList:
            itemText = item.text.upper().strip()
            categoryFound = False

            logging.info(f"Comparing with category: {itemText}")

            # If is the right item, select it.
            if itemText == category.upper().strip():
                logging.info(f"Category found")
                item.click()
                categoryFound = True
                break
            elif itemText == '' or itemText == None:
                logging.info(f"End of category list")
                break
            else:
                logging.info(f"Wrong category")

        # If not found, continue without it.
        if categoryFound == False:
            logging.info(f"No items for the {category} category, ignoring category selection")

    def get_news_list(self, endDate, searchPhrase):
        # Get all news and add it to an list of objects.
        newsObjectList = []

        # Iteration through the page.
        pageCounter = 0
        while True:
            # Get list of news from the page
            logging.info(f"Getting news from page {pageCounter}")
            self.browser.reload_page()
            self.browser.wait_until_element_is_visible("css:.search-results-module-results-menu")
            newsOnPage = self.browser.find_elements("css:.promo-wrapper")

            # Iteration through the newsOnPage length.
            newsCounter = 0
            while newsCounter < len(newsOnPage):
                # Check if date is valid.
                logging.info(f"Checking if the date is within the parameters")
                dateElement = self.browser.find_elements("css:.promo-timestamp")[newsCounter]
                newsDate = int(self.browser.get_element_attribute(dateElement, "data-timestamp"))
                newsDate = datetime.fromtimestamp(newsDate / 1000)
                logging.info(f"Date of current News: {newsDate}")
                logging.info(f"Date of search: {endDate}")
                if endDate <= newsDate:
                    logging.info(f"Date within parameters")
                    validNews = True
                else:
                    logging.info(f"Date out of the parameters")
                    validNews = False
                    break

                # Get values.
                logging.info(f"Getting info from news {newsCounter}")
                newsTitle = self.browser.find_elements("css:.promo-title")[newsCounter].text
                logging.info(f"News Title: {newsTitle}")
                newsDescription = self.browser.find_elements("css:.promo-description")[newsCounter].text
                logging.info(f"News Description: {newsDescription}")

                # Get image values and download it.
                newsImageURL = self.browser.find_elements("css:.image")[newsCounter]
                newsImageName = "NewsImagePG" +str(pageCounter) + "P" + str(newsCounter) + ".png"
                logging.info(f"News Image Name: {newsImageName}")
                newsImageURL = self.browser.get_element_attribute(newsImageURL, "src")
                self.download_image(newsImageURL, newsImageName)

                # Count how many times the search appears on the title and description.
                searchCount = 0
                countTitle = newsTitle.upper().count(searchPhrase.upper())
                countDescription = newsDescription.upper().count(searchPhrase.upper())
                searchCount = countTitle + countDescription
                logging.info(f"News have {searchCount} times the search phrase on it")

                # Check if currency on title and description using regex.
                CurrencyPattern = r'\$\d{1,3}(,\d{3})*(\.\d{1,2})?|\b\d{1,3}( dollars| USD)\b'
                hasCurrency = False
                match = re.search(CurrencyPattern, newsTitle)
                if match:
                    hasCurrency = True
                    logging.info(f"News have currency on its Title or description")
                match = re.search(CurrencyPattern, newsDescription)
                if match:
                    hasCurrency = True
                    logging.info(f"News have currency on its Title or description")
                if hasCurrency == False:
                    logging.info(f"News do not have currency on its Title or description")

                # Create news object and append to list.
                logging.info("Creating News Object and appending to list")
                newsObject = News(newsTitle, newsDescription, newsDate, newsImageName, searchCount, hasCurrency)
                print(newsObject)
                newsObjectList.append(newsObject)

                logging.info(f"Finished getting information from News: {newsCounter}")
                newsCounter = newsCounter + 1

            # Checking if should search other pages.
            if validNews == False:
                logging.info("No more News to get")
                break

            # Click next page to search other pages.
            pageCounter = pageCounter + 1
            nextPageCounter = str(pageCounter + 1)
            try:
                nextPage = self.browser.find_elements(f"xpath://a[@rel='nofollow' and contains(@href, 'search?') and contains(@href, {nextPageCounter})]")
                self.browser.click_element(nextPage)
            except:
                logging.info("Could not click on next page.")
                break

        return newsObjectList

    def download_image(self, imageURL, imageName):
        # Download image from the news.
        folderPath = os.path.join(os.getcwd(), 'output')
        folderPath = os.path.join(folderPath, imageName)
        print(folderPath)
        http = urllib3.PoolManager()
        response = http.request('GET', imageURL)
        with open(folderPath, 'wb') as file:
            file.write(response.data)
        logging.info(f"Image saved successfully")
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
        logging.info("Closing the browser")
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
        logging.info("Saving news to Excel file")
        data = [
            {'Title': obj.title, 'Description': obj.description, 'Date': obj.date, 'Image Name': obj.imageName, 'Number of Search Phrase on info': obj.countSearchPhrase, 'Contains Currency': obj.containsCurrency}
            for obj in newsList
        ]
        folderPath = os.path.join(os.getcwd(), 'output')
        folderPath = os.path.join(folderPath, 'FreshNews.xlsx')
        df = pd.DataFrame(data)
        df.to_excel(folderPath, index=False)
        logging.info("Saved Excel file as FreshNews.xlsx")

@task  
def main():
    # Main function to perform the news scraping task.
    scraper = BrowserControl()
    try:
        # Get work items
        workItems = WorkItems()
        workItems.get_input_work_item()
        searchPhrase = workItems.get_work_item_variable("searchPhrase", "")
        newsCategory = workItems.get_work_item_variable("newsCategory", "")
        numberOfMonths = workItems.get_work_item_variable("numberOfMonths", 0)

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
            logging.info("No category requested, following without selection")

        limitDate = scraper.calculate_date(numberOfMonths)
        newsList = scraper.get_news_list(limitDate, searchPhrase)

        excel = ExcelControl()
        excel.save_news_to_file(newsList)

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logging.info("Finished execution")
        scraper.close_browser()

if __name__ == "__main__":
    main()