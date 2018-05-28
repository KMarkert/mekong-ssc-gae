#!/usr/bin/env python
"""Google Earth Engine python code for the SERVIR-Mekong Surface ecodash Tool"""

# This script handles the loading of the web application and its timeout settings,
# as well as the complete Earth Engine code for all the calculations.

import json
import os
import math

import config
import numpy as np
import ee
import jinja2
import webapp2
import oauth2client.appengine
from itertools import groupby
import datetime

import socket

from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.api import channel
from google.appengine.api import taskqueue

# ------------------------------------------------------------------------------------ #
# Initialization
# ------------------------------------------------------------------------------------ #

# Memcache is used to avoid exceeding our EE quota. Entries in the cache expire
# 24 hours after they are added. See:
# https://cloud.google.com/appengine/docs/python/memcache/
MEMCACHE_EXPIRATION = 60 * 60 * 24


# The URL fetch timeout time (seconds).
URL_FETCH_TIMEOUT = 55

WIKI_URL = ""

base_path = os.path.dirname(__file__)

# The scale at which to reduce the polygons for the WQ time series.
REDUCTION_SCALE_METERS = 30

# Create the Jinja templating system we use to dynamically generate HTML. See:
# http://jinja.pocoo.org/docs/dev/
JINJA2_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(base_path),
    autoescape=True,
    extensions=['jinja2.ext.autoescape'])

ee.Initialize(config.EE_CREDENTIALS)

ee.data.setDeadline(URL_FETCH_TIMEOUT)
socket.setdefaulttimeout(URL_FETCH_TIMEOUT)
urlfetch.set_default_fetch_deadline(URL_FETCH_TIMEOUT)

# set initial dates
start = '2000-01-01'
end = '2000-12-31'
iniMonth = 11
endMonth = 4

# set LMB region
lmbRegion = ee.FeatureCollection('ft:1FOW0_lYQNG3ku2ffNyoORbzDXglPvfMyXmZRb8dj')


class myProcess(object):

    def __init__(self,iniDate,endDate,iniMonth,endMonth):
        self.iniDate = iniDate
        self.endDate = endDate
        self.region = lmbRegion
        self.iniMonth = iniMonth
        self.endMonth = endMonth
        self.monthJulian = {1:[1,31],2:[32,59],3:[60,90],4:[91,120],
                            5:[121,151],6:[152,181],7:[182,212],8:[213,243],
                            9:[244,273],10:[274,304],11:[305,334],12:[335,365]}
        return

    def getQABits(self,image, start, end, newName):
        #Compute the bits we need to extract.
        pattern = 0;
        for i in range(start,end+1):
           pattern += math.pow(2, i);

        # Return a single band image of the extracted QA bits, giving the band
        # a new name.
        return image.select([0], [newName])\
                      .bitwiseAnd(int(pattern))\
                      .rightShift(start);

    def maskClouds(self,image):
        # blank = ee.Image(0);
        # scored = ee.Algorithms.Landsat.simpleCloudScore(image)
        # clouds = blank.where(scored.select(['cloud']).lte(5),1);
        qa = self.getQABits(image.select('pixel_qa'),1,2,'qa')
        clouds = qa.neq(0)
        noClouds = image.updateMask(clouds).set("system:time_start",image.get("system:time_start"))
        return noClouds

    def maskLand(self,image):
        def jrcMask(image):
            date = ee.Date(image.get('system:time_start'))
            blank = ee.Image(0);
            jrc = ee.ImageCollection('JRC/GSW1_0/MonthlyHistory')
            waterClass = ee.Image(jrc.select('water').filterDate(date.advance(-30,'day'),date.advance(30,'day')).max())
            water = blank.where(waterClass.eq(2),1)
            return water

        def qaMask(image):
            qa = self.getQABits(image.select('pixel_qa'),2,2,'qa');
            water = qa.eq(1);
            return water

        blank = ee.Image(1)
        sDate = ee.Number(ee.Date('1984-03-17').millis())
        eDate = ee.Number(ee.Date('2015-10-17').millis())
        imgDate = ee.Number(image.get('system:time_start'))
        result = ee.Image(
                 ee.Algorithms.If(imgDate.gt(sDate).And(imgDate.lt(eDate)),
                 jrcMask(image),
                 qaMask(image)
                 ))

        # inverse = blank.updateMask(result.eq(0));
        # dist = blank.cumulativeCost(inverse,25000).rename(['dist'])

        noLand = image.updateMask(result).set("system:time_start",image.get("system:time_start"))
        return noLand

    def calcTSS(self,image):
        t = ee.Date(image.get('system:time_start'))
        red = image.select('red').multiply(0.0001)
        grn = image.select('grn').multiply(0.0001)
        ratio = red.divide(grn).log()

        logTss = ratio.expression('a*e**(b*X+c)',{
                'X': ratio,
                'a': 1.90353307,
                'b': 1.44788939,
                'c': 0.62996462,
                'e': 2.718281828459045,
              });
        tss = logTss.exp().set("system:time_start",t.millis()).rename(['tss'])

        return tss.updateMask(tss.lt(5000)) # mask bad quality TSS values over 5000 mg/L

    def makeLandsatSeries(self):
        lt4 = ee.ImageCollection('LANDSAT/LT04/C01/T1_SR')
        lt5 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
        le7 = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR')
        lc8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')

        lt4 = lt4.select(['B1','B2','B3','B4','B5','B7','pixel_qa'],['blu','grn','red','nir','swir1','swir2','pixel_qa'])
        lt5 = lt5.select(['B1','B2','B3','B4','B5','B7','pixel_qa'],['blu','grn','red','nir','swir1','swir2','pixel_qa'])
        le7 = le7.select(['B1','B2','B3','B4','B5','B7','pixel_qa'],['blu','grn','red','nir','swir1','swir2','pixel_qa'])
        lc8 = lc8.select(['B2','B3','B4','B5','B6','B7','pixel_qa'],['blu','grn','red','nir','swir1','swir2','pixel_qa'])

        fullCollection = ee.ImageCollection(lt4.merge(lt5).merge(le7).merge(lc8))

        start = ee.Date(self.iniDate)
        end = ee.Date(self.endDate)
        jT1 = self.monthJulian[self.iniMonth][0]
        jT2 = self.monthJulian[self.endMonth][1]

        filteredCollection = fullCollection.filterDate(start, end).filterBounds(self.region)\
                                .filter(ee.Filter.calendarRange(jT1,jT2))

        return filteredCollection

    def getTSS(self):
        collection = self.makeLandsatSeries()
        noClouds = collection.map(self.maskClouds)
        water = noClouds.map(self.maskLand)
        tss = water.map(self.calcTSS)

        return tss

    # helper function to take multiple values of region and aggregate to one value
    def aggRegion(self,regionList):
        values = []
        for i in range(len(regionList)):
            if i != 0:
                date = datetime.datetime.fromtimestamp(regionList[i][-2]/1000.).strftime("%Y-%m-%d")
                values.append([date,regionList[i][-1]])

        sort = sorted(values, key=lambda x: x[0])

        y = [i for i in sort if i[1] > 0]

        out = []
        for key, group in groupby(y, key=lambda x: x[0][:10]):
            data = list(group)
            agg = sum(j for i, j in data if (j != None))
            dates = key.split('-')
            timestamp = datetime.datetime(int(dates[0]),int(dates[1]),int(dates[2]))
            out.append([int(timestamp.strftime('%s'))*1000,agg/float(len(data))])

        return out


    def makeTimeSeries(self,feature):

        area = feature.geometry().area()
        collection = self.getTSS() #.getInfo()
        values = collection.getRegion(feature,100).getInfo()
        out = self.aggRegion(values)

        return out

# ------------------------------------------------------------------------------------ #
# Web request handlers
# ------------------------------------------------------------------------------------ #

class MainHandler(webapp2.RequestHandler):
    """A servlet to handle requests to load the main web page."""

    def get(self):
        mapid = updateMap(start,end,iniMonth,endMonth)
        template_values = {
            'eeMapId': mapid['mapid'],
            'eeToken': mapid['token']
        }

        template = JINJA2_ENVIRONMENT.get_template('index.html')
        self.response.out.write(template.render(template_values))


class DetailsHandler(webapp2.RequestHandler):
  """A servlet to handle requests for details about a Polygon."""

  def get(self):
    """Returns details about a polygon."""

    start = self.request.get('refLow')
    end = self.request.get('refHigh')
    months = self.request.get('months').split(',')

    mapid = updateMap(start,end,int(months[0]),int(months[1]))

    template_values = {
		'eeMapId': mapid['mapid'],
		'eeToken': mapid['token']
        }

    template = JINJA2_ENVIRONMENT.get_template('index.html')
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json.dumps(template_values))

# Download handler to download the map
# returns a url to download
class DownloadHandler(webapp2.RequestHandler):
    """A servlet to handle requests to load the main web page."""

    def get(self):

        poly = json.loads(unicode(self.request.get('polygon')))

        coords = []

        for items in poly:
        	coords.append([items[0],items[1]])

        start = self.request.get('refLow')
        end = self.request.get('refHigh')
        months = self.request.get('months').split(',')

        print "========================================="
        print coords

        polygon = ee.FeatureCollection(ee.Geometry.Polygon(coords))

        downloadURL = downloadMap(polygon,coords,start,end,int(months[0]),int(months[1]))

        print downloadURL
        content = json.dumps(downloadURL)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(content)


class TimeHandler(webapp2.RequestHandler):
    """A servlet to handle requests to load the main web page."""

    def get(self):

        urlfetch.set_default_fetch_deadline(URL_FETCH_TIMEOUT)

        poly = json.loads(unicode(self.request.get('polygon')))

        coords = []

        for items in poly:
        	coords.append([items[0],items[1]])

        start = self.request.get('refLow')
        end = self.request.get('refHigh')
        months = self.request.get('months').split(',')

        polygon = ee.FeatureCollection(ee.Geometry.Polygon(coords))

        try:
          result = ComputePolygonTimeSeries(polygon,coords,start,end,int(months[0]),int(months[1]))
          content = json.dumps({'timeSeries': result})
        except ee.EEException as e:
          content = json.dumps({'error': e})

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(content)

# Define webapp2 routing from URL paths to web request handlers. See:
# http://webapp-improved.appspot.com/tutorials/quickstart.html
app = webapp2.WSGIApplication([
    ('/details', DetailsHandler),
    ('/downloadHandler', DownloadHandler),
    ('/timeHandler',TimeHandler),
    ('/', MainHandler),

])


# ------------------------------------------------------------------------------------ #
# Helper functions
# ------------------------------------------------------------------------------------ #

def updateMap(startDate,endDate,startMonth,closeMonth):

  myProcessor = myProcess(startDate,endDate,startMonth,closeMonth)
  mkTSS = myProcessor.getTSS()

  myImg = ee.Image(mkTSS.select('tss').mean().clip(lmbRegion))

  return myImg.getMapId({'min': 0, 'max': 800,
  'palette' : '000000,0000ff,c729d6,ffa857,ffffff'})

# function to download the map
# returns a download url
def downloadMap(polygon,coords,startDate,endDate,startMonth,closeMonth):

  myProcessor = myProcess(startDate,endDate,startMonth,closeMonth)
  mkTSS = myProcessor.getTSS()

  myImg = ee.Image(mkTSS.select('tss').mean().clip(lmbRegion))

  return myImg.getDownloadURL({
		'scale': 30,
		'crs': 'EPSG:4326',
		'region': coords
  })

def GetPolygonTimeSeries(polygon_id):
  """Returns details about the polygon with the passed-in ID."""
  details = memcache.get(polygon_id)

  # If we've cached details for this polygon, return them.
  if details is not None:
    return details

  details = {'wikiUrl': WIKI_URL + polygon_id.replace('-', '%20')}

  try:
    details['timeSeries'] = ComputePolygonTimeSeries(polygon_id)
    # Store the results in memcache.
    memcache.add(polygon_id, json.dumps(details), MEMCACHE_EXPIRATION)
  except ee.EEException as e:
    # Handle exceptions from the EE client library.
    details['error'] = str(e)

  # Send the results to the browser.
  return json.dumps(details)


def ComputePolygonTimeSeries(polygon,coords,startDate,endDate,startMonth,closeMonth):
  """Returns a series of brightness over time for the polygon."""
  myProcessor = myProcess(startDate,endDate,startMonth,closeMonth)
  # mkTSS = myProcessor.getTSS()
  # collection = collection.select('tss').sort('system:time_start')
  # feature = GetFeature(polygon_id)
  #
  # # Compute the mean brightness in the region in each image.
  # def ComputeMean(img):
  #   reduction = img.reduceRegion(
  #       ee.Reducer.mean(), feature.geometry(), REDUCTION_SCALE_METERS)
  #   return ee.Feature(None, {
  #       'tss': reduction.get('tss'),
  #       'system:time_start': img.get('system:time_start')
  #   })
  # chart_data = collection.map(ComputeMean).getInfo()
  #
  # # Extract the results as a list of lists.
  # def ExtractMean(feature):
  #   return [
  #       feature['properties']['system:time_start'],
  #       feature['properties']['tss']
  #   ]
  ts = myProcessor.makeTimeSeries(polygon)
  return ts


def GetFeature(polygon_id):
  """Returns an ee.Feature for the polygon with the given ID."""
  # Note: The polygon IDs are read from the filesystem in the initialization
  # section below. "sample-id" corresponds to "static/polygons/sample-id.json".
  path = POLYGON_PATH + polygon_id + '.json'
  path = os.path.join(os.path.split(__file__)[0], path)
  with open(path) as f:
    return ee.Feature(json.load(f))
