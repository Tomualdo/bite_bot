from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from pathlib import Path
import os
from time import sleep
import datetime
import re

import my_logger
import cred

log = my_logger.log('main')

class BraveBot(webdriver.Chrome):
    URL = "https://s23-sk.bitefight.gameforge.com"
    USER = cred.USER
    PWD = cred.PWD
    players = {}

    def __init__(self):
        self.adventure_in_progress = None
        self.last_shop_visit = None
        self.desired_items = ['Blarkim', 'Marsil', 'Wayan', 'Ghaif', 'Jadeeye', 'Xanduu', 'Nofor', 'Ghunkhar']
        self.focused_items = []
        self.exception_items = ['Valon']
        self.shop_item_list = None
        self.attack = None
        self.level = None
        self.gold = None
        self.ap = None
        self.energy = None
        self.t_delta = None
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("disable-infobars")
        options.add_experimental_option("detach", True)  # DO NOT CLOSE THE BROWSER WINDOW AT THE END
        # options.headless = True
        # options.add_argument('--headless')
        binary_locations = [
            Path('C:/Program Files (x86)/BraveSoftware/Brave-Browser/Application/brave.exe'),
            Path('/usr/bin/brave-browser'),
            Path('/usr/bin/brave'),
        ]
        for bin in binary_locations:
            if bin.exists():
                binary_location = bin
        options.binary_location = str(binary_location)
        # driver_path = Path("C:/Users/Tom/Downloads/chromedriver_win32/chromedriver.exe")
        driver_path = Path("/home/tom/Downloads/chromedriver_linux64_113")
        # if str(driver_path) not in os.environ:
        #     log.info(f"add driver path")
        #     os.environ['PATH'] += ":" + str(driver_path)
        #     log.info(os.environ['PATH'].split(':')[-1])
        super(BraveBot, self).__init__(options=options)
        self.action = ActionChains(self)
        self.implicitly_wait(5)
        self.maximize_window()
        self.get_main_page()

    def __del__(self):
        log.debug("destructor")
        # self.quit()

    def get_main_page(self, URL=None):
        if not URL:
            URL = self.URL
        self.get(URL + "/profile")

    def login(self):
        log.info(f"Login...")
        usr = self.find_element(By.NAME, "user")
        usr.send_keys(self.USER)
        usr = self.find_element(By.NAME, "pass")
        usr.send_keys(self.PWD)
        usr.submit()

    def get_countdown(self, typ='grave'):
        regex = re.compile(r'((?P<hours>\d{2}):)?((?P<minutes>\d{2}):)?((?P<seconds>\d{2}))?')

        def parse_time(time_str):
            parts = regex.match(time_str)
            if not parts:
                return
            parts = parts.groupdict()
            time_params = {}
            for name, param in parts.items():
                if param:
                    time_params[name] = int(param)
            return datetime.timedelta(**time_params)

        try:
            if 'grave' in typ:
                if 'working' not in self.current_url:
                    self.select_hunt()
                grave_count = self.find_element(By.ID, "graveyardCount").text
                return parse_time(grave_count)

            if "profile/index" not in self.current_url:
                self.get_main_page()
            healing_countdown = self.find_element(By.ID, "healing_countdown").text
            if healing_countdown:
                return parse_time(healing_countdown)
        except Exception as e:
            log.error(f"error: {e}")
            return datetime.timedelta(0)

    def get_energy(self):
        if "profile/index" not in self.current_url:
            self.get_main_page()
        self.find_element(By.LINK_TEXT, "Schopnosti").click()
        schopnosti = self.find_elements(By.XPATH, ".//*[@id='skills_tab']//td[contains(.,'/')]")
        if len(schopnosti) == 2:
            # '(7.810 / 21.500)'
            regex = re.compile(r'\((\d+\.?\d+) / (\d+\.?\d+)\)')
            output = regex.match(schopnosti[1].text)
            energy = list(map(int, [heal.replace('.', '') for heal in output.groups()]))
            log.info(f"{energy}")
            self.energy = energy[0] / energy[1]
            return energy

    def go_hunt(self, target='Farma', r=1):
        self.get(self.URL + "/robbery")
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.get(self.URL + "/robbery")
            # if "profile/index" not in self.current_url:
            #     self.get_main_page()
            # target = self.find_element(By.XPATH, ".//*[@id='humanHunting']//button[contains(.,'Farma')]")
            _target = self.find_element(By.XPATH, f".//*[@id='humanHunting']//button[contains(.,'{target}')]")
            # target = self.find_element(By.XPATH, ".//*[@id='humanHunting']//button[contains(.,'Dedina')]")
            self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            _target.click()
            log.info(self.find_elements(By.XPATH, f"//p")[-2].text)
        return True


    def select_hunt(self):
        self.get(self.URL + "/robbery")
        return self.check_if_work_in_progress()

    def check_if_work_in_progress(self):
        log.info(f"Check if we are having work in progres ")
        if self.adventure_in_progress:
            log.warning("Adventure in progress...")
            return False

        self.get(self.URL + "/city/graveyard")
        self.t_delta = None
        if 'working' in self.current_url:
            log.info(f"Work in progress...")
            self.t_delta = self.get_countdown()
            log.info(f"Remaining time {self.t_delta} "
                     f"until {(datetime.datetime.now() + self.t_delta).strftime('%H:%M:%S')}")
            return True
        log.info(f"No work in progress")
        return False

    def go_grave(self, w='0:30'):
        self.get(self.URL + "/city/graveyard")
        if not self.check_if_work_in_progress():
            work_time = self.find_element(By.XPATH, "//select[contains(@name,'workDuration')]")
            work_time.send_keys(w)
            self.find_element(By.XPATH, "//input[contains(@name,'dowork')]").submit()
            return True

    def go_daemons(self, r=1, level=None):
        self.get(self.URL + "/city/grotte")
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.get(self.URL + "/city/grotte")
            if level is None or level == 1:
                self.find_element(By.XPATH, "//input[contains(@value,'Ľahký')]").click()
            if level == 2:
                self.find_element(By.XPATH, "//input[contains(@value,'Stredná')]").click()
            if level == 3:
                self.find_element(By.XPATH, "//input[contains(@value,'Ťažká')]").click()

            winner = self.find_element(By.XPATH, "//h3[contains(.,'Víťaz')]").text
            result = self.find_element(By.XPATH, "//*[@id='reportResult'][contains(.,'Koniec')]").text
            score = re.search(".*\((\d+ : \d+)\).*", result).group(1)
            score = list(map(int, score.split(':')))
            energy = self.get_energy()

            log.info(f"{winner:} {score:}    {energy:}")
            if energy[0] / energy[1] < 0.19:
                log.info("not enough energy")
                break

            if self.USER in winner and (score[0] / score[1] > 1):
                if not level and not level >= 3:
                    level += 1
                    log.info(f'increase level to {level}')

    def go_attack(self, r=1):
        self.get(self.URL + "/robbery")
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.get(self.URL + "/robbery")
            health = self.get_energy()
            if health[0] / health[1] > 0.20:
                self.select_hunt()
                self.find_element(By.XPATH, "//input[contains(@name,'optionsearch')]").click()

                # target info
                target_level = self.find_element(By.XPATH, "//tr[contains(.,'Úroveň')]").get_attribute('outerHTML')
                level = int(re.search(".*>(\d+)<.*", target_level).group(1))

                attack_btn = self.find_element(By.XPATH, "//button[contains(@type,'submit')]").submit()
                winner = self.find_element(By.XPATH, "//h3[contains(.,'Víťaz')]")
                if self.USER not in winner.text:
                    log.info(f"Loose aganist lvl {level}   health: {health[0]}")
                else:
                    log.info(f"Win aganist lvl {level}    health: {health[0]}")
            else:
                log.info("too low energy")
                break

    def stats_increase(self, st=None, r=1):
        log.info(f"Try to increase stats...")
        for repeat in range(r):
            if "profile/index" not in self.current_url:
                self.get_main_page()
            self.find_element(By.LINK_TEXT, "Schopnosti").click()
            try:
                number_of_stats = 4 # we do not need 5 -> charisma is not necessary
                for idx in range(number_of_stats):
                    stats = self.find_elements(By.XPATH, "//img[contains(@src,'iconplus')]")
                    if st and 'inactiv' not in stats[st].get_attribute('outerHTML'):
                        stats[st].click()
                        log.info(f"increase stats {idx}")
                        break
                    elif not st and 'inactiv' not in stats[idx].get_attribute('outerHTML'):
                        stats[idx].click()
                        log.info(f"increase stats {idx}")
                    elif idx == number_of_stats-1 and not st and 'inactiv' in stats[idx].get_attribute('outerHTML'):
                        log.info("no more gold")

            except IndexError:
                log.info("no more gold")
                break

    def get_ap(self):
        """'(0/0)7.212    0    15    19 / 124    21.330 / 34.100     10    208'"""
        if "profile/index" not in self.current_url:
            self.get_main_page()
        ap = self.find_elements(By.XPATH, "//*[@id='infobar']")
        ap = re.search('.* (\d+ \/ \d+).*', ap[0].text).group(1).split(' / ')
        self.ap = list(map(int, ap))
        return list(map(int, ap))

    def get_level(self):
        #(r'\((\d+\.?\d+) / (\d+\.?\d+)\)')
        if "profile/index" not in self.current_url:
            self.get_main_page()
        level = self.find_element(By.XPATH, "//*[@id='infobar']")
        level = re.search('  (\d+)    (\d+$)', level.text)
        self.level = int(level.group(1))
        self.attack = int(level.group(2))

    def get_gold(self):
        if "profile/index" not in self.current_url:
            self.get_main_page()
        gold = self.find_element(By.XPATH, "//*[@id='infobar']").text
        log.debug(f"Print raw infobar: {gold}")
        gold = re.search('.*\n([\d\.]+) .*', gold).group(1).replace('.', '')
        self.gold = int(gold)
        return int(gold)

    def do_adventure(self, min_energy=0.35):
        self.get_energy()

        self.get(self.URL + "/city/adventure")
        if self.check_if_work_in_progress():
            return

        if self.energy <= min_energy:
            if 'Pokračovať (3 AB)' in self.page_source:
                log.info(f"low energy {self.energy} we have to end adventure")
                self.get(self.URL + "/city/adventure/decision/36")
                self.get(self.URL + "/city/adventure")
                self.adventure_in_progress = False
                return

        if 'Dobrodružstvo končí' not in self.page_source:
            self.get(self.URL + "/city/adventure/startquest")

        if 'Pokračovať (3 AB)' in self.page_source :
            self.get(self.URL + "/city/adventure/decision/35")
            self.get(self.URL + "/city/adventure")

        import random
        ss = True
        safety_counter = 0
        self.adventure_in_progress = True
        while ss:
            self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            a = self.find_elements(By.XPATH, "//*[@class='btn']")
            s = self.find_element(By.XPATH, "//h2").text
            ss = re.search('.* (\d+\/\d+).*', s).group(1).split('/')
            ss = list(map(int, ss))
            if ss[0] == ss[1]:
                break
            rnd = random.choice(a)
            if 'Dobrodružstvo končí' in rnd.text:
                safety_counter += 1
                if safety_counter >=100:
                    log.error(f"SAFETY COUNTER REACHED in ADVENTURE LOOP...")
                    break
                continue
            log.info(f"{ss} {rnd.text}")
            safety_counter = 0
            rnd.click()

        # check at the end if we have enough energy otherwise quit
        self.get_energy()
        self.get_ap()
        self.get(self.URL + "/city/adventure")
        if self.check_if_work_in_progress():
            return

        if self.energy <= min_energy:
            if 'Pokračovať (3 AB)' in self.page_source:
                log.info(f"low energy {self.energy} we have to end adventure")
                self.get(self.URL + "/city/adventure/decision/36")
                self.get(self.URL + "/city/adventure")
                self.adventure_in_progress = False

    def get_players(self):
        if self.players:
            self.players = {}
        self.find_element(By.LINK_TEXT, "Highscore").click()
        def _get_players_data():
            tbod = self.find_element(By.XPATH, "//*[@id='highscore']")
            tr = [tr.text for tr in tbod.find_elements(By.CSS_SELECTOR, "tr")]
            race = [tr.get_attribute('outerHTML') for tr in tbod.find_elements(By.XPATH, "//tr/td/img")]
            race = [True if 'Vlkolakov' in r else False for r in race]

            # filter out only players
            idx = 0
            for record in tr:
                r = re.search('(\d+) (.*) (\d+) ([\d+\.]{0,}) ([\d+\.]{0,})', record)
                if r:
                    name = re.sub(' \[.*\]', '', r.group(2))
                    self.players[name] = [
                        int(r.group(1)),
                        int(r.group(3)),
                        int(r.group(4).replace('.', '')),
                        int(r.group(5).replace('.', '')),
                        race[idx]
                    ]
                    idx += 1

        # pages = self.find_elements(By.XPATH, "//a[contains(@href, number())]")
        end = False
        _get_players_data() # from the 1st page
        while not end:
            page = self.find_elements(By.XPATH, "//center/a/img[contains(@href, fightvalue)]")
            for p in page:
                if p.accessible_name == '+1' or p.accessible_name == 'do konca':
                    p.click()
                    _get_players_data()
                    break
                if page[-1].accessible_name == '-1':  # we are at the end
                    log.info("end of highscore list")
                    end = True
                    break

    def get_player_info(self):
        self.get_energy()
        self.get_level()
        self.get_ap()
        self.get_gold()
        log.info(f"Player info received:\n"
                 f"gold: {self.gold}\n"
                 f"energy: {self.energy:}\n"
                 f"ap: {self.ap:}\n"
                 f"level: {self.level}\n"
                 f"att: {self.attack}\n"
                 f"Focus list {self.focused_items}")

    def shop_item(self, force_shop_data_update=False, buy_only=False):

        item_pages = [
            "/city/shop/weapons/",
            "/city/shop/potions/",
            "/city/shop/helmets/",
            "/city/shop/armor/",
            "/city/shop/stuff/",
            "/city/shop/gloves/",
            "/city/shop/shoes/",
            "/city/shop/shields/"
        ]

        item_activation_list_in_profile = {
            item_pages[0]: 'Zbrane',
            item_pages[1]: 'Elixíry',
            item_pages[2]: 'Helmy',
            item_pages[3]: 'Brnenie',
            item_pages[4]: 'Veci',
            item_pages[5]: 'Rukavice',
            item_pages[6]: 'Topánky',
            item_pages[7]: 'Štíty',

        }

        if not buy_only:
            # check if we need to get shop data
            now_shop_visit = datetime.datetime.now()

            if not self.last_shop_visit:
                log.info("Getting FIRST shop data...")
                self._get_shop_data(item_pages)
                now_shop_visit = datetime.datetime.now()  # update again for first run

            shop_delay = (now_shop_visit - self.last_shop_visit).seconds
            if shop_delay < 60*5:
                log.info(f"skipping shop data... time diff is {shop_delay}")
            elif force_shop_data_update:
                log.info("Getting FORCE shop data...")
                self._get_shop_data(item_pages)
            else:
                self._get_shop_data(item_pages)

        else:
            log.info(f"buy_only is active")
            if not self.last_shop_visit:
                log.warning(f"We do not have any shop data...")
                self._get_shop_data(item_pages)


        # -----------------------------------------------------------------------------
        # buy desired item

        for desired_item in self.desired_items:
            if desired_item in self.shop_item_list.keys() \
                    and self.level >= self.shop_item_list[desired_item]['level'] \
                    and self.shop_item_list[desired_item]['inventory'] == 0 \
                    and desired_item not in self.focused_items:
                self.focused_items.append(desired_item)  # We want this item so other shopping activities have to be suppressed
                log.info(f"New focused item {desired_item}")

        self.get_player_info() # update player stats - mainly for gold
        for focused_item in self.focused_items:
            if self.gold >= self.shop_item_list[focused_item]['price']:
                # it is SHOPPING time
                self.get(self.URL + self.shop_item_list[focused_item]['type'])
                shop = self.find_element(By.ID, "shopOverview")
                shop_items = shop.find_elements(By.TAG_NAME, 'tr')
                for item in shop_items:
                    if focused_item in item.text:
                        log.info(f"We buying : {item.text}")
                        it = item.find_element(By.TAG_NAME, "a")
                        it = it.get_attribute('href')
                        if it:
                            log.info(f"{it}")
                            self.get(it)
                            log.info(f"WE bought {it}".center(50, "*"))
                            #  --------------- activate new item -------------------
                            log.info(f"ACTIVATE new item".center(50, "-"))
                            self.get(self.URL + '/profile')
                            self.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down
                            # expand item tab
                            self.find_element(
                                By.PARTIAL_LINK_TEXT,
                                item_activation_list_in_profile[self.shop_item_list[focused_item]['type']]).click()
                            my_items_table = self.find_element(By.ID, "accordion")
                            my_items = my_items_table.find_elements(By.TAG_NAME, 'tr') # //*[@id="accordion"]/div[5]/table/tbody/tr[2]/td[2]/div/div/a
                            for my_item in my_items:
                                if focused_item in my_item.text:
                                    log.info(f"We are activating : {my_item.text}")
                                    activation_item = my_item.find_element(By.TAG_NAME, "a")
                                    activation_item = activation_item.get_attribute('href')
                                    if activation_item:
                                        log.info(f"activation item href: {activation_item}")
                                        self.get(activation_item)
                                        # now we can remove focused item
                                        self.focused_items.remove(focused_item)
                                        log.info("Removing focused items...")
                                        log.info(f"Focused items: {self.focused_items}")
                                        self.shop_item(force_shop_data_update) # we need to do shop update after activation
                                        return True
                        else:
                            log.warning(f"{focused_item} BUY Problem !")

    def _get_shop_data(self, item_pages):
        log.info("Getting shop data...")
        self.shop_item_list = {}
        for item_page in item_pages:
            log.info(f"Getting page {self.URL + item_page}")
            self.get(self.URL + item_page)

            shop = self.find_element(By.ID, "shopOverview")
            shop_items = shop.find_elements(By.TAG_NAME, 'tr')

            # 'Marsil
            # (Tvoj inventár: 0 kus(ov))
            #
            # Základná šanca na zásah: +1
            # Bonusová šanca na zásah: +2
            # Zručnosť: +5
            #
            # Nákupná cena: 71.492
            # Zvýhodnená cena: 17.873
            # Predpoklady: úroveň 37
            #
            # ---'
            for item in shop_items:
                try:
                    if not item.text:
                        continue
                    item_name = re.search('^(.*)\n', item.text)
                    if item_name.group(1) in self.exception_items:
                        continue
                    inventory = re.search('^.*\n.* (\d+) ', item.text)
                    price = re.search('.*Nákupná cena: ([\d\.]+)', item.text)
                    level = re.search('.*Predpoklady: úroveň (\d+)', item.text)
                    if item_name:
                        self.shop_item_list[item_name.group(1)] = {
                            'inventory': int(inventory.group(1)),
                            'price': int(price.group(1).replace('.', '')),
                            'level': int(level.group(1)),
                            'type': item_page
                        }
                except AttributeError as e:
                    log.warning(f"item type {item_page} item {item.text}: {e}")

        self.last_shop_visit = datetime.datetime.now()
        log.info(f"Shop data successfully updated")

    def end(self):
        pass
#----------------------------------------------------------------------------------------------------------

import platform
import os

if platform.system() == 'Linux':
    from pyvirtualdisplay import Display

pwd = os.path.abspath(os.curdir)


class VirtualDisplay:
    def __init__(self, platform) -> None:
        if platform == 'Linux':
            log.info('Running LINUX !!!')
            self.display = Display(visible=0, size=(1280,1024))
            self.display.start()
        pass

    def __enter__(self):
        if platform.system() == 'Linux':
            log.info("Started Virtual diplay")
            # return self.display.start()
        pass

    def __exit__(self, type, value, traceback):
        if platform.system() == 'Linux':
            log.info("Virtual display Stop")
            self.display.stop()
        else:
            log.info("no linux ?")

#----------------------------------------------------------------------------------------------------------

def main():
    # with VirtualDisplay(platform.system()):
        bot = BraveBot()
        bot.get_main_page()
        bot.login()
        err_counter = 0
        repeat_flag = False
        while True:
            try:
                bot.get_player_info()
                bot.shop_item()
                if bot.check_if_work_in_progress():
                    log.info(f"working for {bot.t_delta.seconds} seconds")
                    sleep(bot.t_delta.seconds)

                # ----------------------------------------------------------------------------------------
                if 'Vlož svoje meno a heslo pre prihlásenie' in bot.page_source:
                    bot.get_main_page()
                    bot.login()
                    bot.get_player_info()
                # ----------------------------------------------------------------------------------------

                if bot.ap[0] == 0 or bot.energy < 0.09:
                    log.info(f"going grave - AP: {bot.ap[0]:} ENERGY: {bot.energy:}")
                    bot.get_player_info()
                    if bot.focused_items:
                        bot.shop_item(buy_only=True)
                    bot.go_grave(w="1:30")
                    bot.check_if_work_in_progress()
                    log.info(f"working for {bot.t_delta.seconds} seconds")
                    sleep(bot.t_delta.seconds)
                    _after_action_strategy(bot)

                # ----------------------------------------------------------------------------------------
                while bot.ap[0] >= 3 and bot.energy > 0.35 and not bot.check_if_work_in_progress():
                    log.info(f"bot AP is {bot.ap[0]} >= 3 --- we are going for ADVENTURE")
                    bot.get_player_info()
                    bot.do_adventure()
                    _after_action_strategy(bot)

                # ----------------------------------------------------------------------------------------
                if bot.ap[0] >=1 and not bot.check_if_work_in_progress():
                    log.info(f"bot AP is {bot.ap[0]} >= 1 --- we are going for HUNT")
                    bot.get_player_info()
                    if bot.ap[0] >= 2:
                        bot.go_hunt(target="Mesto")
                    if bot.ap[0] >= 1:
                        bot.go_hunt(target="Dedina")
                    _after_action_strategy(bot)



            except Exception as e:
                log.error(f"{e}")
                err_counter += 1
                if err_counter >=10:
                    if repeat_flag:
                        sleep(60)
                    bot.get_main_page()
                    bot.login()
                    err_counter = 0
                    repeat_flag = True


def _after_action_strategy(bot):
    bot.get_player_info()
    if not bot.focused_items:
        bot.stats_increase()
    else:
        bot.shop_item(buy_only=True)


if __name__ == '__main__':
    main()