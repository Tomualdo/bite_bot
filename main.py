from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
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
import random
import platform
import traceback
import pickle

import my_logger
import cred

log = my_logger.log('main')


class BraveBot(webdriver.Chrome):
    URL = cred.URL
    USER = cred.USER
    PWD = cred.PWD
    players = {}

    def __init__(self):
        self.desired_talents = [
            'Zdroj života', 'Nával zúrivosti', 'Zúrivý útok', 'Lovec a korisť', 'Rýchly návrat', 'Bezcitnosť',
            'Jed', 'Poznaj svojho protivníka', 'Desivý úder', 'Smrtiaci vietor', 'Železné zovretie', 'Smrtiaca aura',
            'Inštinkt lovca', 'Odčerpanie esencie (malé)', 'Bojové reflexy', 'Podoba ducha'
        ]
        self.healing_cooldown = datetime.datetime.now()
        self.action_focus = []
        self.free_inventory_space = None
        self.adventure_in_progress = None
        self.last_shop_visit = None
        self.desired_items = list(
            {
                'Blarkim', 'Marsil', 'Wayan', 'Ghaif', 'Jadeeye', 'Xanduu', 'Nofor', 'Ghunkhar', 'Yasutsuna', 'Gorgoth',
                'Darnam', 'Baan', 'Kalima', 'Sosul', 'Erenthight', 'Ybor', 'Eriall', 'Rimdil', 'Hyarspex', 'Anzuur',
                'Furios', 'Korgan', 'Void', 'Hexxen', 'Nagash', 'Korgan', 'Tabar', 'Chamkaq', 'Nodachi', 'Balbriggan',
                'Hexxen', 'Yogloth', 'Svinferin', 'Borkaan', 'Anyis', 'Diablis', 'Telgore', 'Telfer', 'Renning',
                'Lyx', 'Zombor', 'Sagamal', 'Vardha', 'Kaimaan', 'Sinclair', 'Emon', 'Nihil Ferrox', 'Brodak', 'Krakarot',
                'Reflec', 'Trollthom', 'Sonisha', 'Bergor', 'Urrosh', 'Rig-Myr', 'Firehold', 'Watari', 'Halgar'
            })
        self.focused_items = []
        self.exception_items = ['Valon']

        self.item_shop_pages = [
            "/city/shop/weapons/",
            "/city/shop/potions/",
            "/city/shop/helmets/",
            "/city/shop/armor/",
            "/city/shop/stuff/",
            "/city/shop/gloves/",
            "/city/shop/shoes/",
            "/city/shop/shields/"
        ]

        self.item_list_profile = {
            self.item_shop_pages[0]: 'Zbrane',
            self.item_shop_pages[1]: 'Elixíry',
            self.item_shop_pages[2]: 'Helmy',
            self.item_shop_pages[3]: 'Brnenie',
            self.item_shop_pages[4]: 'Veci',
            self.item_shop_pages[5]: 'Rukavice',
            self.item_shop_pages[6]: 'Topánky',
            self.item_shop_pages[7]: 'Štíty',

        }

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
        log.info("destructor")
        # self.quit()

    def get_main_page(self, URL=None):
        if not URL:
            URL = self.URL
        log.info(f"Going to {URL + '/profile'} page")
        self.get(URL + "/profile")

    def login(self):
        log.info(f"Login...")
        self.get(self.URL + '/user/login')
        usr = self.find_element(By.NAME, "user")
        usr.send_keys(self.USER)
        usr = self.find_element(By.NAME, "pass")
        usr.send_keys(self.PWD)
        usr.submit()
        self.load_focused_items()

    def logout(self):
        self.find_element(By.LINK_TEXT, "Odhlásiť").click()

    def get_countdown(self, typ='grave'):

        try:
            if 'grave' in typ:
                if 'working' not in self.current_url:
                    self.select_hunt()
                grave_count = self.find_element(By.ID, "graveyardCount").text
                return self._parse_time(grave_count)

            if "profile/index" not in self.current_url:
                self.get_main_page()
            healing_countdown = self.find_element(By.ID, "healing_countdown").text
            if healing_countdown:
                return self._parse_time(healing_countdown)
        except Exception as e:
            log.error(f"error: {e}")
            return datetime.timedelta(0)

    @staticmethod
    def _parse_time(time_str):
        regex = re.compile(r'((?P<hours>\d{2}):)?((?P<minutes>\d{2}):)?((?P<seconds>\d{2}))?')
        parts = regex.match(time_str)
        if not parts:
            return
        parts = parts.groupdict()
        time_params = {}
        for name, param in parts.items():
            if param:
                time_params[name] = int(param)
        return datetime.timedelta(**time_params)

    def get_energy(self):
        energy = self.find_element(By.XPATH, "//*[@id='infobar']").text
        energy = re.search('.* \d+ \/ \d+.* ([-\d+\.]+ \/ \d+\.?\d+)', energy).group(1).replace('.', '').split(' / ')
        energy = list(map(int, energy))
        log.info(f"Energy: {energy}")
        self.energy = energy[0] / energy[1]
        return self.energy

    def go_hunt(self, target='Farma', r=1):
        log.warning("HUNT".center(50, "-"))
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
            results = self.find_elements(By.XPATH, f"//p")
            for result in results:
                log.info(result.text)
        return True

    def select_hunt(self):
        self.get(self.URL + "/robbery")
        return self.check_if_work_in_progress()

    def check_if_work_in_progress(self):
        log.info(f"Check if we are having work in progres ")

        self.get(self.URL + "/city/graveyard")
        if 'adventure' in self.page_source:
            log.info(f"We have unfinished adventure... ")
            self.adventure_in_progress = True

        if self.adventure_in_progress:
            log.warning("Adventure in progress...")
            return False
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
            if self.adventure_in_progress:
                self.do_adventure(finish=True)
                self.get(self.URL + "/city/graveyard")
            work_time = self.find_element(By.XPATH, "//select[contains(@name,'workDuration')]")
            work_time.send_keys(w)
            self.find_element(By.XPATH, "//input[contains(@name,'dowork')]").submit()
            log.warning(" Working... ".center(100, "*"))
            return True

    def go_daemons(self, r=1, level=None):
        log.warning("DAEMONS".center(50, "-"))
        self.get(self.URL + "/city/grotte")
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.get(self.URL + "/city/grotte")
            self.get_player_info()
            if self.energy < 0.09:
                self.get_healing()
                self.get(self.URL + "/city/grotte")
                self.get_player_info()
            if self.energy < 0.09 or self.ap[0] == 0:
                log.warning("not enough power to fight")
                break
            if level is None:
                level = random.choice([1, 2, 3])
            if level is None or level == 1:
                log.info("Easy Demon")
                self.find_element(By.XPATH, "//input[contains(@value,'Ľahký')]").click()
            if level == 2:
                log.info("Advanced Demon")
                self.find_element(By.XPATH, "//input[contains(@value,'Stredná')]").click()
            if level == 3:
                log.info("Hard Demon")
                self.find_element(By.XPATH, "//input[contains(@value,'Ťažká')]").click()

            winner = self.find_element(By.XPATH, "//h3[contains(.,'Víťaz')]").text
            result = self.find_element(By.XPATH, "//*[@id='reportResult'][contains(.,'Koniec')]").text
            score = re.search(".*\((\d+ : \d+)\).*", result)
            if not score:
                log.warning(f"{winner}\n{result}")
                return False
            score = score.group(1)
            score = list(map(int, score.split(':')))
            self.get_energy()

            log.info(f"{winner:}\n{result}\n{score:}\n{self.energy:}")
            if self.energy < 0.09:
                log.info("not enough energy")
                break

            # if self.USER in winner and (score[0] / score[1] > 1):
            #     if not level and not level >= 3:
            #         level += 1
            #         log.info(f'increase level to {level}')

    def go_attack(self, r=1):
        self.get(self.URL + "/robbery")
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.get(self.URL + "/robbery")
            self.get_energy()
            if self.energy > 0.20:

                self.find_element(By.XPATH, "//input[contains(@name,'optionsearch')]").click()

                # target info
                target_level = self.find_element(By.XPATH, "//tr[contains(.,'Úroveň')]").get_attribute('outerHTML')
                level = int(re.search(".*>(\d+)<.*", target_level).group(1))

                attack_btn = self.find_element(By.XPATH, "//button[contains(@type,'submit')]").submit()
                winner = self.find_element(By.XPATH, "//h3[contains(.,'Víťaz')]")
                if self.USER not in winner.text:
                    log.info(f"Loose aganist lvl {level}   health: {self.energy}")
                else:
                    log.info(f"Win aganist lvl {level}    health: {self.energy}")
            else:
                log.info("too low energy")
                break

    def stats_increase(self, st=None, r=1):
        self.hideout()
        log.info(f"Try to increase stats...")
        for repeat in range(r):
            if "profile/index" not in self.current_url:
                self.get_main_page()
                self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.find_element(By.LINK_TEXT, "Schopnosti").click()
            try:
                number_of_stats = 4  # we do not need 5 -> charisma is not necessary
                for idx in range(number_of_stats):
                    stats = self.find_elements(By.XPATH, "//img[contains(@src,'iconplus')]")
                    if st and 'inactiv' not in stats[st].get_attribute('outerHTML'):
                        stats[st].click()
                        log.info(f"increase stats {idx}")
                        break
                    elif not st and 'inactiv' not in stats[idx].get_attribute('outerHTML'):
                        stats[idx].click()
                        log.info(f"increase stats {idx}")
                    elif idx == number_of_stats - 1 and not st and 'inactiv' in stats[idx].get_attribute('outerHTML'):
                        log.info("no more gold")

            except IndexError:
                log.info("no more gold")
                break

    def get_ap(self):
        """'(0/0)7.212    0    15    19 / 124    21.330 / 34.100     10    208'"""
        # if "profile/index" not in self.current_url:
        #     self.get_main_page()
        ap = self.find_elements(By.XPATH, "//*[@id='infobar']")
        ap = re.search('.* (\d+ \/ \d+) .*', ap[0].text).group(1).split(' / ')
        self.ap = list(map(int, ap))
        return list(map(int, ap))

    def get_level(self):
        # (r'\((\d+\.?\d+) / (\d+\.?\d+)\)')
        # if "profile/index" not in self.current_url:
        #     self.get_main_page()
        level = self.find_element(By.XPATH, "//*[@id='infobar']")
        level = re.search('  (\d+)    (\d+$)', level.text)
        self.level = int(level.group(1))
        self.attack = int(level.group(2))

    def get_gold(self):
        # if "profile/index" not in self.current_url:
        #     self.get_main_page()
        gold = self.find_element(By.XPATH, "//*[@id='infobar']").text
        log.debug(f"Print raw infobar: {gold}")
        gold = re.search('.*\n([\d\.]+) .*', gold).group(1).replace('.', '')
        self.gold = int(gold)
        return int(gold)

    def do_adventure(self, min_energy=0.35, finish=False):
        log.warning("ADVENTURE".center(50, "-"))
        if finish:
            #document.location.href='/city/adventure/cancelquest
            log.warning("Cancel Adventure")
            self.get(self.URL + "/city/adventure/cancelquest")
            self.adventure_in_progress = False
            return

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

        if 'Pokračovať (3 AB)' in self.page_source:
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
            if 'Začať dobrodružstvo' in self.page_source:
                log.warning("We probably do not have enough energy...quitting")
                self.adventure_in_progress = False
                return
            if 'Spotreboval si už všetku svoju energiu, takže toto dobrodužstvo sa teraz končí.' in self.page_source:
                self.adventure_in_progress = False
                return
            if 'Dobrodružstvo končí' in rnd.text:
                safety_counter += 1
                if safety_counter >= 100:
                    log.error(f"SAFETY COUNTER REACHED in ADVENTURE LOOP...")
                    break
                continue
            log.info(f"{ss} {rnd.text}")
            safety_counter = 0
            rnd.click()
            if 'Spotreboval si už všetku svoju energiu, takže toto dobrodužstvo sa teraz končí.' in self.page_source:
                self.adventure_in_progress = False
                return
            self.get_player_info()
            if self.energy < 0.1 or 'Si vážne zranený' in self.page_source:
                healing_result = self.get_healing()
                if 'Spotreboval si už všetku svoju energiu, takže toto dobrodužstvo sa teraz končí.' in self.page_source:
                    self.adventure_in_progress = False
                    return
                if isinstance(healing_result, bool) and healing_result is True:
                    log.info(f"healing was SUCCESSFUL")
                    return
                elif healing_result is False:
                    log.info(f"healing FAILED")
                    return
                elif isinstance(healing_result, datetime.timedelta):
                    log.info(f"healing cooldown during adventure")
                    return
            if self.energy < 0.1:
                log.info(f"low energy during adventure :{self.energy} we have to end adventure")
                self.get(self.URL + "/city/adventure/decision/36")
                self.get(self.URL + "/city/adventure")
                self.adventure_in_progress = False

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
        _get_players_data()  # from the 1st page
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
                 f"Focus list {self.focused_items}\n"
                 f"Adventure: {self.adventure_in_progress}\n"
                 f"Inventory space: {self.free_inventory_space}")

    def shop_item(self, force_shop_data_update=False, buy_only=False, activate=True):
        self.get_inventory_space()
        if not self.free_inventory_space:
            log.warning("We have to sell something")
            self.sell_item()

        if not buy_only:
            # check if we need to get shop data
            now_shop_visit = datetime.datetime.now()

            if not self.last_shop_visit:
                log.info("Getting FIRST shop data...")
                self._get_shop_data()
                now_shop_visit = datetime.datetime.now()  # update again for first run

            shop_delay = (now_shop_visit - self.last_shop_visit).seconds
            if force_shop_data_update:
                log.info("Getting FORCE shop data...")
                self._get_shop_data()
            elif shop_delay < 60 * 5:
                log.info(f"skipping shop data... time diff is {shop_delay}")
            else:
                self._get_shop_data()

        else:
            log.info(f"buy_only is active")
            if not self.last_shop_visit:
                log.warning(f"We do not have any shop data...")
                self._get_shop_data()

        # -----------------------------------------------------------------------------
        # buy desired item

        for desired_item in self.desired_items:
            if desired_item in self.shop_item_list.keys() \
                    and self.level == self.shop_item_list[desired_item]['level'] \
                    and self.shop_item_list[desired_item]['inventory'] == 0 \
                    and desired_item not in self.focused_items:
                # We want this item so other shopping activities have to be suppressed
                self._add_focused_and_pickle(desired_item)

        # TODO: remove if in focused olready own
        # if my_item in self.focused_items:
        #     pass

        self.get_player_info()  # update player stats - mainly for gold
        for focused_item in self.focused_items:
            if self.gold < self.shop_item_list[focused_item]['price']:
                log.info(
                    f"Not enough gold for {focused_item}  {self.gold} < {self.shop_item_list[focused_item]['price']}")
                continue
            # it is SHOPPING time
            self.get(self.URL + self.shop_item_list[focused_item]['type'])
            shop = self.find_element(By.ID, "shopOverview")
            shop_items = shop.find_elements(By.TAG_NAME, 'tr')
            for item in shop_items:
                # extract exact name of item
                item_name = re.search('(^.*)\n', item.text)
                if not item_name:
                    continue
                item_name = item_name.group(1)
                if focused_item != item_name:
                    continue
                log.info(f"We buying : {item_name}")
                it = item.find_element(By.TAG_NAME, "a")
                it = it.get_attribute('href')
                log.info(f"{it}")
                # before get we have to decide activation
                is_healing = 'Stredný liečivý elixír' in item_name
                self.get(it)
                self._remove_focused_item_and_pickle(focused_item)
                log.info(f"WE bought {focused_item}".center(50, "*"))
                if is_healing:
                    log.info("Activation is skipped...")
                    return True
                #  --------------- activate new item -------------------
                log.info(f"ACTIVATE new item".center(50, "-"))
                self.get(self.URL + '/profile')
                self.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down
                # expand item tab
                self.find_element(
                    By.PARTIAL_LINK_TEXT,
                    self.item_list_profile[self.shop_item_list[focused_item]['type']]).click()
                my_items_table = self.find_element(By.ID, "accordion")
                my_items = my_items_table.find_elements(By.TAG_NAME,
                                                        'tr')  # //*[@id="accordion"]/div[5]/table/tbody/tr[2]/td[2]/div/div/a
                for my_item in my_items:
                    if focused_item not in my_item.text:
                        continue
                    log.info(f"We are activating : {my_item.text}")
                    activation_item = my_item.find_element(By.TAG_NAME, "a")
                    activation_item = activation_item.get_attribute('href')
                    log.info(f"activation item href: {activation_item}")
                    self.get(activation_item)
                    # now we can remove focused item
                    self._remove_focused_item_and_pickle(focused_item)
                    self.shop_item(
                        force_shop_data_update=True)  # we need to do shop update after activation
                    return True

    def _remove_focused_item_and_pickle(self, focused_item):
        if focused_item not in self.focused_items:
            log.warning(f"{focused_item} already removed")
            return
        self.focused_items.remove(focused_item)
        log.info(f"Removing focused item: {focused_item}")
        with open('focused_items', 'wb') as f:
            pickle.dump(self.focused_items, f)

    def _add_focused_and_pickle(self, desired_item):
        self.focused_items.append(desired_item)
        log.info(f"New focused item {desired_item}")
        with open('focused_items', 'wb') as f:
            pickle.dump(self.focused_items, f)
            log.info(f"Item {desired_item} pickled...")

    def load_focused_items(self):
        if not os.path.isfile('focused_items'):
            log.warning(f"No restore file found...")
            return
        with open('focused_items', 'rb') as f:
            self.focused_items = pickle.load(f)
            log.info(f"Focused items restored: {self.focused_items}")


    def _get_shop_data(self):
        log.info("Getting shop data...")
        self.shop_item_list = {}
        for item_page in self.item_shop_pages:
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

    def get_healing(self, healing_type='Stredný liečivý elixír'):
        if datetime.datetime.now() <= self.healing_cooldown:
            log.warning(f"Healing available at {self.healing_cooldown}")
            return False

        origin_page = self.current_url
        self.get(self.URL + '/profile')
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down
        # expand item tab
        my_items_table = self.find_element(By.ID, "accordion")
        # //*[@id="accordion"]/div[5]/table/tbody/tr[2]/td[2]/div/div/a
        my_items = my_items_table.find_elements(By.TAG_NAME, 'h3')
        for items in my_items:
            if 'Elixíry' not in items.text:
                continue
            self.find_element(
                By.PARTIAL_LINK_TEXT, 'Elixíry').click()
            my_items_table = self.find_element(By.ID, "accordion")
            my_items = my_items_table.find_elements(By.TAG_NAME, 'tr')
            for my_item in my_items:
                if healing_type in my_item.text:
                    # (Tvoj inventár: 2 kus(ov))
                    inventory = re.search('Tvoj inventár: (\d+)', my_item.text)
                    if not inventory:
                        log.error(f"No inventory count for {healing_type}")
                        return False
                    inventory = inventory.group(1)
                    if int(inventory) < 2:
                        log.warning(f"we have only 1 {healing_type}. We want to buy more")
                        if healing_type not in self.focused_items:
                            log.info("Adding HEALING to focused items")
                            # self.focused_items.append(healing_type)
                            self._add_focused_and_pickle(healing_type)

                    if int(inventory) == 0:
                        log.warning(f"we do not have ANY Healing: {healing_type}")
                        if healing_type not in self.focused_items:
                            log.info("Adding HEALING to focused items")
                            self._add_focused_and_pickle(healing_type)
                        if not self.shop_item(buy_only=True):
                            return False
                        else:
                            self.get_healing()
                    log.info(f"HEALING : {my_item.text}")
                    # check timeout:
                    # if 'Čas do konca' in my_item.text:
                    sleep(1)
                    cooldowns = self.find_elements(By.ID, "item_cooldown2_2")
                    for cooldown in cooldowns:
                        cooldown_text = re.search('(\d+:\d+:\d+)', cooldown.text)
                        if not cooldown_text:
                            continue
                        log.warning(f"Healing cooldown...")
                        healing_cooldown = self._parse_time(cooldown_text.group(1))
                        self.healing_cooldown = datetime.datetime.now() + healing_cooldown
                        log.info(f"Remaining time {healing_cooldown} "
                                 f"until {self.healing_cooldown.strftime('%H:%M:%S')}")
                        # datetime.datetime.now() <= healing_cooldown # we dont need to check healing
                        return False

                    log.info("No healing cooldown...")
                    activation_item = my_item.find_element(By.TAG_NAME, "a")
                    activation_item = activation_item.get_attribute('href')
                    if activation_item:
                        log.info(f"activation item href: {activation_item}")
                        self.get(activation_item)
                        self.get_player_info()
                        self.get(origin_page)
                        return True
            log.error(f"Error in healing method or no potions in inventory")
            log.warning(f"we do not have ANY Healing: {healing_type}")
            if healing_type not in self.focused_items:
                log.info("Adding HEALING to focused items")
                self._add_focused_and_pickle(healing_type)
            if not self.shop_item(buy_only=True):
                return False
            else:
                log.info("We bought healing potion... now try to use it")
                return self.get_healing()
                # return True

        log.warning(f"Elixíry not found in inventory")
        if healing_type not in self.focused_items:
            log.info("Adding HEALING to focused items")
            self._add_focused_and_pickle(healing_type)

    def get_inventory_space(self):
        # //*[@id="shop"]/div[2]/div/div[1]/p[2]
        self.get(self.URL + "/city/shop")
        content = self.find_element(By.XPATH, "//*[@id='shop']").text
        #:\nPočet voľných miest v Tvojom inventári: 6 (z celkového počtu 19).\nVýb
        content = re.search('.* (\d+) \(.* (\d+)\)', content)

        self.free_inventory_space = list(map(int, content.groups()))
        log.info(f"Free inventory space: {self.free_inventory_space}")
        if self.free_inventory_space[0] == 0:
            log.warning("You do not have enough space in inventory!")
            return False
        return True

    def sell_item(self):
        origin_page = self.current_url
        excluded_items = 'Elixíry'
        self.get(self.URL + '/profile')
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down
        # expand item tab
        my_items_table = self.find_element(By.ID, "accordion")
        # //*[@id="accordion"]/div[5]/table/tbody/tr[2]/td[2]/div/div/a
        my_items = my_items_table.find_elements(By.TAG_NAME, 'h3')
        item_groups_to_sell = []
        for item in my_items:
            if item.text.split(' ')[0] not in self.item_list_profile.values() or item.text.split(' ')[
                0] in excluded_items:
                continue
            print(f"Getting {item.text}")
            # Brnenie ( 4 )
            item_count = re.search(' \( (\d+) \)', item.text).group(1)
            if int(item_count) > 1:
                log.warning(f"Item: {item.text} > 1 count")
                item_groups_to_sell.append(item.text.split(' ')[0])
        # if inventory is not full, but we do not have space to store new items
        if not item_groups_to_sell and self.free_inventory_space[0] == 0:
            log.error(f"Inventory is not full,"
                      f" but we do not have space to store new items -- HIDEOUT upgrade is necessary ")
            if 'HIDEOUT' not in self.focused_items:
                log.warning(f"adding HIDEOUT to focused items")
                self._add_focused_and_pickle('HIDEOUT')
                return False
        if not item_groups_to_sell:
            log.info("Nothing to sell...")
            return False
        else:
            log.warning("Item sell procedure...")
            for link, type in self.item_list_profile.items():
                for item_group in item_groups_to_sell:
                    if item_group not in type:
                        continue
                    # /city/shop/armor/
                    log.info(f"Getting page {self.URL + link}")
                    self.get(self.URL + link)
                    self.find_element(By.PARTIAL_LINK_TEXT, self.item_list_profile[link]).click()
                    # now we have expanded desired group to sell the item
                    my_items_table = self.find_element(By.ID, "shopOverview")  # //*[@id="shopOverview"]/
                    my_items = my_items_table.find_elements(By.TAG_NAME, 'tr')
                    items_to_sell = {}
                    for my_item in my_items:
                        # check count and level if is < player
                        # check also 'Predať' is in search
                        # iteration must find at least 2 items in inventory and sell last one [-1]
                        level = re.search('.*Predpoklady: úroveň (\d+)', my_item.text)
                        inventory_count = re.search('^.*\n.* (\d+) ', my_item.text)
                        item_name = re.search('^(.*)\n', my_item.text)
                        if not level and not inventory_count and not 'Predať' in my_item.text:
                            continue
                        if int(level.group(1)) < self.level and int(inventory_count.group(1)) >= 1:
                            log.info(f"checking selling item level {level.group(1)} vs player level {self.level}")
                            selling_item = my_item.find_elements(By.TAG_NAME, "a")
                            # distinguish between buy / sell
                            for st in selling_item:
                                href = st.get_attribute('href')
                                if 'sell' not in href:
                                    continue
                                # add items to dir
                                items_to_sell[href] = item_name.group(1)
                            if len(items_to_sell) <= 1:  # continue only if there are at least 2 items
                                continue
                            log.info(f"We are selling : {my_item.text}")
                            log.warning(f"FINAL: {list(items_to_sell.values())[-1]} {list(items_to_sell)[-1]}")
                            self.get(list(items_to_sell)[-1])
                            return True
        log.warning("End of sell....")
        return False

    def hideout(self):
        origin = self.current_url
        self.get(self.URL + '/hideout/index')
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down
        # hideout_items = self.find_element(By.ID, "fightreport")  # //*[@id="fightreport"]
        hideout_items = self.find_element(By.XPATH, "//table[contains(@class, 'upgrade')]//following::tbody")
        hideout_table_items = hideout_items.find_elements(By.TAG_NAME, 'tr')
        for hideout_table_item in hideout_table_items:
            if 'Ďalšia úroveň stojí' not in hideout_table_item.text:
                continue
            elif 'HIDEOUT' in self.focused_items and 'Domov' in hideout_table_item.text:
                log.warning(f"Try to buy HIDEOUT upgrade")
            else:
                pass
            activation_items = hideout_table_item.find_elements(By.TAG_NAME, "a")
            for activation_item in activation_items:
                activation_href = activation_item.get_attribute('href')
                # if not activation_href:
                #     continue
                if 'token' not in activation_href:
                    log.info(f"skip {hideout_table_item.text}")
                    continue

                """
                2023-06-23 19:04:29,640 [main] [INFO ] [line:15] Domov Úroveň 1 / 14
                Ďalšia úroveň stojí 16
                """
                log.info(hideout_table_item.text)
                cost = re.search('Ďalšia úroveň stojí (\d+)', hideout_table_item.text).group(1)
                if int(cost) > self.gold:
                    continue
                log.info(f"BUY hideout upgrade {hideout_items.text} for {cost} gold")
                self.get(activation_href)
                if 'HIDEOUT' in self.focused_items and 'Domov' in hideout_table_item.text:
                    log.warning(f"Remove HIDEOUT from focused items")
                    self._remove_focused_item_and_pickle('HIDEOUT')
                self.get(origin)
                log.info("Hideout BUY successful...")
                return True
        log.info("Nothing to upgrade in hideout...")
        return False

    def check_overview(self):
        self.action_focus = []
        if '/profile/index' not in self.current_url:
            self.get(self.URL + '/profile/index')
        # //*[@id="gameEvent"]/div[2]/div/ul/li[1]/text()
        overview = self.find_elements(By.XPATH, "//*[@id='gameEvent']//ul")
        if not overview:
            log.warning("No game events active...")
            return
        overview = overview[0]
        log.info(f"Overview:\n{overview.text}")
        if 'jaskyni' in overview.text:
            if 'cavern' not in self.action_focus:
                self.action_focus.append('cavern')
        if 'v nákladoch za schopnosti' in overview.text:
            if 'stats' not in self.action_focus:
                self.action_focus.append('stats')
        # TODO overview tips
        """+50% zlata v jaskyni
        +100% skúsenosti v jaskyni
        +100% volných misií (maximum)
        +50% obnovy energie
        -----
        -30% zlata v nákladoch za schopnosti
        -30% zlata v nákladoch za predmety u obchodníka

        """

    def talents(self):
        self.get(self.URL + '/profile/talents')
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.execute_script("window.scrollTo(document.body.scrollHeight, 0);")
        # get price for point
        # //*[@id="talentsOptions"]/tbody/tr[2]/td[3]/table/tbody/tr[1]/td[3]/text()
        talent_options = self.find_elements(By.XPATH, "//*[@id='talentsOptions']//tbody")
        """
        'Tvoje zlato: 173.474   Pekelné kamene: 0\nZobraz filter: 
        \nVšetky naučené talenty\nNaučiteľné talenty\nVšetky talenty\n                             
        Voľné body:\n0\nPoužité body:\n11\nMaximálne body:\n13\nĎalšie body\nÚroveň: 64\n+2\n  
        ďalší bod: 40.131\nVynulovanie ceny v zlate a znovu naučenie všetkých talentov: 19\n
        Vynulovať všetky body: 500\nVynulovať jeden talent: 2'
        """
        if not talent_options:
            log.error("No talents")
            return
        free_points = re.search('Voľné body:\n(\d+)', talent_options[0].text)
        used_points = re.search('Použité body:\n(\d+)', talent_options[0].text)
        max_points = re.search('Maximálne body:\n(\d+)', talent_options[0].text)
        next_level = re.search('Ďalšie body\nÚroveň: (\d+)', talent_options[0].text)
        next_point_cost = re.search('ďalší bod: ([\d\.]+)', talent_options[0].text)

        if not all([free_points, used_points, max_points, next_point_cost, next_level]):
            log.error("Not all vars in talents were found")
            return

        free_points = int(free_points.group(1))
        used_points = int(used_points.group(1))
        max_points = int(max_points.group(1))
        next_level = int(next_level.group(1))
        next_point_cost = int(next_point_cost.group(1).replace('.', ''))

        if free_points > 0:
            # select talent
            talents = self.find_elements(By.XPATH, "//*[@id='specialSkills']//td[@class='talent_buyable']")
            if not talents:
                log.error("No talents found")
                return
            for talent in talents:
                if talent.text in self.desired_talents:
                    log.warning(f"Activating new talent {talent.text}")
                    talent_href = talent.find_element(By.CLASS_NAME, "buytalent").get_attribute('href')
                    self.get(talent_href)
                    return
            log.warning("No desired talents to activate...")
            return
        elif used_points < max_points:
            # buy talent point
            if self.gold >= next_point_cost:
                self.find_element(By.NAME, "buypoint").click()
                self.talents()
            else:
                log.warning(f"Not enough gold for talent point {self.gold} < {next_point_cost}")
                return
        elif used_points == max_points:
            # there is nothing to do, wait for level up
            log.warning(f"All point were used. additional points will be available at level {next_level}")
            return



    def get_energy_potion(self):
        #//*[@id="items"]/div[2]/div/div/h2[1]
        self.get(self.URL + '/profile')
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down
        # expand item tab
        my_active_items_table = self.find_elements(By.XPATH, "//*[@id='items']//h2")
        for active in my_active_items_table:
            if 'Aktívne' not in active:
                continue

    def end(self):
        pass


# ----------------------------------------------------------------------------------------------------------

if platform.system() == 'Linux':
    from pyvirtualdisplay import Display

pwd = os.path.abspath(os.curdir)


class VirtualDisplay:
    def __init__(self, plt) -> None:
        if 'Ubuntu 22.04 LTS' in platform.freedesktop_os_release().values():
            return
        if plt == 'Linux':
            log.info('Running LINUX !!!')
            self.display = Display(visible=0, size=(1280, 1024))
            self.display.start()
        pass

    def __enter__(self):
        if 'Ubuntu 22.04 LTS' in platform.freedesktop_os_release().values():
            log.info("Running UBUNTU skip virtual display")
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


# ----------------------------------------------------------------------------------------------------------

def main():
    with VirtualDisplay(platform.system()):
        bot = BraveBot()
        bot.get_main_page()
        bot.login()
        err_counter = 0
        MIN_ENERGY = 0.09
        MIN_ENERGY_ADVENTURE = 0.35
        repeat_flag = False
        no_action_count = 0
        while True:
            try:
                log.info(" START loop ".center(100, "-"))
                if 'Vlož svoje meno a heslo pre prihlásenie' in bot.page_source:
                    bot.get_main_page()
                    bot.login()
                    bot.get_player_info()

                # ----------------------------------------------------------------------------------------
                bot.get_player_info()
                bot.shop_item()
                bot.sell_item()
                if not bot.focused_items:
                    bot.hideout()
                    bot.talents()
                if bot.check_if_work_in_progress():
                    log.info(f"working for {bot.t_delta.seconds} seconds")
                    sleep(bot.t_delta.seconds)
                # ----------------------------------------------------------------------------------------
                # try to heal up
                bot.get_player_info()
                if bot.energy < 0.2:
                    log.warning("Low energy...TRY ro heal...".center(50, "-"))
                    bot.get_healing()
                    bot.get_player_info()
                # ----------------------------------------------------------------------------------------

                if bot.ap[0] == 0 or no_action_count > MAX_NO_ACTION():
                    if no_action_count > MAX_NO_ACTION():
                        log.warning("No action performed in 10 loops...Going grave")
                        grave_time = "0:30"
                    elif bot.energy >= 0.5:
                        log.info(f"going grave SHORT - AP: {bot.ap[0]:} ENERGY: {bot.energy:}")
                        grave_time = "0:30"
                    elif 0.5 > bot.energy > 0.3:
                        log.info(f"going grave MID - AP: {bot.ap[0]:} ENERGY: {bot.energy:}")
                        grave_time = "1:30"
                    else:
                        log.info(f"going grave LONG - AP: {bot.ap[0]:} ENERGY: {bot.energy:}")
                        grave_time = "2:30"

                    bot.get_player_info()
                    if bot.focused_items:
                        bot.shop_item(buy_only=True)
                    bot.go_grave(w=grave_time)
                    bot.check_if_work_in_progress()
                    log.info(f"working for {bot.t_delta.seconds} seconds")
                    sleep(bot.t_delta.seconds)
                    _after_action_strategy(bot)

                # ----------------------------------------------------------------------------------------
                # randomly choose actions: hunt, cavern ...:
                choice = random.choice(['hunt', 'cavern', 'cavern', 'adventure', 'adventure', 'adventure'])
                bot.get_player_info()
                bot.check_overview()
                if bot.adventure_in_progress:
                    log.info("Adventure in progress... SELECT ADVENTURE")
                    choice = 'adventure'
                elif bot.action_focus:
                    log.info(f"Action in focus: {bot.action_focus}")
                    choice = bot.action_focus[0]
                elif choice == 'adventure':
                    pass
                elif bot.ap[0] / bot.ap[1] < bot.energy:
                    log.info(f"we have more energy {bot.energy} than ap {bot.ap[0] / bot.ap[1]}...")
                    choice = 'cavern'
                else:
                    log.info(f"we have LESS energy {bot.energy} than ap {bot.ap[0] / bot.ap[1]}...")
                    choice = 'hunt'
                # ----------------------------------------------------------------------------------------
                if choice == 'hunt':
                    if bot.ap[0] >= 1 and bot.energy >= MIN_ENERGY:
                        no_action_count = 0
                        log.info(f"bot AP is {bot.ap[0]} >= 1 e: {bot.energy}--- we are going for HUNT")
                        if bot.level > 30:
                            bot.go_hunt(target="Mesto")
                        else:
                            bot.go_hunt(target="Dedina")
                        _after_action_strategy(bot)
                # ----------------------------------------------------------------------------------------
                elif choice == 'cavern':
                    if bot.ap[0] >= 1 and bot.energy >= MIN_ENERGY:
                        no_action_count = 0
                        log.info(f"bot AP is {bot.ap[0]} >= 1 e: {bot.energy} --- we are going for DAEMONS")
                        bot.go_daemons()
                        _after_action_strategy(bot)and not bot.check_if_work_in_progress()
                # ----------------------------------------------------------------------------------------
                elif choice == 'adventure':
                    log.info("Adventure wos chosen")
                    if bot.ap[0] >= 3 and bot.energy > MIN_ENERGY_ADVENTURE:
                        pass
                    else:
                        if bot.adventure_in_progress:
                            log.warning("We have active adventure, but it is not possible to continue...")
                            bot.do_adventure(finish=True)
                    while bot.ap[0] >= 3 and bot.energy > MIN_ENERGY_ADVENTURE:
                        no_action_count = 0
                        log.info(f"bot AP is {bot.ap[0]} >= 3 --- we are going for ADVENTURE")
                        bot.get_player_info()
                        bot.do_adventure()
                        _after_action_strategy(bot)

                if bot.ap[0] >= 1 and MIN_ENERGY >= bot.energy >= 0.03:
                    log.info(f"bot AP is {bot.ap[0]} >= 1 e: {bot.energy}--- we are going for HUNT with low energy")
                    # if bot.energy <= 0.05:
                    #     log.warning("too low energy")
                    #     continue
                    no_action_count = 0
                    if bot.ap[0] >= 2:
                        bot.go_hunt(target="Mesto")
                    if bot.ap[0] >= 1:
                        bot.go_hunt(target="Dedina")
                    _after_action_strategy(bot)

                no_action_count += 1
                log.warning(f"{no_action_count}")
                log.info(" end loop ".center(100, "-"))

            except Exception as e:
                log.error(f"Error in main loop !\n{e} {traceback.format_exc()}")
                err_counter += 1
                if err_counter >= 10:
                    if repeat_flag:
                        sleep(60)
                    try:
                        bot.logout()
                        bot.get_main_page()
                        bot.login()
                    except Exception as ee:
                        log.error(f"Exc in EXC: {ee} {traceback.format_exc()}")
                    err_counter = 0
                    repeat_flag = True


def MAX_NO_ACTION():
    return 10


def _after_action_strategy(bot):
    bot.get_player_info()
    if not bot.focused_items:
        bot.stats_increase()
    else:
        bot.shop_item(buy_only=True)


if __name__ == '__main__':
    main()
