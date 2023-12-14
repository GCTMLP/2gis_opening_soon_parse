import json
import re
import os
import string
import random
import logging
import time
import pandas as pd

from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, InvalidArgumentException
from selenium.webdriver.chrome.options import Options

from threading import Thread, Lock

import xpaths


class TwoGisParser(Thread):
    def __init__(self, search_words=[], places=[], lock=None, result_file_name='result_tmp.json'):
        super().__init__()
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_experimental_option("excludeSwitches",
                                               ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.search_words = search_words
        self.places = places
        self.file_for_links = ''.join(random.choice(string.ascii_lowercase) for i in range(6))+'.txt'
        self.lock = lock
        self.result_file_name = result_file_name

        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

    def xpath_finder(self, xpath, many=False):
        '''
        Функция поиска элемента(ов) по классу
        '''
        if many:
            return self.driver.find_elements(By.XPATH,
                                                 xpath)
        return self.driver.find_element(By.XPATH,
                                            xpath)

    def search(self, search_word, search_town):
        """
        Метод настройки перед парсингом ссылок на объекты,
        вводим данные города и поисковой фразы

        :param search_word: фраза по которой ищем объекты
        :param search_town: город в котором ищем объекты
        :return:
        """
        self.driver.get('https://2gis.ru/')
        time.sleep(1)
        # Убираем всплывающие окна и принимаем куки (если есть)
        try:
            self.xpath_finder(xpaths.ADVERTISEMENT).click()
        except NoSuchElementException:
            pass
        try:
            self.xpath_finder(xpaths.COCKIES_XPATH).click()
        except NoSuchElementException:
            pass
        time.sleep(2)
        # Ищем необходимый город и переключаемся на него
        search_bar = self.driver.find_element(By.CSS_SELECTOR,
                                'input[placeholder="Поиск в 2ГИС"]')
        search_bar.send_keys(search_town)
        time.sleep(2)
        search_bar.send_keys(Keys.RETURN)
        # Если на город сразу не переключилось, выбираем его предложенного списка (кликаем на первый)
        try:
            time.sleep(3)
            self.xpath_finder(xpaths.FIRST_TOWN_CLICK).click()
        except NoSuchElementException:
            pass
        time.sleep(3)
        # Вставляем поисковую фразу
        search_bar = self.driver.find_element(By.CSS_SELECTOR,
                                              'input[placeholder="Поиск в 2ГИС"]')
        search_bar.send_keys(search_word)
        time.sleep(3)
        search_bar.send_keys(Keys.RETURN)

    def pages_prepare(self):
        """
        Метод "прокликивания" страниц с объектами для сбора ссылок на них
        :return: None
        """
        while True:
            # вызываем метод сбора ссылок с одной страницы
            self.link_picker()
            # Кликаем на следующую страницу
            try:
                button_next_page = self.xpath_finder(xpaths.NEXT_PAGE)
            except NoSuchElementException:
                break
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(button_next_page).perform()
                time.sleep(2)
                button_next_page.click()
            except Exception as e:
                logging.error(f'unknown error in scrolling page: {e}')

    def link_picker(self):
        """
        Метод сбора ссылкок с одной страницы
        :return: None
        """
        time.sleep(3)
        # Индексируемся по элементам на одной странице (их всегда 12)
        for num in range(1, 13):
            try:
                link_name_object = self.xpath_finder(
                        xpaths.OBJECT_LINK_XPATH.format(num))
                link = link_name_object.get_attribute('href')
                text_in_preview = self.xpath_finder(
                            xpaths.OBJECT_PREVIEW.format(num)
                ).get_attribute('innerText')
                # Если в превью есть слово про открытие - записываем ссылку на данный объект во временный файл
                if 'Скоро открытие' in text_in_preview:
                    self.file_writer(link.split('?')[0])
                    logging.info('find another one link')
            except NoSuchElementException:
                # Если попалась рекламма вместо объекта
                pass
            except Exception as e:
                logging.error(f'unknown error in link_picker: {e}')

    def file_writer(self, data):
        """
        Метод записи спарсенных ссылок в файл
        :param data: список ссылок
        :return: None
        """
        try:
            with open(self.file_for_links, 'a+') as file:
                file.write(data)
                file.write('\n')
        except Exception as e:
            logging.error('unknown error in file_writer ' + e)

    def links_prepare(self):
        """
        Метод прохода по спарсенным ссылкам для вызова на каждой метода all_data_picker
        :return: None
        """
        try:
            with open(self.file_for_links, 'r') as file:
                all_links = file.read().split('\n')
        except FileNotFoundError:
            all_links = []
        # Делаем причесанные ссылки, покороче
        clear_all_links = []
        for link in all_links:
            if link not in clear_all_links:
                clear_all_links.append(link)
        all_malls = []
        # На каждую ссылку вызываем метод сбора данных
        for link in clear_all_links:
            try:
                all_malls.append(self.all_data_picker(link))
            except Exception as e:
                logging.error(f'unknown error in all_data_picker {e}')
        # Запись спарсенных данных
        self.lock.acquire()
        with open(self.result_file_name, 'a+') as file:
            json.dump(all_malls, file)
        self.lock.release()

    def all_data_picker(self, link):
        print(link)
        try:
            self.driver.get(link)
        except InvalidArgumentException:
            pass
        time.sleep(1)
        try:
            self.xpath_finder(xpaths.ADVERTISEMENT).click()
        except:
            pass
        try:
            self.xpath_finder(xpaths.COCKIES_XPATH).click()
        except:
            pass
        data = {}
        try:
            self.xpath_finder(xpaths.PHONES_BUTTON).click()
        except NoSuchElementException:
            pass
        try:
            self.xpath_finder(xpaths.PHONES_BUTTON2).click()
        except NoSuchElementException:
            pass
        contacts = self.xpath_finder(xpaths.CONTACTS.format(1)).get_attribute('innerText')
        contacts+= self.xpath_finder(
                    xpaths.CONTACTS.format(2)).get_attribute('innerText')
        data['link'] = link.split('?')[0]
        data['name'] = self.xpath_finder(xpaths.NAME).text
        try:
            data['address_city'] = self.xpath_finder(xpaths.ADDRESS_CITY.format(1)).text
        except NoSuchElementException:
            try:
                data['address_city'] = self.xpath_finder(
                    xpaths.ADDRESS_CITY.format(2)).text
            except NoSuchElementException:
                data['address_street'] = ''

        try:
            data['address_street'] = self.xpath_finder(xpaths.ADDRESS_STREET.format(1)).text
        except NoSuchElementException:
            try:
                data['address_street'] = self.xpath_finder(
                    xpaths.ADDRESS_STREET.format(2)).text
            except NoSuchElementException:
                data['address_street'] = ''

        data['phone'] = ' '.join(re.findall(r'\+[ ()‒\-0-9]+', contacts))
        data['email'] = ' '.join(re.findall(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', contacts))
        data['site'] = ' '.join(
            re.findall(r'[a-z.]*[\S]+\.[\S]+',
                       contacts))
        info_el = xpaths.INFO_ELEMENTS
        try:
            self.xpath_finder(info_el.format(2)).click()
        except NoSuchElementException:
            self.xpath_finder(xpaths.INFO_ELEMENTS2.format(2)).click()
            info_el = xpaths.INFO_ELEMENTS2
        time.sleep(1)
        about_mall = self.xpath_finder(xpaths.ABOUT_MALL).get_attribute('innerText')
        about_mall = about_mall.split('\n')
        about_data = {}
        try:
            about_building_start = about_mall.index('Здание')
            about_building_end = about_mall.index('Транспорт')
            about_building = about_mall[about_building_start+1:about_building_end]
            for num in range(0, len(about_building), 2):
                about_data[about_building[num]] = about_building[num+1]
        except KeyError:
            logging.info('empty tab mall info')
        except Exception as e:
            logging.error(f'unknown error while grabbing tab mall info {e}')
        try:
            about_transport_start = about_mall.index('Транспорт')
            about_transport = about_mall[about_transport_start:]
            about_data['Транспорт рядом'] = ''
            for num in range(0, len(about_transport), 2):
                if about_transport[num].startswith('\u200b'):
                    about_data['Транспорт рядом'] += about_transport[num]+' '+about_transport[num+1]+'\n'
            about_data['Транспорт рядом'] = about_data['Транспорт рядом'].replace('\u200b', ' ')
            about_data['Транспорт рядом'] = about_data['Транспорт рядом'].replace('\xa0', '')
        except Exception as e:
            logging.error(f'unknown error while grabbing transport near mall {e}')
        data['about'] = about_data
        self.xpath_finder(info_el.format(3)).click()
        time.sleep(2)
        try:
            all_organizations = []
            organizations_in_building = self.xpath_finder(xpaths.ORGANIZATIONS_IN_BUILDING, many=True)
            for num in range(1, len(organizations_in_building)+1):
                org_name = self.xpath_finder(xpaths.ONE_ORGANIZATION_IN_BUILDING.format(num)).text
                org_link = self.xpath_finder(xpaths.ONE_ORGANIZATION_IN_BUILDING.format(num)).get_attribute('href').split('?')[0]
                all_organizations.append(f'{org_name} - {org_link}')
            data['organizations'] = '\n'.join(all_organizations)
            self.xpath_finder(info_el.format(4)).click()
        except NoSuchElementException:
            try:
                data['mark'] = self.xpath_finder(xpaths.MARK).text
                all_reviews = self.xpath_finder(
                    xpaths.ALL_REVIEWS).text.split('Полезно')
                text_reviews = []
                for num in range(3, len(all_reviews) + 2):
                    text_review = self.xpath_finder(
                        xpaths.TEXT_REVIEW.format(num)).text
                    text_reviews.append(text_review)
                data['reviews'] = ' '.join(text_reviews)
            except Exception as e:
                logging.error(
                    f'unknown error while grabbing marks in mall {e}')
                data['mark'] = ''
                data['reviews'] = ''
        else:
            try:
                data['mark'] = self.xpath_finder(xpaths.MARK).text
                all_reviews = self.xpath_finder(xpaths.ALL_REVIEWS).text.split('Полезно')
                text_reviews = []
                for num in range(3, len(all_reviews)+2):
                    text_review = self.xpath_finder(xpaths.TEXT_REVIEW.format(num)).text
                    text_reviews.append(text_review)
                data['reviews'] = ' '.join(text_reviews)
            except Exception as e:
                logging.error(
                    f'unknown error while grabbing marks in mall {e}')
                data['mark'] = ''
                data['reviews'] = ''
        print(data)
        return data

    def run(self):
        """
        Метод запуска парсера (переопределен от Thread)
        :return:
        """
        for place in self.places:
            print(place)
            self.lock.acquire()
            # На всякий случай записываю города, которые отработаны
            with open('cit_prepare.txt', 'a+') as f:
                f.write(place)
                f.write('\n')
            self.lock.release()
            # Запускаем парсинг ссылок по ключевым словам
            for search_word in self.search_words:
                self.search(search_word, place)
                self.pages_prepare()
        logging.info(f'starting prepare links in thread {self.ident}')
        self.links_prepare()
        # Удаляем tmp файл, в котором хранились ссылки строящихся тц
        if os.path.exists(self.file_for_links):
            os.remove(self.file_for_links)


def prepare_json_tmp(result_file_name):
    """
    Функция для превращения результата из json в xlsx
    :param result_file_name: Имя файла, в который записывали результат по тц
    :return: None
    """
    with open(result_file_name, 'r') as file:
        data = file.read()
    correct_data = data.replace('}][{', '}, {')
    correct_data = correct_data.replace('][', '')
    df = pd.DataFrame(json.loads(correct_data))
    writer = pd.ExcelWriter('result/result.xlsx')
    df.to_excel(writer)
    writer.close()
    os.remove(result_file_name)


def main(num, areas_file_name, searc_words_file):
    """
    Основная функция запуска парсера в потоках
    :param num:
    :param result_file_name:
    :return:
    """
    result_json_file = 'result_tmp.json'
    lock = Lock()
    with open(searc_words_file, 'r') as file_search:
        search_words = file_search.read().split('\n')
    with open(areas_file_name, 'r') as file_area:
        places = file_area.read().split('\n')
    threads = []
    for i in range(num):
        count = int(len(places) // num)
        if i == num - 1:
            t = TwoGisParser(search_words, places[int(count * i):], lock)
        else:
            t = TwoGisParser(search_words, places[int(count * i):int(count * (i + 1))], lock)
        threads.append(t)
    for t in threads:
        logging.info(f'thread {t.ident} start')
        t.start()
    for t in threads:
        t.join()
    prepare_json_tmp(result_json_file)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename="log/parse_log.log",
                        filemode="w",
                        format="%(asctime)s %(levelname)s %(message)s")
    main(int(os.getenv('THREAD_COUNT', default=3)), os.getenv('AREAS_FILE', default='areas.txt'), os.getenv('SEARCH_WORDS_FILE', default='search_words.txt'))
