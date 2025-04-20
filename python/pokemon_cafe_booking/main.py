import calendar
import os
import re
from datetime import datetime

from pydantic import BaseModel
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from python.pokemon_cafe_booking import definition


class BookingTimetable(BaseModel):
    seat: str
    start_from: str
    row: int
    col: int


def parse_calendar_text(text: str) -> list[datetime]:
    # Get Current month
    current_month_pattern = r"\d{4}年\d{1,2}月"

    # Split the string using regex
    current_month: str = re.findall(current_month_pattern, text)[0]
    year_month = current_month.replace("年", "/").replace("月", "").split("/")
    year = int(year_month[0])
    month = int(year_month[1])

    # Regex pattern to split after the Saturday
    after_sat = r"土[\s\S]*?"
    day_of_month: str = re.split(after_sat, text, 1)[1]

    # Split based on the pattern that matches the digit "1"
    split_string = re.split(
        r"(?<=\b1\b)",
        day_of_month,
    )
    first_day_of_month: list[str] = split_string[0].splitlines()
    rest_of_days: list[str] = split_string[1].splitlines()
    rest_of_days = rest_of_days[0:-1]  # Remove the "1" at the end

    all_days = first_day_of_month + rest_of_days
    all_days = list(filter(lambda x: x != "", all_days))

    if len(all_days) == 0:
        return []

    # Fill available days in the current month
    is_available_flags = [False] * 31
    for i in range(len(all_days)):
        if all_days[i].isnumeric():
            n_day = int(all_days[i])
            if all_days[min(i + 1, len(all_days) - 1)] in ["満席", "未開放"]:
                continue

            if n_day > 31:
                continue

            is_available_flags[n_day - 1] = True

    availabilities = []
    day_range = calendar.monthrange(year, month)[1]
    for i in range(day_range):
        if is_available_flags[i]:
            availabilities.append(
                datetime(
                    year=year,
                    month=month,
                    day=i + 1,
                )
            )

    return availabilities


def get_timetable(text: str) -> list[BookingTimetable]:
    timetable_text = text.splitlines()
    timetable_text_sz = len(timetable_text)

    index = 0
    res = []
    for i in range(timetable_text_sz):
        if re.search(r"[A-Z]席", timetable_text[i]) is not None:
            end_index = min(i + 4, timetable_text_sz - 1)
            timeslot = timetable_text[i:end_index]
            if timeslot[2] != "満席":
                row = index // 4
                col = index % 4
                res.append(
                    BookingTimetable(
                        seat=timeslot[0],
                        start_from=timeslot[1].replace("~", ""),
                        row=row + 1,
                        col=col + 1,
                    )
                )
            index += 1

    return res


def create_booking(location: str, n_guests: int) -> None:
    if location == "Tokyo":
        website = "https://reserve.pokemon-cafe.jp/"
    elif location == "Osaka":
        website = "https://osaka.pokemon-cafe.jp/"

    chrome_options = Options()
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("detach", True)
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    service = Service(
        executable_path=os.path.join(
            definition.ROOT_DIR,
            "chromedriver.exe",
        )
    )
    driver = webdriver.Chrome(options=chrome_options, service=service)
    driver.get(website)
    try:
        # Step 1: Agree to terms and conditions
        driver.find_element(
            By.XPATH,
            "//*[@class='agreeChecked']",
        ).click()
        driver.find_element(
            By.XPATH,
            "//*[@class='button']",
        ).click()

        # Step 2: Make reservation button
        make_reservation_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@class='button arrow-down']")
            )
        )
        make_reservation_button.click()

        # Step 3: Fill in number of people
        select = Select(driver.find_element(By.NAME, "guest"))
        select.select_by_index(n_guests)

        # Step 4: Reads calendar and find available dates
        calendar_element = driver.find_element(
            By.XPATH,
            "//*[@id='step2-form']/div",
        )
        # First time
        available_dates = parse_calendar_text(calendar_element.text)
        # If no available dates, try next month
        if len(available_dates) == 0:
            driver.find_element(
                By.XPATH,
                "//*[contains(text(), '次の月を見る')]",
            ).click()
            calendar_element = driver.find_element(
                By.XPATH,
                "//*[@id='step2-form']/div",
            )
            available_dates = parse_calendar_text(calendar_element.text)

        # print(available_dates)
        # Second time if nothing found, there's no available date at the moment
        if len(available_dates) == 0:
            return

        # Try booking for the date
        booking_date = available_dates[0]
        driver.find_element(
            By.XPATH,
            "//*[contains(text(), " + str(booking_date.day) + ")]",
        ).click()
        driver.find_element(By.XPATH, "//*[@class='button']").click()

        timetable_element = driver.find_element(
            By.XPATH,
            "//*[@id='time_table']/tbody",
        )

        available_timetables = get_timetable(timetable_element.text)
        if len(available_timetables) == 0:
            return

        booking_time = available_timetables[0]
        print(booking_date.strftime("%Y-%m-%d"))
        print(booking_time)
        booking_timeslot_grid = driver.find_element(
            By.XPATH,
            f"//*[@id='time_table']/tbody/tr[{booking_time.row}]/td[{booking_time.col}]",  # noqa: E501
        )
        booking_timeslot_grid.click()

        contact_form = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='step3-form']"))
        )
        confirm_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@id='submit_button']"),
            )
        )
        contact_form.find_element(By.NAME, "name").send_keys("John Doe")
        contact_form.find_element(By.NAME, "name_kana").send_keys("John Doe")
        contact_form.find_element(By.NAME, "phone_number").send_keys(
            "09012345678",
        )
        contact_form.find_element(By.NAME, "email").send_keys(
            "john.doe@example.com",
        )
        print(confirm_button.is_displayed())

    except NoSuchElementException:
        pass

    except Exception as e:
        raise Exception(f"Failed to book for Tokyo: {e}")

    finally:
        print("Booking process completed.")
        # driver.quit()


def main() -> None:
    create_booking("Tokyo", 2)


if __name__ == "__main__":
    main()
