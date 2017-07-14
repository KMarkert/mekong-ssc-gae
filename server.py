#!/usr/bin/env python
"""A simple example of connecting to Earth Engine using App Engine."""



# Works in the local development environment and when deployed.
# If successful, shows a single web page with the SRTM DEM
# displayed in a Google Map.  See accompanying README file for
# instructions on how to set up authentication.

import os

import config
import ee
import jinja2
import webapp2

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class myProcess(object):

    def __init__(self,iniDate,endDate,region):
        self.iniDate = iniDate
        self.endDate = endDate
        self.region = region
        return

    def maskClouds(self,image):
        blank = ee.Image(0);
        scored = ee.Algorithms.Landsat.simpleCloudScore(image)
        clouds = blank.where(scored.select(['cloud']).lte(5),1);
        noClouds = image.updateMask(clouds).set("system:time_start",image.get("system:time_start"))
        return noClouds

    def maskLand(self,image):
        blank = ee.Image(0);
        jrc = ee.ImageCollection('JRC/GSW1_0/YearlyHistory')
        waterClass = jrc.select('waterClass').filterDate(self.iniDate,self.endDate).mode()
        water = blank.where(waterClass.gte(2),1)
        noLand = image.updateMask(water).set("system:time_start",image.get("system:time_start"))
        return noLand

    def bandTransform(self,image):
        red = image.select('B3')
        grn = image.select('B2')
        proxy = red.divide(grn).log10().set("system:time_start",image.get("system:time_start"))
        return proxy

    def calcTSS(self,image):
        odr4 = ee.Image(4);
        odr3 = ee.Image(3);
        odr2 = ee.Image(2);
        coef1 = ee.Image(-30.46093867);
        coef2 = ee.Image(-74.76793674);
        coef3 = ee.Image(-3.57940747);
        coef4 = ee.Image(7.23611937);
        coef5 = ee.Image(1.85468679);

        logTss = coef1.multiply(image.pow(odr4)).add(
                coef2.multiply(image.pow(odr3))).add(
                coef3.multiply(image.pow(odr2))).add(
                coef4.multiply(image)).add(
                coef5);

        tss = ee.Image(10).pow(logTss).set("system:time_start",image.get("system:time_start")).rename(['tss'])

        return tss

    def qualityMask(self,image):
        qualityTss = image.updateMask(image.lt(500)).set("system:time_start",image.get("system:time_start"))
        return qualityTss

    def makeLandsatSeries(self):
        lt4 = ee.ImageCollection('LANDSAT/LT4_L1T_TOA')
        lt5 = ee.ImageCollection('LANDSAT/LT5_L1T_TOA')
        le7 = ee.ImageCollection('LANDSAT/LE07/C01/T1_RT_TOA')
        #lc8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA').map(self.maskClouds)

        #lt4 = lt4.select(['B1,B2,B3,B4,B5,B7'],['blu','grn','red','nir','swir1','swir2'])
        #lt5 = lt5.select(['B1,B2,B3,B4,B5,B7'],['blu','grn','red','nir','swir1','swir2'])
        #le7 = le7.select(['B1,B2,B3,B4,B5,B7'],['blu','grn','red','nir','swir1','swir2'])
        #lc8 = lc8.select(['B2,B3,B4,B5,B6,B7'],['blu','grn','red','nir','swir1','swir2'])

        fullCollection = ee.ImageCollection(lt4.merge(lt5).merge(le7))

        start = ee.Date(self.iniDate)
        end = ee.Date(self.endDate)

        filteredCollection = fullCollection.filterDate(start, end).filterBounds(self.region)

        return filteredCollection

    def getTSS(self):
        collection = self.makeLandsatSeries()
        noClouds = collection.map(self.maskClouds)
        water = noClouds.map(self.maskLand)
        proxy = water.map(self.bandTransform)
        tss = proxy.map(self.calcTSS)
        qualityTss = tss.map(self.qualityMask)

        return qualityTss

class MainPage(webapp2.RequestHandler):

  def get(self):                             # pylint: disable=g-bad-name
    """Request an image from Earth Engine and render it to a web page."""
    ee.Initialize(config.EE_CREDENTIALS)

    lmbRegion = ee.FeatureCollection('ft:1FOW0_lYQNG3ku2ffNyoORbzDXglPvfMyXmZRb8dj')

    myProcessor = myProcess('2000-01-01','2000-12-31',lmbRegion)
    mkTSS = myProcessor.getTSS()

    myImg = ee.Image(mkTSS.select('tss').mean().clip(lmbRegion))

    mapid = myImg.getMapId({'min': 0, 'max': 200,
    'palette' : '000000,0000ff,ff0000,ffffff'})

    # These could be put directly into template.render, but it
    # helps make the script more readable to pull them out here, especially
    # if this is expanded to include more variables.
    template_values = {
        'mapid': mapid['mapid'],
        'token': mapid['token']
    }
    template = jinja_environment.get_template('index.html')
    self.response.out.write(template.render(template_values))

app = webapp2.WSGIApplication([('/', MainPage)], debug=True)
