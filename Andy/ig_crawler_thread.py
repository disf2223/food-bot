from builtins import range
import pandas as pd
from database import Database
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import threading, queue, time, re, os


def pre_manager(tag, tag_jq):
    task = [0]
    task[0] = tag
    tag_jq.put(task)


def pre_crawler(pre_crawler_id, tag_jq, url_jq, options):
    while True:
        history = []
        tag = tag_jq.get()[0]
        driver.get(f'https://www.instagram.com/explore/tags/{tag}/')
        for i in range(300):
            a = driver.find_elements_by_css_selector('a')
            for i in a:
                try:
                    if re.findall(r'https://www.instagram.com/p/[\S]*/', i.get_attribute('href')):
                        url = i.get_attribute('href')
                        if url not in history:
                            history.append(url)
                            url_jq.put(url)

                except:
                    pass

            driver.execute_script("window.scrollBy(0,-200)")
            time.sleep(0.5)
            driver.execute_script("window.scrollBy(0,10000)")
            time.sleep(1.5)

        print(f'pre_crawler {pre_crawler_id} finished tag {tag}')
        print(f'History length = {len(history)}')

        tag_jq.task_done()


def final_crawler(final_crawler_id, url_jq, data_q, options):
    while True:
        link = url_jq.get()
        try:
            driver1.get(link)
            have_tag = driver1.find_elements_by_class_name('O4GlU')
            if have_tag:
                post_time = driver1.find_element_by_class_name('FH9sR').get_attribute('datetime')
                if int(post_time.split('T')[0].split('-')[1]) >= 5:

                    location = have_tag[0].text
                    author = driver1.find_elements_by_class_name('FPmhX')[0].text
                    try:
                        likes = driver1.find_element_by_class_name('sqdOP')[1].text.split('')[0]
                    except:
                        likes = 0
                    tags = ''
                    for j in driver1.find_elements_by_class_name('C4VMK')[0].find_elements_by_css_selector('a'):
                        if 'tags' in j.get_attribute('href'):
                            tags += j.text
                    raw_text = ''.join(k.text for k in driver1.find_elements_by_class_name('C4VMK'))
                    try:
                        text = raw_text.split(driver1.find_element_by_class_name('FH9sR').text)[0]
                    except:
                        text = ''

                    data_q.put([link, author, location, likes, post_time, tags, text])

            print(f'final_crawler {final_crawler_id} finished url {link}')
        except:
            pass

        url_jq.task_done()


def main():
    data_q = queue.Queue()
    tag_jq = queue.Queue()
    url_jq = queue.Queue()
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome('/root/chromedriver', chrome_options=options)
    driver1 = webdriver.Chrome('/root/chromedriver', chrome_options=options)

    for tag in tag_list:
        pre_manager(tag, tag_jq)

    for i in range(1, os.cpu_count()+1):
        name = f'pre_crawler_{i}'
        name = threading.Thread(target=pre_crawler, args=(i, tag_jq, url_jq, options))
        name.daemon = True
        name.start()

    driver.close()
    tag_jq.join()


    for j in range(1, os.cpu_count()+1):
        name = f'final_crawler_{j}'
        name = threading.Thread(target=final_crawler, args=(j, url_jq, data_q, options))
        name.daemon = True
        name.start()

    driver1.close()
    url_jq.join()

    # df = pd.DataFrame(columns=['_id', '作者', '打卡地點', '人氣/讚數', '發文時間', '標籤', '文章內容'])
    data_ig_columns = ['_id', '作者', '打卡地點', '人氣/讚數', '發文時間', '標籤', '文章內容']

    Database.setConnectionWithMongo("ig", host='mongodb', port=27017)
    collection = Database.getConnectionWithMongo()

    for i in range(data_q.qsize()):
        tmp = data_q.get()
        tmp_dict = dict(zip(data_ig_columns, tmp))
        collection.update(
                        {'_id':tmp_dict['_id']},
                        {'$setOnInsert':tmp_dict},
                        upsert=True)
        # df.loc[i] = tmp

    # df.to_json(save_path, orient='index', force_ascii=False)

    working_time = time.perf_counter()
    print(f'Used {round(working_time / 3600, 2)} hrs')


if __name__ == "__main__":

    tag_list = ['台北早午餐', '台北小吃', '台北早餐', '台北下午茶', '台北甜點']

    # Remember to add ".json" at the end of the file name 'cause the output is json file >ω<
    # save_path = f'C:\\Users\\Big data\\Desktop\\IG_台北.json'

    main()

