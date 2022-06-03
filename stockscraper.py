#Inisiasi library
import requests
import pandas as pd
import time
from datetime import datetime, date, timedelta
import re
import json
import os
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from glob import glob
from tqdm import tqdm
pd.options.mode.chained_assignment = None

def getdate():
   print('getting date...')
   #Mengambil tanggal hari ini
   today = date.today()
   #Mengambil tanggal hari kerja terakhir (termasuk hari ini)
   if date.weekday(today) == 5:
       akhir = today - timedelta(days = 1)
   elif date.weekday(today) == 6:      
       akhir = today - timedelta(days = 2)
   else:
       akhir = today
   #Mengambil tanggal 5 hari kerja sebelumnya (termasuk hari ini)
   awal = (akhir - pd.tseries.offsets.BDay(4)).date()
   #Mengubah format datetime ke dalam bentuk string
   awal = awal.strftime("%Y_%m_%d")
   akhir = akhir.strftime("%Y_%m_%d")
   return (awal, akhir)

def getsector():
    print('getting sector...')
    #Menginstall driver browser untuk Selenium
    browser = webdriver.Chrome(ChromeDriverManager().install())
    #Menggunakan Selenium untuk membuka website
    browser.get('https://www.idx.co.id//umbraco/Surface/Helper/GetSectors')
    content = browser.find_element(By.TAG_NAME, "pre").text
    #Menutup browser
    browser.close()
    #Mengubah text ke dalam bentuk json
    namasektor = json.loads(content)
    return namasektor

def getstocklist():
    print('getting stocklist...')
    namasektor = getsector()
    sektor = [x.replace(' ', '%20') for x in namasektor]
    DaftarSaham = pd.DataFrame()
    if not os.path.exists('IHSGstockdata\\'):
        os.mkdir('IHSGstockdata\\')
    browser = webdriver.Chrome(ChromeDriverManager().install())
    for i,x in enumerate(sektor): 
        #Menggunakan Selenium untuk membuka website
        browser.get('https://www.idx.co.id/umbraco/Surface/StockData/GetSecuritiesStock?code=        &sector='+x+'&board=&draw=3&columns[0][data]=Code&columns[0][name]=        &columns[0][searchable]=true&columns[0][orderable]=false&columns[0][search][value]=        &columns[0][search][regex]=false&columns[1][data]=Code&columns[1][name]=        &columns[1][searchable]=true&columns[1][orderable]=false&columns[1][search][value]=        &columns[1][search][regex]=false&columns[2][data]=Name&columns[2][name]=        &columns[2][searchable]=true&columns[2][orderable]=false&columns[2][search][value]=        &columns[2][search][regex]=false&columns[3][data]=ListingDate&columns[3][name]=        &columns[3][searchable]=true&columns[3][orderable]=false&columns[3][search][value]=        &columns[3][search][regex]=false&columns[4][data]=Shares&columns[4][name]=        &columns[4][searchable]=true&columns[4][orderable]=false&columns[4][search][value]=        &columns[4][search][regex]=false&columns[5][data]=ListingBoard&columns[5][name]=        &columns[5][searchable]=true&columns[5][orderable]=false&columns[5][search][value]=        &columns[5][search][regex]=false&start=0&length=1000&search[value]=        &search[regex]=false&_=1649584456297')
        #Mengambil semua text yang ada di webpage
        content = browser.find_element(By.TAG_NAME, "pre").text
        #Mengubah text ke dalam bentuk json
        parsed_json = json.loads(content)
        #Mengubah json ke dalam bentuk DataFrame
        df = pd.DataFrame(parsed_json['data'])
        #Mengubah format tanggal menjadi datetime
        df['ListingDate'] = [datetime.strptime(x[:10], '%Y-%m-%d') for x in df['ListingDate']]
        df['Sector'] = namasektor[i]
        df['ListingBoard'] = [x.capitalize() for x in df['ListingBoard']]
        #Menghapus kolom 'Links'
        df.drop(['Links'], axis=1, inplace=True)
        DaftarSaham = DaftarSaham.append(df)
    #Menutup browser
    browser.close()
    # urut berdasarkan kode saham
    DaftarSaham = DaftarSaham.sort_values(by='Code').reset_index(drop=True)
    if os.path.exists('IHSGstockdata\\DaftarSaham.csv'):
        olddata = pd.read_csv('IHSGstockdata\\DaftarSaham.csv')
        tambah=pd.DataFrame(columns=DaftarSaham.columns)
        for i,data in enumerate(DaftarSaham['Code']):
            if data not in olddata['Code'].values:
                tambah = tambah.append(DaftarSaham.iloc[i])
        try:
            tambah['ListingDate'] = tambah['ListingDate'].dt.strftime('%Y-%m-%d')
        except:
            pass
        olddata = olddata.append(tambah, ignore_index=True)
        olddata = olddata.sort_values(by='Code').reset_index(drop=True)
        return olddata
    else:
        return DaftarSaham

def getcookiecrumb():
    print('getting cookie and crumb...')
    #Mengambil crumb dan cookies dengan cara visit yahoo finance satu kali
    #Deklarasi url yang akan di visit
    url = 'https://finance.yahoo.com/quote/AALI.JK?p=AALI.JK&.tsrc=fin-srch'
    with requests.session():
        #deklarasi header untuk request
        header = {'Connection': 'keep-alive',
                    'Expires': '-1',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) \
                    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
                    }   
        #Mengunjungi website
        website = requests.get(url, headers=header)
        #Mengambil crumb
        crumb = re.findall('"CrumbStore":{"crumb":"(.+?)"}', str(website.text))[0]
        #Mengambil cookies
        cookies = website.cookies
        #Mengambil jam buka dan jam tutup bursa saham
        website = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/AALI.JK?&range=5d&useYfid=true',                                   '&interval=1m&includePrePost=true&events=div|split|earn&lang=en-US&region=US&crumb='+crumb+
                                   '&corsDomain=finance.yahoo.com', headers = header, cookies = cookies).text
        site_json=json.loads(website)
        tradingperiod = site_json['chart']['result'][0]['meta']['tradingPeriods']['regular'][0]
        return (header, cookies, crumb, tradingperiod)

# "validRanges":["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"]
def getstockdata(DaftarSaham, header:dict, cookies, crumb:str, awal:str, akhir:str):
    print('getting stock data...')
    error=[]
    if not os.path.exists('IHSGstockdata\\minutesdata\\'):
        os.mkdir('IHSGstockdata\\minutesdata\\')
    if not os.path.exists('IHSGstockdata\\minutesdata\\'+awal+'-'+akhir+'\\'):
        os.mkdir('IHSGstockdata\\minutesdata\\'+awal+'-'+akhir+'\\')
    #Melakukan looping untuk mengambil semua data saham
    for kode_emiten in tqdm(DaftarSaham['Code']):
        try:
    #         print('scraping', kode_emiten)
            #Membuka website dengan crumb dan cookies yang sudah didapatkan sebelumnya
            website = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/'+kode_emiten+'.JK?&range=5d&useYfid=true',                                   '&interval=1m&includePrePost=true&events=div|split|earn&lang=en-US&region=US&crumb='+crumb+
                                   '&corsDomain=finance.yahoo.com', headers = header, cookies = cookies).text
            #Mengubah text yang didapatkan dari request ke dalam bentuk json
            site_json=json.loads(website)
            #Menentukan lokasi data saham (open, low, high, close, volume)
            stockdata = site_json['chart']['result'][0]['indicators']['quote'][0]
            #Melakukan transformasi data dari json ke DataFrame
            stockdf = pd.DataFrame(list(zip([datetime.fromtimestamp(x).strftime("%x %X") for x in site_json['chart']['result'][0]['timestamp']],
                                  stockdata['open'], stockdata['low'], stockdata['high'], stockdata['close'],
                                  stockdata['volume'])), columns =['timestamp', 'open', 'low', 'high', 'close', 'volume'])
            #Mengisi data yang kosong/NaN dengan 0
            stockdf.fillna(0, inplace=True)
            #Mengubah tipe data kolom timestamp menjadi datetime
            stockdf['timestamp'] = pd.to_datetime(stockdf['timestamp'])
            #Mengubah tipe data kolom open, low, high, close, dan volume menjadi integer
            stockdf[['open', 'low', 'high', 'close', 'volume']] = stockdf[['open', 'low', 'high', 'close', 'volume']].astype('int64')
            #Menyimpan data saham ke dalam bentuk csv
            stockdf.to_csv('IHSGstockdata\\minutesdata\\'+awal+'-'+akhir+'\\'+kode_emiten+'.csv',index=False)
        except:
            error.append(kode_emiten)
            continue
    print('Daftar scraping saham yang error: \n', error)

def cleandata(awal:str, akhir:str, tradingperiod):
    print('cleaning data...')
    DaftarSaham = pd.read_csv('IHSGstockdata\\DaftarSaham.csv')
    lastdata = glob('IHSGstockdata\\minutesdata\\'+awal+'-'+akhir+'\\*.csv')
    for i,data in tqdm(enumerate(lastdata)):
        kode_emiten = data[-8:-4]
        stockdf = pd.read_csv(data)
        tanggal= pd.bdate_range(start=datetime.strptime(awal,"%Y_%m_%d"), end=datetime.strptime(akhir,"%Y_%m_%d")+timedelta(days=1), freq='1T')
        startperiod = datetime.utcfromtimestamp(tradingperiod[0]['start']+25200).strftime('%H:%M')
        endperiod = datetime.utcfromtimestamp(tradingperiod[0]['end']+25200-60).strftime('%H:%M')
        tanggal = tanggal[tanggal.indexer_between_time(startperiod,endperiod)]
        tanggal = tanggal.strftime("%Y-%m-%d %H:%M:%S")
        tanggal = tanggal.to_list()
        emptydf = pd.DataFrame(columns={'timestamp':'','open':'','low':'','high':'','close':'','volume':''})
        emptydf['timestamp'] = tanggal
        result = pd.concat([stockdf, emptydf], ignore_index=True, sort=False)
        result.drop_duplicates(subset=['timestamp'], keep='first', inplace=True)
        result = result.sort_values(by=['timestamp']).fillna(0).reset_index(drop=True)
        x=0
        while result['close'][x]==0:
            x+=1
        for i in range(x):
            result['open'][i] = result['open'][x]
            result['low'][i] = result['low'][x]
            result['high'][i] = result['high'][x]
            result['close'][i] = result['close'][x]
        for i in range(x, len(result['timestamp'])):
            if result['close'][i]==0:
                result['open'][i] = result['open'][i-1]
                result['low'][i] = result['low'][i-1]
                result['high'][i] = result['high'][i-1]
                result['close'][i] = result['close'][i-1]
        result = result.loc[((result.timestamp.isin(emptydf['timestamp'])))]
        listingdate = DaftarSaham.loc[DaftarSaham['Code']==kode_emiten]['ListingDate'].values[0]
        result = result.loc[result['timestamp']>=listingdate].reset_index(drop=True)
        result.to_csv('IHSGstockdata\\minutesdata\\'+awal+'-'+akhir+'\\'+kode_emiten+'.csv',index=False)

def appenddata(awal:str, akhir:str):
    print('appending data...')
    lastdata = glob('IHSGstockdata\\minutesdata\\'+awal+'-'+akhir+'\\*.csv')
    if not os.path.exists('IHSGstockdata\\minutes\\'):
        os.mkdir('IHSGstockdata\\minutes\\')
    for i,data in tqdm(enumerate(lastdata)):
        kode_emiten = data[-8:-4]
        stockdf = pd.read_csv(data)
        if os.path.exists('IHSGstockdata\\minutes\\'+kode_emiten+'.csv'):
            df = pd.read_csv('IHSGstockdata\\minutes\\'+kode_emiten+'.csv')
            result = pd.concat([stockdf, df], ignore_index=True, sort=False)
            result.drop_duplicates(subset=['timestamp'], keep='first', inplace=True)
            result = result.sort_values(by=['timestamp']).fillna(0).reset_index(drop=True)
            result.to_csv('IHSGstockdata\\minutes\\'+kode_emiten+'.csv', mode='w', index=False, header=True)
        else:
            stockdf.to_csv('IHSGstockdata\\minutes\\'+kode_emiten+'.csv', mode='w', index=False, header=True)

def addextra():
    print('adding extra data to stocklist...')
    DaftarSaham = pd.read_csv('IHSGstockdata\\DaftarSaham.csv')
    lastprice=[]
    marketcap=[]
    firstadded=[]
    lastupdated=[]
    lastdata = list(map(lambda x: x[-8:-4] ,glob('IHSGstockdata\\minutes\\*.csv')))
    for kode_emiten in tqdm(DaftarSaham['Code']):
        if kode_emiten in lastdata:
            stockdf = pd.read_csv('IHSGstockdata\\minutes\\'+kode_emiten+'.csv')
            firstadded.append(stockdf['timestamp'].iloc[0])
            lastupdated.append(stockdf['timestamp'].iloc[-1])
            lastprice.append(stockdf['close'].iloc[-1])
            marketcap.append(stockdf['close'].iloc[-1]*DaftarSaham.loc[DaftarSaham['Code']==kode_emiten]['Shares'].values[0])
        else:
            lastprice.append('')
            marketcap.append('')
            firstadded.append('')
            lastupdated.append('')
    DaftarSaham['LastPrice'] = lastprice
    DaftarSaham['MarketCap'] = marketcap
    DaftarSaham['MinutesFirstAdded'] = firstadded
    DaftarSaham['MinutesLastUpdated'] = lastupdated
    DaftarSaham.to_csv('IHSGstockdata\\DaftarSaham.csv',index=False)

if __name__ == "__main__":
    awal, akhir = getdate()
    print(awal, akhir)
    DaftarSaham = getstocklist()
    DaftarSaham.to_csv('IHSGstockdata\\DaftarSaham.csv',index=False)
    header, cookies, crumb, tradingperiod = getcookiecrumb()
    getstockdata(DaftarSaham, header, cookies, crumb, awal, akhir)
    cleandata(awal, akhir, tradingperiod)
    appenddata(awal, akhir)
    addextra()