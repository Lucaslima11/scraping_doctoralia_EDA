from selenium import webdriver 
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import SessionNotCreatedException
from webdriver_manager.chrome import ChromeDriverManager 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim

class MainProfile:

    def __init__(self):
        self.psi_page = {}
        options=Options()
        options.add_argument('--headless')

        while True:
            try:
                self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
                break
            except SessionNotCreatedException:
                continue
    
    @staticmethod
    def doctoralia_url(page:int):
        return f'https://www.doctoralia.com.br/psicanalista/rio-de-janeiro/{str(page)}'
    
    @staticmethod
    def x_path_principal_profile(list_number, *add):
        x_value = f"//*[@id='search-content']/ul/li[{list_number}]/div/div/div/div[1]/div[1]/div/div[2]"
        xpath = '/'.join([x_value,'/'.join([str(value) for value in add])])
        return xpath
    
    @staticmethod
    def x_path_card(list_number):
        xpath = f"//*[@id='search-content']/ul/li[{list_number}]/div/div/div"
        return xpath
    
    def _name_links(self, profile):
        elements = self.driver.find_elements(By.XPATH, self.x_path_principal_profile(profile, 'h3','a'))
        self.psi_text = self.driver.find_element(By.XPATH, "//span[@data-ga-label='Doctor Name']").text
        self.psi_link = self.driver.find_element(By.XPATH, )

        #self.psi_text = ''.join([element.text for element in elements])
        self.psi_links = ''.join([link.get_attribute('href') for link in elements])
    
    def _opinions_made(self, profile):
        opinions = self.driver.find_elements(By.XPATH, "self.x_path_principal_profile(profile, 'a','span')")
        self.opinion_given = ''.join([opinion.text for opinion in opinions]).split(' ')[0]
        self.star_given = ''.join([opinion.get_dom_attribute('data-score') for opinion in opinions])
    
    def _specs_psi(self, profile):
        specs = self.driver.find_elements(By.XPATH, self.x_path_principal_profile(profile, 'div', 'span','h4','span'))
        self.main_spec = ''.join([spec.text for spec in specs])

    def _badge_user(self, profile):
        hid_elem = self.driver.find_elements(By.XPATH, self.x_path_principal_profile(profile, 'div', 'span','span'))
        self.bagde = ''.join([badge.text for badge in hid_elem])
    
    def _address_attend(self, profile):
        cards = self.driver.find_elements(By.XPATH, self.x_path_card(profile))
        self.label_adr = cards[0].find_element(By.CLASS_NAME, 'text-truncate').text
        self.type_atend = [card.find_element(By.CLASS_NAME, "overflow-hidden").text.split('\n') for card in cards][0][-1]
        self.maps = cards[0].find_element(By.CLASS_NAME, 'overflow-hidden').find_element(By.CLASS_NAME, 'text-muted').get_attribute('href')
        
        try:
            self.num_adr = len(cards[0].find_element(By.TAG_NAME, 'ul').text.split('\n'))
        except:
            self.num_adr = 1

    def _run_profile(self, profiles):
        for profile in range(1, profiles+1):
            self._name_links(profile)
            self._opinions_made(profile)
            self._specs_psi(profile)
            self._badge_user(profile)
            #self._address_attend(profile)
            self.psi_page[self.psi_text] = [
                self.psi_links,
                self.opinion_given,
                self.star_given, 
                self.main_spec, 
                self.bagde,
                #self.num_adr,
                #self.label_adr,
                #self.type_atend,
                #self.maps
            ]
    
    def run_pages(self, pages, profiles=25):
        for page in range(1, pages+1):
            self.driver.get(self.doctoralia_url(page))
            self._run_profile(profiles)
    
    def psi_dataframe(self, columns = ['link',
                                       'reviews',
                                       'stars',
                                       'spec',
                                       'label',
                                       'addresses',
                                       'address_1',
                                       'type_address_1',
                                       'loc_address_1']):
        psi = pd.DataFrame(self.psi_page).T.reset_index(names='psicanalista').sort_index()
        psi.columns = columns
        psi['id'] = psi['link'].str.extract('(?:%5B|id=)(\d+)').astype('Int64')
        return psi
    
class CleanDF:
    
    def __init__(self, dataframe):
        self.dataframe = dataframe
        self._create_columns()
        self._locate_neighboor()
    
    def _create_columns(self):
        self.dataframe  = self.dataframe.replace(
                                                    {'reviews':'',
                                                    'stars':'',
                                                    'spec':'',
                                                    'label':'',
                                                    'address_1':'',
                                                    'type_address_1':''
                                                    },
                                            np.NaN)
        self.dataframe['type_address_1'] = self.dataframe['type_address_1'].str.upper()
        self.dataframe['lat'] = self.dataframe['loc_address_1'].str.extract(r'(-[2-3]{2}.[0-9]{5,})')
        self.dataframe['lon'] = self.dataframe['loc_address_1'].str.extract(r'(-[0-9]{2}.[0-9]{5,}$)')
        self.dataframe['lat_lon'] = self.dataframe.apply(lambda row:(row['lat'], row['lon']), axis=1)
    
    def _locate_neighboor(self):
        geolocator = Nominatim(user_agent='psi')
        self.dataframe['bairro'] = self.dataframe['lat_lon'].apply(lambda row: geolocator.reverse(row, zoom=14).address.split(',')[0])
        self.dataframe = self.dataframe.replace({'bairro':{
        'Corporate Executive Offices':'Barra da Tijuca',
        'Fazenda Parque Recreio':'Recreio dos Bandeirantes',
        'Office Park Center':'Jacarepaguá',
        'Freguesia (Jacarepaguá)':'Freguesia',
        'O2 Corporate & Offices': 'Barra da Tijuca',
        'Centro Metropolitano': 'Jacarepaguá',
        'Brookfield Place': 'Jacarepaguá',
        'Athaydeville': 'Barra da Tijuca'
        }})