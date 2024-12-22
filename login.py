import psycopg2
import requests
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from PIL import Image
from io import BytesIO
import base64
import captcha as captcha
import random
import os
from dotenv import load_dotenv
load_dotenv()


DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT"),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD")
}


def create_web_driver():
    options = webdriver.ChromeOptions()
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--window-size=1920,1400")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(1)
    return driver

# Function to login to the website and get the token
def login(username,password):
    # Make a request to the login API endpoint
    driver = create_web_driver()
    url = 'https://services.gst.gov.in/services/login?flag=einvoice'
    driver.get(url)
    time.sleep(5)
    
    driver.find_element(By.ID, "username").click()
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys(username)

    driver.find_element(By.ID, "user_pass").click()
    driver.find_element(By.ID, "user_pass").clear()
    driver.find_element(By.ID, "user_pass").send_keys(password)

    captcha_image_element = driver.find_element(By.ID, "imgCaptcha")
    captcha_image_data = captcha_image_element.screenshot_as_png

    image = Image.open(BytesIO(captcha_image_data))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    captcha_id, captcha_text = captcha.get_captcha_base64(base64_image)

    driver.find_element(By.ID, "captcha").click()
    driver.find_element(By.ID, "captcha").clear()
    driver.find_element(By.ID, "captcha").send_keys(captcha_text)

    button = driver.find_element(By.XPATH, f'//button[text()="Login"]')
    button.click()
    time.sleep(10)

    try:
        alert_element = driver.find_element(By.CLASS_NAME, "alert-danger")
        alert_text = alert_element.text
        print("alert_text", alert_text)

        if 'Invalid Username or Password. Please try again.' in alert_text:
            return None
        elif 'You have entered a wrong password for 3 consecutive times' in alert_text:
            return None
    except:
        pass

    try:
        alert_success = driver.find_element(By.CLASS_NAME, "alert-success")
        alert_success_text = alert_success.text
        print("alert_success_element", alert_success_text)

        if 'OTP' in alert_success_text:
            return None
    except:
        pass

    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == 'AuthToken':
            auth_token = cookie['value']
            return auth_token

# Function to extend the session
def extend_session(token):
    base_url = "https://services.gst.gov.in/services/auth/api/keepalive"

    cookies = {
        'AuthToken': token,
    }

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Referer': 'https://services.gst.gov.in/services/auth/fowelcome',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }

    try:
        response = requests.get(base_url, cookies=cookies, headers=headers)

        if response.status_code == 200:
            if "Your session is expired" in response.text or "You don't have permission" in response.text:
                print("Session extension failed. Your session is expired or permission issue.")
                return False
            else:
                print("Session extended successfully.")
                return True
        else:
            print(f"Failed to extend the session. Status Code: {response.status_code}")
            return False

    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# Function to create the database table
def create_table(cursor):
    cursor.execute('''CREATE TABLE IF NOT EXISTS tokens (token TEXT)''')

# Function to insert a token into the database
def insert_token(cursor, token):
    cursor.execute("INSERT INTO tokens (token) VALUES (%s)", (token,))

# Function to get the active token from the database
def get_active_token(cursor):
    cursor.execute("SELECT token FROM tokens")
    token = cursor.fetchone()
    if token:
        return token[0]
    else:
        return None

# Main function
def main():
    username = 'ETACUDER2017'
    password= 'Etacuder@2025'

    # Connect to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    create_table(cursor)
    conn.commit()

    try:
        active_token = get_active_token(cursor)
        if not active_token:
            token = login(username,password)
            if token:
                insert_token(cursor, token)
                conn.commit()
                active_token = token

        if active_token:
            if not extend_session(active_token):
                # If session extension fails, re-login
                token = login(username,password)
                if token:
                    cursor.execute("DELETE FROM tokens")  # Clear the tokens table
                    insert_token(cursor, token)
                    conn.commit()
                    active_token = token
    except Exception as e:
        print("An error occurred:", str(e))
        time.sleep(5)  # Retry after 10 minutes

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
