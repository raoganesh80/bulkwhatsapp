from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from . import settings
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time,os,re,random,string
import pandas as pd

def index(request):
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
                leads = pd.read_csv(f"{os.path.join(settings.BASE_DIR, 'media')}/{request_file.name}")
                numbers = None

                # getting headers
                header = list(leads.keys())
                
                # header validation
                if True in [True if 'Unnamed:' in head else False for head in header]:
                    return render(request, 'index.html', context={"error": "Column name is empty!!"})

                for head in header:
                    # check phone header exist or not after then save phone numbers then remove phone header.
                    if head.lower() == 'phone':
                        numbers = [re.sub('[^0-9]', '', str(num))[-10:] for num in leads[head]]
                        header.remove(head)
                        header_check = True
                        break
                    else:
                        header_check = False
                
                if header_check is False:
                    return render(request, 'index.html', context={"error": "It is necessary to have a phone or mobile column inside the csv file !!!"})

                # input msg box
                msg=request.POST['msg']

                # change random-tag to digits.
                msg=msg.replace('<random>', ''.join((random.choice(string.digits) for i in range(15))))
                
                # join line break at the end of the line.
                msg=''.join((line+'%0A' for line in msg.splitlines()))
                
                # change tab-tag to tab
                msg=msg.replace('<tab>','%09')
                
                # link chrome driver
                # chrome_options = webdriver.ChromeOptions()
                # chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
                # chrome_options.add_argument("--headless")
                # chrome_options.add_argument("--disable-dev-shm-usage")
                # chrome_options.add_argument("--no-sandbox")
                driver = webdriver.Chrome(executable_path=os.environ.get(
                    "CHROMEDRIVER_PATH"))

                # open web.whatsapp.com for QR Code scaning.
                driver.get("https://web.whatsapp.com/")
                time.sleep(15)
                try:
                    driver.find_element_by_xpath(
                    '//*[@id="app"]/div/div/div[4]/div/div/div[2]/h1')

                    # save session id
                    url = driver.command_executor._url
                    session_id = driver.session_id if driver.session_id else None
                    driver = webdriver.Remote(
                        command_executor=url, desired_capabilities={})
                    driver.close()

                    non_whatsapp_no_list=[]
                    # sending process will be start one by one number
                    print('start sending process.....')
                    for i in range(len(numbers)):

                        final_msg=msg

                        # replaceing all the tags into there values.
                        for head in header:
                            final_msg = final_msg.replace(f'<{str(head)}>', str(leads[head][i]) if str(leads[head][i]) != 'nan' else '')
                        
                        # set the session id
                        driver.session_id = session_id
                        time.sleep(1)
                        driver.get(
                            f"https://web.whatsapp.com/send?phone=+91{str(numbers[i])}&text={final_msg}")
                        
                        time.sleep(3)
                        try: # if any number not exist in whatsapp then this block will excecute
                            popup = driver.find_element_by_xpath('//*[@id="app"]/div/span[2]/div/span/div/div/div/div/div/div[2]/div/div/div')
                            popup.click()
                            non_whatsapp_no_list.append(numbers[i])
                        except Exception as e:
                            action_send = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
                                (By.XPATH, "/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[3]/button")))
                            action_send.click()
                        time.sleep(4)
                        print(non_whatsapp_no_list)
                    driver.close()
                except Exception as e:
                    print('QR Code not scaned')
                    driver.close()
            except Exception as e:
                fs.delete(request_file.name)
                print('Error -> ', type(e).__name__,': ', __file__,'\nLine no. : ', e.__traceback__.tb_lineno,'\n',e,sep='')
                driver.close()
            finally:
                fs.delete(request_file.name)
        else:
            return render(request, 'index.html', context={"error": "File must be CSV only!"})
        
    return render(request,'index.html')
