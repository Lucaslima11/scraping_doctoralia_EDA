from selenium import webdriver 
from selenium.webdriver.chrome.service import Service as ChromeService 
from webdriver_manager.chrome import ChromeDriverManager 
from selenium.webdriver.common.by import By
import pandas as pd
import numpy as np

SUBPAGES = [
            '&tab=profile-info',
            '&tab=profile-pricing',
            '&tab=profile-reviews',
            '&tab=profile-questions',
            '&tab=profile-experience'
            ]

NO_RELATED_WORKS = ['Acupuntura',
                    'Primeira consulta Terapias Complementares e Alternativas',
                    'Constelação sistêmica familiar',
                    'Aconselhamento para familiares de dependentes químicos',
                    'Atendimento online em coaching',
                    'Consulta sexologia',
                    'Consulta Psiquiatra',
                    'Primeira consulta Psiquiatria',
                    'Hipnose',
                    'Consulta Psicopedagogia',
                    'Alfabetização',
                    'Avaliação em Terapias Integrativas e Complementares'
                    ]

class DetailProfile:

    def __init__(self, dataframe_pages):
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        self.driver.implicitly_wait(5)
        self.psi_profile = {}
        self.psi_pages = dataframe_pages

    def _services_prices(self):
        try:
            prices = self.driver.find_elements(By.XPATH, "//div[@class='media-body text-muted']//descendant::span[@data-id='service-price']")
            services = self.driver.find_elements(By.XPATH, "//div[@class='media-body text-muted']//descendant::p[@data-test-id='address-service-item']")

            self.service_price = [[service.text, price.text][0].split('•') for service, price in zip(services, prices) \
                            if (service.text, price.text) != ('','') or service.text !='']
        except Exception as e:
            self.service_price = [None, None]
            print('Error in service price:', e)
    
    def _accept_insurance(self):
        try:
            inss = self.driver.find_elements(By.XPATH, "//div[@data-id='check-your-insurance-vue']//descendant::div[@class='media-body']/p")

            self.acc_ins = [ins.text for ins in inss if ins.text != '']
        except Exception as e:
            self.acc_ins = 'Sem info'
            print('Error in insurance:', e)
    
    def _patient_age(self):
        try:    
            allowed = self.driver.find_elements(By.XPATH, "//div[@data-test-id='doctor-address-allowed-patients']//descendant::span")

            self.patient = [allow.text for allow in allowed if allow.text != '']
        except Exception as e:
            self.patient = 'Sem info'
            print('Error in patient allowed:', e)
    
    def _run_profile(self):
        for index, profile in self.dataframe_pages.iterrows():
            self.driver.get(profile['link']+ SUBPAGES[0])
            self._services_prices()
            self._accept_insurance()
            self._patient_age()
            self.psi_pages[profile['id']]=[self.service_price, self.acc_ins, self.patient]
    
    def psi_profile_df(self, columns = ['id','service','insurance','patient_range']):
        psi = pd.DataFrame(self.psi_pages).T.reset_index()
        psi.columns = columns
        return psi
    

class CleanDFProfile:

    def __init__(self, dataframe):
        self.dataframe = dataframe
        self._rearange_services()
        self._clean_service_price()
        self._define_insurance_coverage()
        self._attend_age()
    
    def _rearange_services(self):
        self.dataframe['service'] = self.dataframe['service'].replace({'[]':'N/A'})\
                                                    .str.replace("^\[|\[''],|]$|\s\W\d{1,}\s\w+", '', regex=True)\
                                                    .str.strip()\
                                                    .str.replace("['']", 'N/A')\
                                                    .str.split('],')

        self.dataframe = self.dataframe.explode('service')
        self.dataframe['service'] = self.dataframe.service.str.split(',')

        for index, row in self.dataframe.iterrows():
            if isinstance(row['service'], list):
                self.dataframe.loc[index, 'name_service'] = row['service'][0]
                if len(row['service'])>1:
                    self.dataframe.loc[index, 'price'] = row['service'][1]
    
    def _clean_service_price(self):
        self.dataframe['price'] = self.dataframe['price'].str.strip().str.extract(r'R\$\s(\d+)').astype(float)
        self.dataframe['name_service'] = self.dataframe['name_service'].str.replace(r"\[|\]|'",'', regex=True)\
                                                                    .str.replace(r'\(\w+.+\)','', regex=True)\
                                                                    .str.strip()
        self.dataframe['name_service'] = self.dataframe['name_service'].replace('N/A', np.NaN)
        self.dataframe = self.dataframe[~self.dataframe['name_service'].isin(NO_RELATED_WORKS)].reset_index(drop=True)
    
    def _define_insurance_coverage(self):
        conditions = [
            self.dataframe['insurance']=="['Aceita somente pacientes particulares (sem convênio médico) neste endereço']",
            self.dataframe['insurance']=="['Aceita pacientes particulares (sem convênio médico) e pacientes com convênio médico neste endereço']"
        ]
        selection = [0,1]
        self.dataframe['ins_coverage'] = np.select(conditions, selection, default=np.NaN)
    
    def _attend_age(self):
        self.dataframe['patient_range'] = self.dataframe['patient_range'].replace({0: np.NaN, "[]": np.NaN})
        self.dataframe.loc[self.dataframe['patient_range'].str.contains(r"adultos", na=False) ,'attend_adult'] = 1
        self.dataframe.loc[~self.dataframe['patient_range'].str.contains(r"adultos", na=False) ,'attend_adult'] = 0
        self.dataframe.loc[~self.dataframe['patient_range'].str.contains("crianças", na=False) ,'attend_child'] = 0
        self.dataframe.loc[self.dataframe['patient_range'].str.contains(r"crianças", na=False) ,'attend_child'] = 1

        self.dataframe['service_age'] = self.dataframe['patient_range'].str.extract(r'(\d+)')
        self.dataframe.loc[self.dataframe['patient_range'].str.contains('crianças de qualquer idade', na=False), 'service_age'] = 0
        self.dataframe.loc[(self.dataframe['attend_adult']==1)&(self.dataframe['attend_child']==0), 'service_age'] = 18


def merge_profile(df1, df2):
    psi_df = df1.merge(df2, how='left', on='id')
    return psi_df