#!/usr/bin/env python
"""Google Earth Engine python code for the SERVIR-Mekong Surface ecodash Tool"""

# This script handles the loading of the web application and its timeout settings,
# as well as the complete Earth Engine code for all the calculations.

import json
import os

import config
import numpy as np
import ee
import jinja2
import webapp2
import oauth2client.appengine

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
URL_FETCH_TIMEOUT = 120

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
end = '2002-12-31'

# set LMB region
lmbRegion = ee.FeatureCollection('ft:1FOW0_lYQNG3ku2ffNyoORbzDXglPvfMyXmZRb8dj')


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
        qualityTss = image.updateMask(image.lt(250)).set("system:time_start",image.get("system:time_start"))
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

# ------------------------------------------------------------------------------------ #
# Web request handlers
# ------------------------------------------------------------------------------------ #

class MainHandler(webapp2.RequestHandler):
    """A servlet to handle requests to load the main web page."""

    def get(self):
        mapid = updateMap(start,end)
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

    start = self.request.get('refLow') + '-01-01'
    end = self.request.get('refHigh') + '-12-31'

    mapid = updateMap(start,end)

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


		start = self.request.get('refLow') + '-01-01'
		end = self.request.get('refHigh') + '-12-31'


		print "========================================="
		print coords


		polygon = ee.FeatureCollection(ee.Geometry.Polygon(coords))

		downloadURL = downloadMap(polygon,coords,start,end)

		print downloadURL
		content = json.dumps(downloadURL)

		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(content)


# Define webapp2 routing from URL paths to web request handlers. See:
# http://webapp-improved.appspot.com/tutorials/quickstart.html
app = webapp2.WSGIApplication([
    ('/details', DetailsHandler),
    ('/downloadHandler', DownloadHandler),
    ('/', MainHandler),

])


# ------------------------------------------------------------------------------------ #
# Helper functions
# ------------------------------------------------------------------------------------ #

def updateMap(startDate,endDate):

  myProcessor = myProcess(startDate,endDate,lmbRegion)
  mkTSS = myProcessor.getTSS()

  myImg = ee.Image(mkTSS.select('tss').mean().clip(lmbRegion))

  return myImg.getMapId({'min': 0, 'max': 200,
  'palette' : '000000,0000ff,c729d6,ffa857,ffffff'})



# function to download the map
# returns a download url
def downloadMap(polygon,coords,startDate,endDate):

  myProcessor = myProcess('2010-01-01','2010-07-31',lmbRegion)
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


def ComputePolygonTimeSeries(polygon_id):
  """Returns a series of brightness over time for the polygon."""
  myProcessor = myProcess(startDate,endDate,lmbRegion)
  mkTSS = myProcessor.getTSS()
  collection = collection.select('tss').sort('system:time_start')
  feature = GetFeature(polygon_id)

  # Compute the mean brightness in the region in each image.
  def ComputeMean(img):
    reduction = img.reduceRegion(
        ee.Reducer.mean(), feature.geometry(), REDUCTION_SCALE_METERS)
    return ee.Feature(None, {
        'tss': reduction.get('tss'),
        'system:time_start': img.get('system:time_start')
    })
  chart_data = collection.map(ComputeMean).getInfo()

  # Extract the results as a list of lists.
  def ExtractMean(feature):
    return [
        feature['properties']['system:time_start'],
        feature['properties']['tss']
    ]
  return map(ExtractMean, chart_data['features'])


def GetFeature(polygon_id):
  """Returns an ee.Feature for the polygon with the given ID."""
  # Note: The polygon IDs are read from the filesystem in the initialization
  # section below. "sample-id" corresponds to "static/polygons/sample-id.json".
  path = POLYGON_PATH + polygon_id + '.json'
  path = os.path.join(os.path.split(__file__)[0], path)
  with open(path) as f:
    return ee.Feature(json.load(f))
