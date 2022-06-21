# Myanmar Scripts (FINISH README!!!!)



During my master [thesis](https://estudogeral.uc.pt/handle/10316/99470) I had to obtain, clean and store geographic data on Myanmar.
Hence, I designed python procedures to automate these tasks, trying to adapt them to any geographical context as best I could.


## hdx_extract.py

### hdx
The [Humanitarian Data Exchange](https://data.humdata.org/) is an open repository set up by [OCHA](https://www.unocha.org/) that pools data from various Humanitarian organizations, allowing for a better dissemination of said data. The portal is indeed convenient and easy to use, but when large amounts of data with varying extensions spread over many datasets is what you’re after, it becomes easier to consume the data over an API. Hence, I developed a simple function that, making use of a [python wrapper](https://github.com/OCHA-DAP) of said API, would download data, namely Shapefiles and Geopackages, from [MIMU](http://themimu.info/), [UNOSAT](https://www.unitar.org/sustainable-development-goals/united-nations-satellite-centre-UNOSAT) and [HOT](https://www.hotosm.org/) for the state of Rakhine, in Myanmar, the main focal area of my thesis.
The previous defaults can all be changed directly in the function call in the script.
All the data will be placed in a folder titled ‘HDX’ in the python script’s directory, organizing the downloaded data in folders according to their original source. It will also produce a text file with the names of any datasets that might have been unsuccessfully downloaded.


### get_new_codes_mimu
Because at the time of writing of my thesis certain data from MIMU was only available at their website, I also designed a little function to get that XLSX data and add it to the HDX folder where the previously obtained datasets were stored.
Because this particular section of MIMU’s website was made up of dynamic Javascript, browser automation had to be employed in order to mimic user interaction.



## toGeoPackage.py
Given that large amounts of data were obtained from the previous procedure, I found it useful to work only with the portions of it pertaining to a specific area in the state of Rakhine, the township of Sittwe (စစ်တွေမြို့နယ်), a costal area not only prone to flooding, but also home to quite a few Rohingya shelters that house members of this ethnic group that did not migrate to Cox’s Bazar, in Bangladesh.

For a given directory, with or without intermediate levels, with shp and csv files within, select only those objects or portions of each csv/shp geometrically contained within a reference polygon object, saving said objects in a final geopackage.
Caveats:
- Start


vil_correct
Purpose:
Village Tracts, Villages and Wards layer have been merged as 3 different layers of the same geopackage to allow the creation of temporary layers via SQL queries.


## Warnung:
Please fill out the Variables.txt before running this program.

Please check the requirements file to make sure you meet the necessary dependencies to run this program. Otherwise, open command prompt and: pip install -r "C:\path\to\requirements.txt"

You will need Microsoft Excel.

You will need browser automation software. If you use Chrome please get it [here](https://chromedriver.storage.googleapis.com/index.html?path=102.0.5005.61/) or if you prefer Firefox you can find it [here](https://github.com/mozilla/geckodriver/releases/tag/v0.31.0).

You can find gdal for windows [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal). Pick the version according to your currently installed Python version and Windows architecture, most likely 64 bit. After that just go to command prompt and: pip install "C:\path\to\this wheel file.whl"
