import os
import sys
import six
import pause
import argparse
import logging.config
import re
import time
from time import sleep
import random
import json
from selenium import webdriver
from dateutil import parser as date_parser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [PID %(process)d] [Thread %(thread)d] [%(levelname)s] [%(name)s] %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": [
            "console"
        ]
    }
})

LOGGER = logging.getLogger()


def run(driver, username, password, url, shoe_size, release_time=None, page_load_timeout=None):
    driver.set_page_load_timeout(page_load_timeout)

    LOGGER.info("Requesting page: " + url)
    driver.get(url)
    driver.maximize_window()
    wait_until_visible(driver, css_selector="button[data-qa='top-nav-join-or-login-button']", duration=50)
    login_btn = driver.find_elements_by_css_selector("button[data-qa='top-nav-join-or-login-button']")[0]

    # todo: 显示不出来时，需要不断重试
    login_btn.click()
    wait_until_visible(driver, css_selector="div.view-header", duration=120)

    login(driver, username, password)
    wait_until_visible(driver, xpath="//img[@data-qa='portrait-img']", duration=120)

    LOGGER.info("Waiting for page complete...")
    product_id = driver.find_element_by_name("branch:deeplink:productId").get_attribute("content")
    new_url = url + "?size=" + str(shoe_size) + "&productId=" + product_id
    driver.get(new_url)

    target_time_stamp = int(time.mktime(time.strptime(release_time, '%Y-%m-%d %H:%M:%S'))) * 1000
    keep_wait(driver, target_time_stamp=target_time_stamp, url=new_url)

    LOGGER.info("waiting for Alipay button show...")
    wait_until_clickable(driver, class_name="payment-provider-btn", duration=50)
    click_save_btn_js = 'document.getElementsByClassName("payment-provider-btn")[1].click();document.getElementsByClassName("ncss-btn-primary-dark selectable")[1].click();'
    driver.execute_script(click_save_btn_js)

    LOGGER.info('submit save')

    submit_js = 'let time = (new Date()).getTime();let expectTime ="' + str(
        release_time) + '";let expectTimeStamp = (new Date(expectTime)).getTime();let sub = expectTimeStamp - time;setTimeout(()=>{let btn = document.getElementsByClassName("ncss-btn-primary-dark selectable")[2];btn.click();}, sub);'
    driver.execute_script(submit_js)

    sleep(800)


def login(driver, username, password):
    login_js = 'const input = document.getElementsByName("verifyMobileNumber")[0];input.value = "{username}";const pw = document.getElementsByName("password")[0];pw.value ="{password}";document.getElementsByClassName("nike-unite-submit-button mobileLoginSubmit nike-unite-component")[0].children[0].click();'.format(username=username, password=password)
    LOGGER.info(login_js)
    driver.execute_script(login_js)
    LOGGER.info("Successfully logged in")


def keep_wait(driver, target_time_stamp, url):
    LOGGER.info("waiting for release time...")
    while True:
        current_time = int(time.time() * 1000)
        if (target_time_stamp - current_time) > 180000:
            driver.get(url)
            print("refresh page every min, current time:", current_time)
            sleep(60)
        else:
            LOGGER.info("ready for submit...")
            break


def wait_until_clickable(driver, xpath=None, class_name=None, el_id=None, css_selector=None, duration=10000,
                         frequency=0.1):
    if xpath:
        WebDriverWait(driver, duration, frequency).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    elif class_name:
        WebDriverWait(driver, duration, frequency).until(EC.element_to_be_clickable((By.CLASS_NAME, class_name)))
    elif el_id:
        WebDriverWait(driver, duration, frequency).until(EC.element_to_be_clickable((By.ID, el_id)))
    elif css_selector:
        WebDriverWait(driver, duration, frequency).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector)))


def wait_until_visible(driver, xpath=None, class_name=None, el_id=None, css_selector=None, tag_name=None, name=None,
                       duration=20,
                       frequency=0.1):
    if xpath:
        WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.XPATH, xpath)))
    elif class_name:
        WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
    elif el_id:
        WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.ID, el_id)))
    elif css_selector:
        WebDriverWait(driver, duration, frequency).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
    elif tag_name:
        WebDriverWait(driver, duration, frequency).until(
            EC.visibility_of_element_located((By.TAG_NAME, tag_name)))
    elif name:
        WebDriverWait(driver, duration, frequency).until(
            EC.visibility_of_element_located((By.NAME, name)))


def wait_until_present(driver, xpath=None, class_name=None, el_id=None, duration=10000, frequency=0.1):
    if xpath:
        return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.XPATH, xpath)))
    elif class_name:
        return WebDriverWait(driver, duration, frequency).until(
            EC.presence_of_element_located((By.CLASS_NAME, class_name)))
    elif el_id:
        return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.ID, el_id)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--shoe-size", default=6)
    parser.add_argument("--login-time", default=None)
    parser.add_argument("--release-time", default=None)
    parser.add_argument("--screenshot-path", default=None)
    parser.add_argument("--html-path", default=None)
    parser.add_argument("--page-load-timeout", type=int, default=100)
    parser.add_argument("--driver-type", default="chrome", choices=("firefox", "chrome"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--select-payment", action="store_true")
    parser.add_argument("--purchase", action="store_true")
    parser.add_argument("--num-retries", type=int, default=1)
    parser.add_argument("--dont-quit", action="store_true")
    parser.add_argument("--shoe-type", default="M", choices=("M", "W", "Y", "C", "XXS", "XS", "S", "L", "XL"))
    parser.add_argument("--shipping-option", default="STANDARD", choices=("STANDARD", "TWO_DAY", "NEXT_DAY"))
    parser.add_argument("--cvv", default=None)
    parser.add_argument("--shipping-address", default=None)
    parser.add_argument("--webdriver-path", required=False, default=None)
    args = parser.parse_args()

    driver = None

    if args.driver_type == "firefox":
        options = webdriver.FirefoxOptions()
        if args.headless:
            options.add_argument("--headless")
        if args.webdriver_path != None:
            executable_path = args.webdriver_path
        elif sys.platform == "darwin":
            executable_path = "./bin/geckodriver_mac"
        elif "linux" in sys.platform:
            executable_path = "./bin/geckodriver_linux"
        elif "win32" in sys.platform:
            executable_path = "./bin/geckodriver_win32.exe"
        else:
            raise Exception(
                "Drivers for installed operating system not found. Try specifying the path to the drivers with the --webdriver-path option")
        driver = webdriver.Firefox(executable_path=executable_path, firefox_options=options, log_path=os.devnull)
    elif args.driver_type == "chrome":
        options = webdriver.ChromeOptions()
        if args.headless:
            options.add_argument("headless")
        if args.webdriver_path != None:
            executable_path = args.webdriver_path
        elif sys.platform == "darwin":
            executable_path = "./bin/chromedriver_mac"
        elif "linux" in sys.platform:
            executable_path = "./bin/chromedriver_linux"
        elif "win32" in sys.platform:
            executable_path = "./bin/chromedriver_win32.exe"
        else:
            raise Exception(
                "Drivers for installed operating system not found. Try specifying the path to the drivers with the --webdriver-path option")
        driver = webdriver.Chrome(executable_path=executable_path, options=options)
    else:
        raise Exception("Specified web browser not supported, only Firefox and Chrome are supported at this point")

    run(driver=driver, username=args.username, password=args.password, url=args.url,
        shoe_size=args.shoe_size, release_time=args.release_time,
        page_load_timeout=args.page_load_timeout)
