from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from . import settings
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import time
import os
import re
import random
import string
import requests
import pandas as pd


def load_QR_Code(request):
    return JsonResponse({'context': context})


def index(request):

    global context
    context = None

    if request.method == "POST":

        print("File uploading process.....")
        # if the post request has a file under the input name 'document', then save the file.
        request_file = request.FILES['document'] if 'document' in request.FILES else None

        if request_file.name[-4::] == ".csv":
            try:
                # save attatched file
                # create a new instance of FileSystemStorage
                fs = FileSystemStorage()
                fs.save(request_file.name, request_file)

                # open csv file and extrect data
                leads = pd.read_csv(
                    f"{os.path.join(settings.BASE_DIR, 'media')}/{request_file.name}")
                fs.delete(request_file.name)
                numbers = None

                # getting headers
                header = list(leads.keys())

                # header validation
                if True in [True if 'Unnamed:' in head else False for head in header]:
                    return render(request, 'index.html', context={"error": "Column name is empty!!"})

                for head in header:
                    # check phone header exist or not after then save phone numbers then remove phone header.
                    if head.lower() == 'phone':
                        numbers = [re.sub('[^0-9]', '', str(num))[-10:]
                                   for num in leads[head]]
                        header.remove(head)
                        header_check = True
                        break
                    else:
                        header_check = False

                if header_check is False:
                    return render(request, 'index.html', context={"error": "It is necessary to have a phone or mobile column inside the csv file !!!"})

                # print(numbers)

                # input msg box
                msg = request.POST['msg']

                # change random-tag to digits.
                msg = msg.replace('<random>', ''.join(
                    (random.choice(string.digits) for i in range(15))))

                # join line break at the end of the line.
                msg = ''.join((line+'%0A' for line in msg.splitlines()))

                # change tab-tag to tab
                msg = msg.replace('<tab>', '%09')

                # link chrome driver to server envirorment.
                chrome_options = webdriver.ChromeOptions()
                chrome_options.binary_location = '/usr/bin/google-chrome'
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                driver = webdriver.Chrome(
                    executable_path='/root/demoproject/chromedriver', chrome_options=chrome_options)

                # driver = webdriver.Chrome()  # this code will work only local server

                # open web.whatsapp.com for QR Code scaning.
                url = "https://web.whatsapp.com/"
                driver.get(url)
                if requests.get(url).status_code != 200:
                    driver.close()
                    return render(request, 'index.html', context={"error": "Whatsapp server dosn't response !!"})

                time.sleep(4)
                # QR code snapshot here
                # print(driver.page_source)
                cur_img = ''
                counter = 0
                try:
                    get_img_div = driver.find_element_by_xpath(
                        '//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div')
                    # if qr code load loop will execute.
                    while(True):
                        get_img = get_img_div.get_attribute('data-ref')
                        # print('qr_code : ',get_img)
                        if(cur_img != get_img):  # if qr code image change.
                            counter += 1
                            driver.save_screenshot(
                                f"{os.path.join(settings.BASE_DIR, 'staticfiles/images')}/page_image.png")
                            qrcode_ele = driver.find_element_by_xpath(
                                '//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div')
                            location = qrcode_ele.location
                            size = qrcode_ele.size
                            # crop image
                            x = location['x']-30
                            y = location['y']-30
                            width = location['x']+size['width']+30
                            height = location['y']+size['height']+30
                            im = Image.open(
                                f"{os.path.join(settings.BASE_DIR, 'staticfiles/images')}/page_image.png")
                            im = im.crop(
                                (int(x), int(y), int(width), int(height)))
                            im.save(
                                f"{os.path.join(settings.BASE_DIR, 'staticfiles/images')}/qr_code{counter}.png")
                            context = {
                                'qr_code_url': f'static/images/qr_code{counter}.png', 'counter': counter}

                        if(counter == 3):  # if 3 qr code images is loaded.
                            break
                        cur_img = get_img
                except Exception as e:
                    print('Error -> ', type(e).__name__, ': ', __file__,
                          '\nLine no. : ', e.__traceback__.tb_lineno, '\n', e, sep='')
                    print('QR Code not open properly')

                time.sleep(15)
                try:
                    driver.find_element_by_xpath(
                        '//*[@id="app"]/div/div/div[4]/div/div/div[2]/h1')
                    # if authentication done.
                    context['auth'] = True
                    # save session id
                    url = driver.command_executor._url
                    session_id = driver.session_id if driver.session_id else None
                    driver = webdriver.Remote(
                        command_executor=url, desired_capabilities={})
                    driver.close()

                    non_whatsapp_no_list = []
                    # sending process will be start one by one number
                    print('start sending process.....')
                    for i in range(len(numbers)):

                        final_msg = msg

                        # replaceing all the tags into there values.
                        for head in header:
                            final_msg = final_msg.replace(f'<{str(head)}>', str(
                                leads[head][i]) if str(leads[head][i]) != 'nan' else '')

                        # set the session id
                        driver.session_id = session_id
                        time.sleep(1)
                        # open sending url
                        url = f"https://web.whatsapp.com/send?phone=+91{str(numbers[i])}&text={final_msg}"
                        driver.get(url)
                        if requests.get(url).status_code == 200:
                            time.sleep(3)
                            try:  # if any number not exist in whatsapp then this block will excecute
                                popup = driver.find_element_by_xpath(
                                    '//*[@id="app"]/div/span[2]/div/span/div/div/div/div/div/div[2]/div/div/div')
                                popup.click()
                                non_whatsapp_no_list.append(numbers[i])
                            except Exception as e:
                                action_send = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
                                    (By.XPATH, "/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[3]/button")))
                                action_send.click()
                        time.sleep(1)
                    print(non_whatsapp_no_list if len(non_whatsapp_no_list)
                          != 0 else 'Non whatsapp numbers not found.')
                except Exception as e:
                    print('Error -> ', type(e).__name__, ': ', __file__,
                          '\nLine no. : ', e.__traceback__.tb_lineno, '\n', e, sep='')
                    print('QR Code not scaned')
            except Exception as e:
                print('Error -> ', type(e).__name__, ': ', __file__,
                      '\nLine no. : ', e.__traceback__.tb_lineno, '\n', e, sep='')
            driver.close()
        else:
            return render(request, 'index.html', context={"error": "File must be CSV only!"})

    return render(request, 'index.html')
