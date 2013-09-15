#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib
import urllib2
import sys
import os
import re
import csv
import json
from xml.dom import Node;
from xml.dom import minidom;
try:
   import StorageServer
except:
   import storageserverdummy as StorageServer

cache = StorageServer.StorageServer("plugin.program.wienerlinien", 999999)


version = "0.1.0"
plugin = "WienerLinien-" + version
author = "sofaking"


pluginhandle = int(sys.argv[1])
settings = xbmcaddon.Addon(id='plugin.program.wienerlinien') 
#CSV Urls
stations_url = "http://data.wien.gv.at/csv/wienerlinien-ogd-haltestellen.csv"
lines_url = "http://data.wien.gv.at/csv/wienerlinien-ogd-linien.csv"
positions_url = "http://data.wien.gv.at/csv/wienerlinien-ogd-steige.csv"
basepath = settings.getAddonInfo('path')
resourcespath = os.path.join(settings.getAddonInfo('path'),"resources")

defaultbackdrop = os.path.join(basepath,"fanart.jpg")

stationpath = os.path.join(resourcespath, "stations.csv")
linepath = os.path.join(resourcespath, "lines.csv")
positionpath = os.path.join(resourcespath, "positions.csv")

#GET CSVs
urllib.urlretrieve(stations_url, stationpath)
urllib.urlretrieve(lines_url, linepath)
urllib.urlretrieve(positions_url, positionpath)


def getMainMenu():
    addDirectory("Station Suchen","Hier kannst du nach einer Station suchen","searchStation")
    addDirectory("Favoriten","Hier kannst du schnell auf deine Favoriten zugreifen. Benutze das Kontextmenü um Stationen zu deinen Favoriten hinzuzufügen.","getFavorites")
    addDirectory("Monitor","Hier kannst du auf die Monitordaten der Stationen zugreifen","getMonitor")
    addDirectory("Störungen","Hier werden gegebenenfalls Störungen angezeigt","getFailures")
    xbmcplugin.setContent(pluginhandle,'episodes')
    xbmcplugin.endOfDirectory(pluginhandle)

def addDirectory(title,desc,mode,id=''):
    parameters = {"title" : title,"mode" : mode,"id":id}
    u = sys.argv[0] + '?' + urllib.urlencode(parameters)
    liz=xbmcgui.ListItem(label=title,label2=desc,iconImage=os.path.join(basepath,"icon.png"))
    liz.setProperty('IsPlayable', 'false')
    ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
    return ok

	
def parameters_string_to_dict(parameters):
        paramDict = {}
        if parameters:
            paramPairs = parameters[1:].split("&")
            for paramsPair in paramPairs:
                paramSplits = paramsPair.split('=')
                if (len(paramSplits)) == 2:
                    paramDict[paramSplits[0]] = paramSplits[1]
        return paramDict

def getMonitor(search=''):
    dictReader = csv.DictReader(open(stationpath, 'rb'), fieldnames = ['HALTESTELLEN_ID', 'TYP','DIVA', 'NAME', 'GEMEINDE', 'GEMEINDE_I'], delimiter = ';', quotechar = '"')
    for row in dictReader:
        if(row['NAME'] != "NAME"):
            if search.lower() in row['NAME'].lower():
                parameters = {"title" : row['NAME'],"id" : row['HALTESTELLEN_ID'],"mode" : "getStationInfos"}
                u = sys.argv[0] + '?' + urllib.urlencode(parameters)
                liz=xbmcgui.ListItem(row['NAME'],iconImage=os.path.join(basepath,"icon.png"))
                liz.setProperty('IsPlayable', 'false')
                xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
    xbmcplugin.setContent(pluginhandle,'episodes')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.endOfDirectory(pluginhandle)

def getStationPositions(haltestellen_id):
    dictReader = csv.DictReader(open(positionpath, 'rb'), fieldnames = ['STEIG_ID', 'FK_LINIEN_ID','FK_HALTESTELLEN_ID', 'RICHTUNG', 'REIHENFOLGE', 'RBL_NUMMER','BEREICH','STEIG', 'STEIG_WGS84_LAT', 'STEIG_WGS84_LON', 'STAND'], delimiter = ';', quotechar = '"')
    haltestellen_list =[]
    rbl_str = ""
    for row in dictReader:
        if row['FK_HALTESTELLEN_ID'] == haltestellen_id:
            if findStationDuplicate(haltestellen_list,row['RBL_NUMMER']):
                haltestellen_list.append(row['RBL_NUMMER'])
    for rbl in haltestellen_list:
        if rbl != '':
            if ":" in rbl:
                rbl_array = rbl.split(":")
                for rbl_item in rbl_array:
                    rbl_str += "rbl=%s&" % rbl_item
            else:
                rbl_str += "rbl=%s&" % rbl
    if rbl_str != '':
        json_url = "http://www.wienerlinien.at/ogd_realtime/monitor?%ssender=5L88jCE2ts" % rbl_str
        getJsonMessage(json_url)
    else:
        notFound()
    

def notFound():
    parameters = {"title" : "Es sind keine Echtzeitdaten vorhanden","mode" : "notFound"}
    u = sys.argv[0] + '?' + urllib.urlencode(parameters)
    liz=xbmcgui.ListItem("Es sind keine Echtzeitdaten vorhanden",iconImage=os.path.join(basepath,"icon.png"))
    liz.setProperty('IsPlayable', 'false')
    xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
    xbmcplugin.setContent(pluginhandle,'episodes')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.endOfDirectory(pluginhandle)

def searchStation():
    addDirectory("Suchen ...","","searchStationResult")
    cache.table_name = "searchhistory"
    some_dict = cache.get("searches").split("|")
    for str in reversed(some_dict):
        addDirectory(str,"","searchStationHistory",str)
    xbmcplugin.setContent(pluginhandle,'episodes')
    xbmcplugin.endOfDirectory(pluginhandle)
	
def searchStationResult():
    keyboard = xbmc.Keyboard('')
    keyboard.doModal()
    if (keyboard.isConfirmed()):
      cache.table_name = "searchhistory"
      keyboard_in = keyboard.getText()
      some_dict = cache.get("searches") + "|"+keyboard_in
      cache.set("searches",some_dict);
      getMonitor(keyboard_in)
    xbmcplugin.setContent(pluginhandle,'episodes')
    xbmcplugin.endOfDirectory(pluginhandle)
	
def findStationDuplicate(list,id):
    for item in list:
        if item == id:
            return False
    return True			

def getJsonMessage(url):
    url = urllib.unquote_plus(url)
    print "URL:%s" % url
    parameters = {"title" : " --- Aktualisieren --","mode" : "refreshStations" , "id" : url}
    u = sys.argv[0] + '?' + urllib.urlencode(parameters)
    liz=xbmcgui.ListItem(label=" --- Aktualisieren --", label2="",iconImage=os.path.join(basepath,"icon.png"))
    liz.setProperty('IsPlayable', 'false')
    xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
    json_response = urllib2.urlopen(url).read()
    json_dict = json.loads(json_response)
    for column in json_dict['data']['monitors']:
        for row in column['lines']:
            departure_str = ""
            jam_str = ""
            for departures in row['departures']['departure']:
                departure_str += "%s min | " % departures['departureTime']['countdown']
            name = row['name']
            towards = row['towards']
            if row['trafficjam']:
                jam_str = "# Stau in Zufahrt #"
            title = "%s | %s | %s | %s" % (name.encode('utf-8'),towards.encode('utf-8'),departure_str,jam_str)
            parameters = {"title" : title,"mode" : "refreshStations","id": url}
            u = sys.argv[0] + '?' + urllib.urlencode(parameters)
            liz=xbmcgui.ListItem(label=title, label2=departure_str,iconImage=os.path.join(basepath,"icon.png"))
            liz.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.endOfDirectory(pluginhandle)

	
def getFavorites():
    xbmc.executebuiltin('XBMC.ActivateWindow(favourites)')
	
def getJsonFailureMessage():
    url = "http://www.wienerlinien.at/ogd_realtime/trafficInfoList?sender=5L88jCE2ts"
    dictReader = csv.DictReader(open(positionpath, 'rb'), fieldnames = ['STEIG_ID', 'FK_LINIEN_ID','FK_HALTESTELLEN_ID', 'RICHTUNG', 'REIHENFOLGE', 'RBL_NUMMER','BEREICH','STEIG', 'STEIG_WGS84_LAT', 'STEIG_WGS84_LON', 'STAND'], delimiter = ';', quotechar = '"')
    json_response = urllib2.urlopen(url).read()
    json_dict = json.loads(json_response)
    for column in json_dict['data']['trafficInfos']:
            try:
                title = column["title"].replace("\n"," | ").encode('utf-8')
            except:
                title = ''
            try:
                desc = column["description"].encode('utf-8')
            except:
                desc = "Kein Beschreibung verfügbar"
            try:
                reason = column['attributes']["reason"].encode('utf-8')
                desc += "| %s |" % reason
            except:
                print ''
            relatedlines = ''
            try:
                for line in column['attributes']["relatedLines"]:
                    relatedlines += "[%s] " % line
                desc += "| %s |" % relatedlines
            except:
                try:
                    for line in column["relatedLines"]:
                        print "RELATED LINE"
                        desc += " [Linie %s] " % line
                except:
                    print ''
            relatedStops = ''
            try:
                for related in column['attributes']["relatedStops"]:
                    relatedStops += "[%s] " % line
                #desc += "| %s |" % relatedStops
            except:
                try:
                    for stops in column["relatedStops"]:
                        relatedStops += "[%s] " % stops
                    #desc += "| %s |" % relatedStops
                except:
                    print ''
            try:
                station = column['attributes']["station"].encode('utf-8')
                desc += "[ %s ]" % station
            except:
                station = ''
            try:
                status = column['attributes']["status"].encode('utf-8')
                desc += "| Staus: %s |" % status
            except:
                 status = ''
            try:
                duration = "%s bis &s" % (column['attributes']["ausVon"].encode('utf-8'),column['attributes']["ausBis"].encode('utf-8')) 
                desc += "| Dauer: %s |" % duration
            except:
                duration = "kein Angabe zur Dauer" 
            print title
            print desc
            print "############################################################" 
            parameters = {"title" : title,"mode" : "getFailures"}
            u = sys.argv[0] + '?' + urllib.urlencode(parameters)
            liz2=xbmcgui.ListItem(label=title, label2=desc,iconImage=os.path.join(basepath,"icon.png"))
            liz2.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz2,isFolder=True)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL )
    xbmcplugin.endOfDirectory(pluginhandle)
	
params=parameters_string_to_dict(sys.argv[2])
mode=params.get('mode')
id=params.get('id')
xbmcplugin.setPluginFanart(int(sys.argv[1]), defaultbackdrop, color2='0xFFFF3300')

if mode =='getMonitor':
    getMonitor()
elif mode == 'getStationInfos':
    getStationPositions(id)
elif mode == 'refreshStations':
    getJsonMessage(id)
elif mode == 'getFavorites':
    getFavorites();
elif mode == 'searchStation':
    searchStation()
elif mode == 'searchStationResult':
    searchStationResult()
elif mode == 'searchStationHistory':
    getMonitor(id)
elif mode == 'getFailures':
    getJsonFailureMessage()
else:
    getMainMenu()