from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep
from datetime import datetime,timedelta
import requests
import json
import gspread
from config import *



def get_video_stats(video_id,api_key)-> list:
  
  '''
    video_id -> youtube-id of the youtube video from where to fetch details
    api_key -> google developer console youtube api key
    return -> returns list of video data
  ''' 
 

  url = f'https://www.googleapis.com/youtube/v3/videos?key={api_key}&fields=items(snippet(title,publishedAt),statistics(viewCount,likeCount,commentCount))&part=snippet,statistics&id={video_id}'

  r = requests.get(url)
  
  stats = json.loads(r.content)["items"][0]

  title = stats["snippet"]["title"]
  publish_date = stats["snippet"]["publishedAt"]

  publish_date = (datetime.strptime(publish_date,"%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d"))

  views = stats["statistics"]["viewCount"]
  likes = stats["statistics"]["likeCount"]
  comments = stats["statistics"]["commentCount"]

  return title,publish_date,views,likes,comments


def get_delta(coin_name,time_delta,curr_date,driver):
  
  '''
    coin_name -> name of the coin from where to fetch volume
    time_delta -> time differece before and after the published date in the youtube video
    curr_date -> published date of the youtube video
    driver -> chrome driver instance
    return -> returns before and after volume of the coin
  '''
 
  driver.get(f"https://coinmarketcap.com/currencies/{coin_name}/historical-data/")

  time_diff = time_delta

  
  curr_date = datetime.strptime(curr_date,"%Y-%m-%d")

  before_date = (curr_date-timedelta(days=time_diff)).strftime('%Y-%m-%d')
  after_date = (curr_date+timedelta(days=time_diff)).strftime('%Y-%m-%d')

  date_range_volume_data = []



  sleep(1)


  flag = True
  counter = 1

  range_flag = False

  while(flag):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    sleep(3)
    data = driver.find_elements(By.XPATH,"/html/body/div/div[1]/div[1]/div[2]/div/div[3]/div/div/div[2]/table/tbody/tr")
    n = len(data)



    for row in range(counter,n+1):

      if(counter>=n):
        break
      
      date =  WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH,f"/html/body/div/div[1]/div[1]/div[2]/div/div[3]/div/div/div[2]/table/tbody/tr[{row}]/td[1]"))).text
      date = datetime.strptime(date, '%b %d, %Y').strftime('%Y-%m-%d')
      
      
      
      if(date==after_date):
        range_flag=True
            
      
      if(range_flag):
        volume =  WebDriverWait(driver, 10).until(
                  EC.presence_of_element_located(
                      (By.XPATH,f"/html/body/div/div[1]/div[1]/div[2]/div/div[3]/div/div/div[2]/table/tbody/tr[{row}]/td[6]"))).text

        volume = int((volume.replace("$","")).replace(",",""))
        date_range_volume_data.append(volume)
        if(date==before_date):
          range_flag=False
          flag=False
          break
        
      
      counter+=1
      
    sleep(1)
    button = driver.find_element_by_xpath("/html/body/div/div[1]/div[1]/div[2]/div/div[3]/div/div/p[1]/button")
    driver.execute_script("arguments[0].click();", button)
    


  after_volume = max(date_range_volume_data[0:(len(date_range_volume_data)//2)])
  before_volume = min(date_range_volume_data[(len(date_range_volume_data)//2)+1:])
  print("done")
  return before_volume,after_volume


if __name__=="__main__":
  

  options = webdriver.ChromeOptions()
        
  options.add_argument('--log-level=3')
  options.add_argument(
      "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
  )
  options.add_argument('--no-sandbox')
  # options.add_argument("window-size=1920,1080")
  # options.add_argument('--disable-dev-shm-usage')
  options.add_argument('--headless')
  driver = webdriver.Chrome(options=options)
  driver.maximize_window()
  
  gc = gspread.service_account(filename="cred.json")
  sh = gc.open_by_url(spreadheet_url)
  incoming = sh.get_worksheet(0)
  outgoing = sh.get_worksheet(1)
  
  sheet_data = incoming.batch_get((f"A{starting_row}:A",f"B{starting_row}:B"))
  youtube_urls = sheet_data[0]
  coin_names = sheet_data[1]
  
  for index in range(min(len(youtube_urls),len(coin_names))):
    video_id = youtube_urls[index][0].split("=")[-1]
    coin_name = coin_names[index][0]
    
    try:
      title,publish_date,views,likes,comments = get_video_stats(video_id,api_key) 
      print(publish_date)  
      before_vol,after_vol = get_delta(coin_name,3,publish_date,driver)
      outgoing.append_row([youtube_urls[index][0],coin_name,title,publish_date,views,likes,comments,before_vol,after_vol,after_vol-before_vol])
    except Exception as e:
      print(e)
    
  driver.close()