# - * - coding: utf-8 - * -
import psycopg2, os, re, sys, csv
from osgeo import ogr, osr
from psycopg2.sql import SQL, Identifier
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT



#Creation of a database for Myanmar from Shapefile or GeoPackage files
#Database will derive its name from the country directory, containing only shp or gpkg files, each amounting to one table in the database. Table names will be derived from filenames minus the extension.
#Country directory will be passed as a command line argument

def dataSource_to_dataBase(country_directory):
    
    #Database, table and field names always in lowercase
    dbname = re.compile(r'([^\\]*)$').search(country_directory).group(1).lower()
    with open(fr"{variables[2]['Path']}", 'r') as txt:
        connect_params = txt.read()
    
    #Create the new database for Myanmar. Need to connect to a preexisting database first, like the postgres database which comes by default with PostgreSQL
    connection = psycopg2.connect(f'dbname=postgres {connect_params}')
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) #Necessary command for creating databases. No need for connection.commit at the end of the database creation command seeing as the commit will be done automatically
    cur = connection.cursor()    
    cur.execute(SQL('CREATE DATABASE {};').format(Identifier(dbname))) #Percantage char only for value insertion. Table and database names must be used as instances of the Identifier class.
    cur.close()
    connection.close()
    print(f'{dbname} database created successfully!')
    
    #Change to newly created database
    connection = psycopg2.connect(f'dbname={dbname} {connect_params}')
    cur = connection.cursor()
    cur.execute("CREATE EXTENSION postgis;") #Give the database spatial capabilities
    extensions_dict = {'shp': 'ESRI Shapefile', 'gpkg': 'GPKG'}
    fieldTypes_dict = {'Integer': 'INT', 'Integer64': 'BIGINT', 'Real': 'REAL', 'String': 'TEXT'}
    #Create new table for every new DataSource file and add its respective Fields and features to the Table.
    for x,y,z in os.walk(country_directory):
        if len(z) == 0:
            continue
        for i in z:
            if i.endswith('shp') or i.endswith('gpkg'):
                table_name = re.compile(r'([^\\]+)\.\w{3,4}$').search(i).group(1).lower()
                file = fr'{x}\{i}'
                extension = i[i.index('.')+1:]
                driver = ogr.GetDriverByName(extensions_dict[extension])
                dataSource = driver.Open(file, 0)
                layer = dataSource.GetLayer()
                srid = layer.GetSpatialRef().GetAttrValue('AUTHORITY', 1) #Returns the EPSG code string
                layerDefn = layer.GetLayerDefn()
                #Add Layer fields to table
                fields_tuples_list = []
                for i in range(layerDefn.GetFieldCount()):
                    fieldDefn = layerDefn.GetFieldDefn(i)
                    fieldName = fieldDefn.GetName()
                    fieldType = fieldDefn.GetFieldTypeName(fieldDefn.GetType())
                    fields_tuples_list.append((fieldName, fieldTypes_dict.get(fieldType, "VARCHAR"))) #In case of a None type, VARCHAR will be used, allowing both chars and digits
                sql_fields_list = list(SQL("{} {}").format(Identifier(k[0]), SQL(k[1])) for k in fields_tuples_list) #Data types such as VARCHAR or any of the fieldTypes_dict values must be passed as instances of the SQL class, the same way as database and table names must be passed as instances of the Identifier class. Very important tips for preventing SQL injection.
                geometry_field = SQL("{} {}").format(Identifier('geom'), SQL('GEOMETRY'))
                query = SQL('CREATE TABLE {} ({}, {});').format(
                    Identifier(table_name),
                    SQL(', ').join(sql_fields_list),
                    geometry_field)
                cur.execute(query)
                print(f'{table_name} table created successfully!')
                #Create Spatial index for the given table. Speeds up searching for features resorting to their extents
                create_sp_ix_query = SQL("CREATE INDEX {table_index} ON {tableName} USING GIST ({geom_field});").format(
                table_index = Identifier(f'{table_name}_geom_idx'),
                tableName=Identifier(table_name),
                geom_field=Identifier('geom'))
                cur.execute(create_sp_ix_query)
                #Add layer features to table
                for feature in layer:
                    wkt = feature.GetGeometryRef().ExportToWkt()
                    query = SQL("INSERT INTO {table} ({fields}) VALUES ({percents}, ST_GeometryFromText(%s, %s));").format(
                    table=Identifier(table_name),
                    fields=SQL(', ').join(list(Identifier(i[0]) for i in fields_tuples_list) + [Identifier('geom')]),
                    percents=SQL(', ').join(list(SQL('%s') for j in range(len(fields_tuples_list)))))
                    query_values_list = list(feature.GetField(z[0]) for z in fields_tuples_list) + [wkt, srid]
                    cur.execute(query, tuple(query_values_list))
                dataSource = None
    #End code
    connection.commit()
    cur.close()
    connection.close()
    print('Process completed!')
#****************************************************************************

directory = re.compile(r'(.*)\\[^\\]*$').search(sys.argv[0]).group(1)
#Get variables paths
with open(fr'{directory}\Variables.txt', 'r', encoding='utf-8', newline='') as txt:
    reader = csv.DictReader(txt, delimiter=',')
    fieldnames = reader.fieldnames
    variables = tuple(reader)
for row in variables:
    if row['Path'] == '':
        sys.exit('Missing variable paths. Please fill out Variables.txt first.')

dataSource_to_dataBase(sys.argv[1])