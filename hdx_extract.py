# - * - coding: utf-8 - * -
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from selenium import webdriver
import shutil, zipfile, winsound, re, time, requests, os, sys, csv



def hdx(country, formats_list, organizations, query):
    #Create HDX configuration
    Configuration.create(hdx_site='prod', user_agent='Whoever', hdx_read_only=True)
    #Lists
    datasets_ids_list = []
    organizations_names_list = []
    total_resources_downloaded = 0
    failed_resources = []
    start_dir = fr"{directory}\HDX"
    os.mkdir(start_dir)
    #Get Data
    for org in organizations:
        for frmt in formats_list:
            datasets = Dataset.search_in_hdx(query=query, sort='metadata_created desc', fq_list=[f'groups:{country}', f'res_format:{frmt}', f'organization:{org}'])
            for dataset in datasets:
                if dataset.get('id') in datasets_ids_list:
                    continue
                else:
                    print(f'Analyzing Dataset: {dataset.get("title")}...')
                    datasets_ids_list.append(dataset.get('id'))
                    organization_name = dataset.get('organization').get('name')
                    if organization_name not in organizations_names_list:
                        print(f'New Organization detected: {organization_name}....')
                        organizations_names_list.append(organization_name)
                        os.mkdir(f'{start_dir}\{organization_name}')
                    cur_dataset_resources_list = dataset.get_resources()
                    for resource in cur_dataset_resources_list:
                        if resource.get('format') == frmt: #eventhough the desired format was specified a priori, other formats will still show up in the dataset's list of resources, hence this if condition
                            try:
                                resource_name = resource.get("name")
                                _, path = resource.download(fr'{start_dir}\{organization_name}')
                                total_resources_downloaded += 1
                                print('Downloaded: ' + resource.get("name"))
                                #Remove erroneous extensions from zipped files, unzip and delete them
                                if path.endswith('.zip') == False:
                                    clean_zip_name = re.compile(r'\.\w+$').sub('.zip', path)
                                    shutil.move(path, clean_zip_name)
                                else:
                                    clean_zip_name = path
                                with zipfile.ZipFile(clean_zip_name) as f_zip:
                                    f_zip.extractall(clean_zip_name[:clean_zip_name.index('.zip')])
                                os.unlink(clean_zip_name)
                            except:
                                failed_resources.append(resource_name+'\n')                  
    with open(fr'{start_dir}\failed resources.txt', 'w', encoding='utf-8') as txt:
        txt.writelines(['The following resources could not be downloaded:\n'] + failed_resources)
    print(f'Total files downloaded was: {total_resources_downloaded}.\nPlease refer to the failed resources TXT file for a list of resources that were not downloaded.')
    winsound.Beep(440, 3000)

#************************************************************

#These codes ain't in Humdata yet. Get them for each village from MIMUs website.
def get_new_codes_mimu():
    print('Getting Villge codes from MIMU...\n')
    start_dir = fr"{directory}\HDX\MIMU"
    os.chdir(start_dir)
    if 'firefox' in variables[0]['Path'].lower():
        browser_options = webdriver.FirefoxOptions()
        browser_options.add_argument("--private")
        browser = webdriver.Firefox(options=browser_options, executable_path=variables[1]['Path'])
    #For Chrome
    else:
        browser_options = webdriver.ChromeOptions()
        browser_options.add_argument("--incognito")
        browser = webdriver.Chrome(options=browser_options, executable_path=variables[1]['Path'])
    browser.get('https://themimu.info/place-codes')
    browser.find_element_by_id('pcode-datasets').click()
    pages = browser.find_elements_by_tag_name('#pcode-datasets span a[tabindex]')
    for i in range(len(pages)):
        results = browser.find_elements_by_tag_name('#pcode-datasets a[href]')
        for result in results:
            url = result.get_attribute('href')
            zip_name = re.compile(r'([^/]+)$').search(url).group(1)
            zip_path = fr'{start_dir}\{zip_name}'
            zip_request = requests.get(url)
            #Create the Zip
            with open(zip_path, 'wb') as f:
                for chunk in zip_request.iter_content():
                    if chunk:
                        f.write(chunk)
            #Extract and delete it
            with zipfile.ZipFile(zip_path) as f_zip:
                f_zip.extractall(zip_path[:zip_path.index('.zip')])
            os.unlink(zip_path)
        if i != len(pages)-1:
            browser.find_element_by_tag_name('#pcode-datasets a.next.paginate_button').click()
    browser.close()
    print('Finished downloading codes from MIMU')
#******************************************************************


directory = re.compile(r'(.*)\\[^\\]*$').search(sys.argv[0]).group(1)
#Get variables paths
with open(fr'{directory}\Variables.txt', 'r', encoding='utf-8', newline='') as txt:
    reader = csv.DictReader(txt, delimiter=',')
    fieldnames = reader.fieldnames
    variables = tuple(reader)
for row in variables:
    if row['Path'] == '':
        sys.exit('Missing variable paths. Please fill out Variables.txt first.')




hdx(country='mmr', formats_list=['Geopackage', 'SHP'], organizations=('mimu', 'unosat', 'hot'), query='Rakhine')
get_new_codes_mimu()