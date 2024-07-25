import logging
from robocorp.tasks import task
from RPA.Robocorp.WorkItems import WorkItems
from objects import BrowserControl
from objects import ExcelControl
from SeleniumLibrary.errors import ElementNotFound

@task  
def main():
    # Main function to perform the news scraping task.
    scraper = BrowserControl()
    try:
        # Get work items.
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

    except ElementNotFound as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logging.info("Finished execution")
        scraper.close_browser()

if __name__ == "__main__":
    main()