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
    URL = "https://s23-sk.bitefight.gameforge.com/profile"
    USER = cred.USER
    PWD = cred.PWD
    players = {}

    def __init__(self):
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
        self.get(URL)

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
            return energy

    def go_hunt(self, target='Farma', r=1):
        self.find_element(By.LINK_TEXT, "Lov").click()
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.find_element(By.LINK_TEXT, "Lov").click()
            # if "profile/index" not in self.current_url:
            #     self.get_main_page()
            # target = self.find_element(By.XPATH, ".//*[@id='humanHunting']//button[contains(.,'Farma')]")
            _target = self.find_element(By.XPATH, f".//*[@id='humanHunting']//button[contains(.,'{target}')]")
            # target = self.find_element(By.XPATH, ".//*[@id='humanHunting']//button[contains(.,'Dedina')]")
            self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            _target.click()
            log.info(self.find_elements(By.XPATH, f"//p")[-1].text)
        return True


    def select_hunt(self):
        self.find_element(By.LINK_TEXT, "Lov").click()
        return self.check_if_work_in_progress()

    def check_if_work_in_progress(self):
        if 'working' in self.current_url:
            # log.info(f"Work in progress...")
            log.info(f"Work in progress...")
            self.t_delta = self.get_countdown()
            # log.info(f"Remaining time {self.t_delta}")
            log.info(f"Remaining time {self.t_delta}")
            return True
        return False

    def go_grave(self, w='0:30'):
        self.find_element(By.LINK_TEXT, "Mesto").click()
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.find_element(By.LINK_TEXT, "Cintorín").click()
        if not self.check_if_work_in_progress():
            work_time = self.find_element(By.XPATH, "//select[contains(@name,'workDuration')]")
            work_time.send_keys(w)
            self.find_element(By.XPATH, "//input[contains(@name,'dowork')]").submit()
            return True

    def go_daemons(self, r=1, level=None):
        self.find_element(By.LINK_TEXT, "Mesto").click()
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.find_element(By.LINK_TEXT, "Jaskyňa").click()
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.find_element(By.LINK_TEXT, "Mesto").click()
            self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.find_element(By.LINK_TEXT, "Jaskyňa").click()
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
        self.find_element(By.LINK_TEXT, "Lov").click()
        if self.check_if_work_in_progress():
            return False
        for repeat in range(r):
            self.find_element(By.LINK_TEXT, "Lov").click()
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

        # get values
        """//*[@id="skills_tab"]/div[2]/div/div/table/tbody/tr[3]/td[2]/div[2]/table/tbody/tr[5]/td[2]"""

        for repeat in range(r):
            if "profile/index" not in self.current_url:
                self.get_main_page()
            self.find_element(By.LINK_TEXT, "Schopnosti").click()
            try:
                for idx in range(4):
                    stats = self.find_elements(By.XPATH, "//img[contains(@src,'iconplus')]")
                    if st and 'inactiv' not in stats[st].get_attribute('outerHTML'):
                        stats[st].click()
                        break
                    elif not st and 'inactiv' not in stats[idx].get_attribute('outerHTML'):
                        stats[idx].click()
                    else:
                        log.info("no more gold")
                        break
            except IndexError:
                log.info("no more gold")
                break

    def get_ap(self):
        """'(0/0)7.212    0    15    19 / 124    21.330 / 34.100     10    208'"""
        if "profile/index" not in self.current_url:
            self.get_main_page()
        ap = self.find_elements(By.XPATH, "//*[@id='infobar']")
        ap = re.search('.* (\d+ \/ \d+).*', ap[0].text).group(1).split(' / ')
        return list(map(int, ap))

    def get_gold(self):
        if "profile/index" not in self.current_url:
            self.get_main_page()
        gold = self.find_element(By.XPATH, "//*[@id='infobar']").text
        gold = re.search('.*\n([\d\.]+) .*', gold).group(1).replace('.', '')
        return int(gold)

    def do_adventure(self):
        import random
        ss = True
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
                continue
            log.info(f"{ss} {rnd.text}")
            rnd.click()

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
        gold = bot.get_gold()
        ap = bot.get_ap()
        energy = bot.get_energy()
        while True:
            try:
                if 'Vlož svoje meno a heslo pre prihlásenie' in bot.page_source:
                    bot.get_main_page()
                    bot.login()
                    ap = bot.get_ap()
                    energy = bot.get_energy()
                if ap[0] == 0 or (energy[0] / energy[1]) < 0.09:
                    log.info(f"going grave {ap[0]:} {energy[0]:}")
                    bot.go_grave()
                    sleep(30*60+1)
                if not bot.go_hunt():
                    sleep(bot.t_delta.seconds)
                bot.stats_increase()
                ap = bot.get_ap()
                energy = bot.get_energy()
                log.info(bot.get_gold())
            except Exception as e:
                log.error(f"{e}")




if __name__ == '__main__':
    main()