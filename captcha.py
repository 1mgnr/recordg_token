import requests
from html import unescape
from dotenv import load_dotenv
import os

load_dotenv()

def get_captcha_base64(data):
    """
    Get captcha result from base64 string
    """

    response = requests.post('http://2captcha.com/in.php', data={
        'key': os.getenv('2CAPTCHA_KEY'),
        'method': 'base64',
        'body': data,
        'json': 1,
        'regsense': 1
    }).json()

    captcha_id = response['request']

    # wait for captcha to be solved
    while True:
        response = requests.post('http://2captcha.com/res.php', data={
            'key': os.getenv('2CAPTCHA_KEY'),
            'action': 'get',
            'id': int(captcha_id)
        }).text
        if response == 'ERROR_CAPTCHA_UNSOLVABLE':
            print("captcha unsolvable error")
            return '000000'

        if '|' in response:
            _, captcha_text = unescape(response).split('|')
            return (captcha_id, captcha_text)
        

def mark_good(captcha_id):
    """
    Mark captcha as good
    """

    resp = requests.post('http://2captcha.com/res.php', data={
        'key': os.getenv('2CAPTCHA_KEY'),
        'action': 'reportgood',
        'id': int(captcha_id)
    })

    if resp.status_code == 200 and resp.text == 'OK_REPORT_RECORDED':
        print('Good captcha reported')
        return True
    else:
        print('Failed to report good captcha')
        return False


def mark_bad(captcha_id):
    """
    Mark captcha as bad
    """

    resp = requests.post('http://2captcha.com/res.php', data={
        'key':os.getenv('2CAPTCHA_KEY'),
        'action': 'reportbad',
        'id': int(captcha_id)
    })

    if resp.status_code == 200 and resp.text == 'OK_REPORT_RECORDED':
        print('Bad captcha reported')
        return True
    else:
        print('Failed to report bad captcha')
        return False
