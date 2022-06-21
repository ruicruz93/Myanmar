# - * - coding: utf-8 - * -
from osgeo import ogr, osr
import os, re, csv, chardet, sys


def filterAndConvert2Geopackage():
    #Open the reference object in case of filtering
    if len(sys.argv) == 4:
        filter_attribute = "{z[0]} = \'{z[1]}\'".format(z=tuple(i.strip() for i in re.compile(r'(.*)=(.*)').search(sys.argv[-1]).groups()))
        filter_params = [sys.argv[-2], filter_attribute]
        #Open the layer containing the reference feature
        clip_source = filter_params[0]
        clip_driver = ogr.GetDriverByName('GPKG')
        clip_dataSource = clip_driver.Open(clip_source, 0)
        clip_Layer = clip_dataSource.GetLayer()
        clip_Layer.SetAttributeFilter(filter_params[1]) #The Clip method used later on will take a layer as input, not a feature, hence this attribute filter is applied now
        clip_feature = clip_Layer.GetNextFeature() #.GetFeature(1) would override the previous filter
        clip_feature_geom = clip_feature.GetGeometryRef() #The Contains method used later on takes geometry objects as input    
    for x,y,z in os.walk(sys.argv[1]):
        for file in z:
            extension = re.compile(r'\.([^\\]+)$').search(file).group(1).lower()
            if extension == 'shp' or extension == 'csv':
                info = re.compile(r'([^\\]+)\\([^\\]+)$').findall(x) #Most filenames will be too long but similar to its containg folder's name, so it will be easier on the eyes to see that level and the level above it for reference
                print(f'Analyzing file {info[0][1]} from folder {info[0][0]}')
                #Open the input layer
                in_source = fr'{x}\{file}'
                if extension == 'shp':
                    in_driver = ogr.GetDriverByName('ESRI Shapefile')
                    in_dataSource = in_driver.Open(in_source, 0) #0 to open in read-only mode
                    in_Layer = in_dataSource.GetLayer()
                    crs = in_Layer.GetSpatialRef()
                    in_LayerDefinition = in_Layer.GetLayerDefn()
                    in_Layer_geomType = ogr.GeometryTypeToName(in_Layer.GetGeomType()) #String with geometry type. Ex: Multi Point
                    if len(sys.argv) == 4:
                        multi_part = ogr.Geometry(ogr.wkbGeometryCollection)
                        for feat in in_Layer:
                            multi_part.AddGeometry(feat.GetGeometryRef())
                        in_hull_polygon = multi_part.ConvexHull()
                        #Move on to the next file if the current's convex hull doesn't even intersect the reference feature
                        if in_hull_polygon.Intersects(clip_feature_geom) == False:
                            print(f"{file} has no records in the reference feature.")
                            in_dataSource = None
                            continue
                
                #if  extension is CSV
                else:
                    #Convert CSV's encoding to utf-8 if needed
                    with open(in_source, 'rb') as in_csv:
                        contents = in_csv.read()
                        in_encoding = chardet.detect(contents)['encoding']
                    if in_encoding.lower() != 'utf-8':
                        with open(in_source, 'wb') as nu_csv:
                            nu_csv.write(contents.decode(in_encoding).encode('utf-8'))
                    #Get the records from the CSV 
                    with open(in_source, 'r', encoding='utf-8', newline='') as input_csv:
                        reader = csv.DictReader(input_csv, delimiter=',')
                        registos = tuple(reader) #This variable will ensure continued access to the records after closing the CSV in python. Each tuple element will be a dictionary for each record.
                        fieldnames = reader.fieldnames #This iterable however will still be accessible after closing of the CSV
                    crs = osr.SpatialReference()
                    crs.ImportFromEPSG(4326)
                    multi_part = ogr.Geometry(ogr.wkbGeometryCollection)
                    for row in registos:
                        multi_part.AddGeometry(ogr.CreateGeometryFromWkt(f"POINT ({row['Longitude']} {row['Latitude']})"))                                        
                    in_hull_polygon = multi_part.ConvexHull()
                    #Move on to the next file if the current's convex hull doesn't even intersect the reference feature
                    if in_hull_polygon.Intersects(clip_feature_geom) == False:
                        print(f"{file} has no records in the reference feature.")
                        in_dataSource = None
                        continue
                
                #Create the output layer
                out_source = fr'{x}\{file[:file.index(extension)]}gpkg'
                out_driver = ogr.GetDriverByName('GPKG')
                out_dataSource = out_driver.CreateDataSource(out_source)
                out_Layer = out_dataSource.CreateLayer(name=file[:file.index(f'.{extension}')] + '_1', srs=crs, geom_type=ogr.wkbUnknown)
                out_LayerDefinition = out_Layer.GetLayerDefn()                
                
                #Start editing the GeoPackage:
                out_Layer.StartTransaction()
                
                #Input layer will be filtered for its features or portions contained in the reference polygon
                if len(sys.argv) == 4:                    
                    #For point geometries, check which are contained in the reference feature
                    if extension == 'csv' or in_Layer_geomType in ('Point', 'Multi Point'):
                        #For shapefiles
                        if extension == 'shp':
                            #Create the output fields from the input ones
                            for i in range(in_LayerDefinition.GetFieldCount()):
                                out_Layer.CreateField(in_LayerDefinition.GetFieldDefn(i))
                            #Create the output features from the input ones
                            for inFeat in in_Layer:
                                if clip_feature_geom.Contains(inFeat.GetGeometryRef()) == False:
                                    continue
                                else:
                                    outFeature = ogr.Feature(out_LayerDefinition)
                                    for i in range(out_LayerDefinition.GetFieldCount()):
                                        fieldDefn = out_LayerDefinition.GetFieldDefn(i)
                                        fieldName = fieldDefn.GetName()
                                        outFeature.SetField(fieldName, inFeat.GetField(fieldName))
                                    outFeature.SetGeometry(inFeat.GetGeometryRef())
                                    out_Layer.CreateFeature(outFeature)
                                    outFeature = None                   
                        
                        #For CSVs
                        else:
                            #Seeing as there are no field definitions like in Shapefiles, to create the output fields we must first determine their data types by accessing the attribute values of the first record for every field
                            fieldnames_dic = {} #Dic with fieldname:data type value pairs
                            for field in fieldnames:
                                if re.compile(r'\d+\.\d+').search(registos[0][field]) != None:
                                    campo = ogr.FieldDefn(field, ogr.OFTReal) #Double
                                    campo.SetPrecision(7)
                                    out_Layer.CreateField(campo)
                                    fieldnames_dic[field] = 'double'
                                elif registos[0][field].isdecimal() == True:
                                    campo = ogr.FieldDefn(field, ogr.OFTInteger64) #64 bit ints in case of really big numbers > 2,147,483,647
                                    out_Layer.CreateField(campo)
                                    fieldnames_dic[field] = 'int'
                                else:
                                    campo = ogr.FieldDefn(field, ogr.OFTString) #String 
                                    campo.SetWidth(150) #In case of very long names
                                    out_Layer.CreateField(campo)
                                    fieldnames_dic[field] = 'string'
                            #Create the output features from the input ones
                            for row in registos:
                                ponto = ogr.CreateGeometryFromWkt(f"POINT ({row['Longitude']} {row['Latitude']})")
                                if clip_feature_geom.Contains(ponto) == False:
                                    continue
                                else:
                                    outFeature = ogr.Feature(out_LayerDefinition)
                                    for field in fieldnames:
                                        if fieldnames_dic[field] == 'double':
                                            outFeature.SetField(field, float(row[field]))
                                        elif fieldnames_dic[field] == 'int':
                                            outFeature.SetField(field, int(row[field]))
                                        else:
                                            outFeature.SetField(field, row[field])
                                    outFeature.SetGeometry(ponto)
                                    out_Layer.CreateFeature(outFeature)
                                    outFeature = None
                    
                    #For Linestring or Polygon geometries, clip the portions that intersect the reference feature
                    #With the Clip method, the output layer will inherit the input layer's fields
                    else:
                        in_Layer.Clip(clip_Layer, out_Layer)
                
                #No filtering
                elif len(sys.argv) == 2:
                    #Create the out layer fields from the input shapefile ones
                    for i in range(in_LayerDefinition.GetFieldCount()):
                        out_Layer.CreateField(in_LayerDefinition.GetFieldDefn(i))                    
                    #Create the out layer features from the input shapefile ones
                    for inFeat in in_Layer:
                        outFeature = ogr.Feature(out_LayerDefinition)
                        for i in range(out_LayerDefinition.GetFieldCount()):
                            fieldDefn = out_LayerDefinition.GetFieldDefn(i)
                            fieldName = fieldDefn.GetName()
                            outFeature.SetField(fieldName, inFeat.GetField(fieldName))
                        outFeature.SetGeometry(inFeat.GetGeometryRef())
                        out_Layer.CreateFeature(outFeature)
                        outFeature = None
                
                #Commit changes to the Geopackage and turn off both input and output data sources
                out_Layer.CommitTransaction()
                in_dataSource = None
                out_dataSource = None
        
        #Delete all files within current directory. The newly created GeoPackage/s will not be deleted seeing as the directory file list is not updated during the for loop.
        for i in z:
            os.unlink(fr'{x}\{i}')
    if len(sys.argv) == 4:
        clip_dataSource = None
#***************************************************************

filterAndConvert2Geopackage()