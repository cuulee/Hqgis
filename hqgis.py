# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Hqgis
                                 A QGIS plugin
 Access the HERE API in QGIS
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2018-12-22
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Riccardo Klinger
        email                : riccardo.klinger@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QUrl
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QAction, QFileDialog
from PyQt5 import QtGui, QtWidgets, QtNetwork
from functools import partial
# Initialize Qt resources from file resources.py
from .resources import *
from .GetMapCoordinates import GetMapCoordinates
# Import the code for the dialog
from .hqgis_dialog import HqgisDialog
import os.path
import requests, json, urllib
from PyQt5.QtCore import QVariant
from qgis.core import QgsPoint,QgsSymbol, QgsRendererRange, QgsGraduatedSymbolRenderer, QgsPointXY, QgsGeometry,QgsMapLayerProxyModel, QgsVectorLayer, QgsProject, QgsCoordinateReferenceSystem, QgsFeature, QgsField, QgsMessageLog, QgsNetworkAccessManager
from qgis.PyQt.QtWidgets import QProgressBar
from qgis.PyQt.QtCore import *
from qgis.utils import iface


class Hqgis:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Hqgis_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = HqgisDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Hqgis')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Hqgis')
        self.toolbar.setObjectName(u'Hqgis')
        self.getMapCoordinates = GetMapCoordinates(self.iface)
        self.getMapCoordTool=None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):

        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Hqgis', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/hereqgis/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Access the HERE API'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.loadCredFunction()

        self.dlg.getCreds.clicked.connect(self.getCredFunction)
        self.dlg.saveCreds.clicked.connect(self.saveCredFunction)
        self.dlg.loadCreds.clicked.connect(self.loadCredFunction)
        self.dlg.mapLayerBox.setAllowEmptyLayer(False)
        self.dlg.mapLayerBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.dlg.mapLayerBox.currentIndexChanged.connect(self.loadField)
        self.loadField()
        self.dlg.mapLayerBox_2.setAllowEmptyLayer(False)
        self.dlg.mapLayerBox_2.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.loadFields()
        self.dlg.mapLayerBox_2.currentIndexChanged.connect(self.loadFields)
        self.dlg.geocodeAddressButton.clicked.connect(self.geocode)
        self.dlg.batchGeocodeFieldButton.clicked.connect(self.batchGeocodeField)
        self.dlg.batchGeocodeFieldsButton.clicked.connect(self.batchGeocodeFields)

        self.dlg.calcRouteSingleButton.clicked.connect(self.calculateRouteSingle)

        #coordButton
        # Activate click tool in canvas.
        self.dlg.captureButton.setIcon(QIcon(os.path.join(os.path.dirname(__file__),"target.png")))
        self.dlg.captureButton_2.setIcon(QIcon(os.path.join(os.path.dirname(__file__),"target.png")))

        #self.dlg.captureButton.setChecked(True)

        self.dlg.toAddress.editingFinished .connect(partial(self.geocodeline,[self.dlg.toAddress,self.dlg.ToLabel]))
        #self.dlg.captureButton.setChecked(True)
        self.getMapCoordTool=self.getMapCoordinates
        self.getMapCoordTool.setButton(self.dlg.captureButton)
        self.getMapCoordTool.setButton(self.dlg.captureButton_2)
        self.getMapCoordTool.setButton(self.dlg.captureButton_4)
        self.getMapCoordTool.setButton(self.dlg.captureButton_3)
        self.getMapCoordTool.setWidget(self.dlg)
        self.iface.mapCanvas().setMapTool(self.getMapCoordTool)
        self.dlg.captureButton.pressed.connect(self.setGetMapToolCoordFrom)
        self.dlg.captureButton_2.pressed.connect(self.setGetMapToolCoordTo)
        self.dlg.fromAddress.editingFinished.connect(partial(self.geocodeline,[self.dlg.fromAddress,self.dlg.FromLabel]))
        self.dlg.captureButton_4.setIcon(QIcon(os.path.join(os.path.dirname(__file__),"target.png")))
        self.dlg.findPOISButton.setEnabled(False)
        self.dlg.captureButton_4.pressed.connect(self.setGetMapToolCoordPlace)
        self.dlg.captureButton_3.setIcon(QIcon(os.path.join(os.path.dirname(__file__),"target.png")))
        self.dlg.calcIsoButton.setEnabled(False)
        self.dlg.captureButton_3.pressed.connect(self.setGetMapToolCoordIso)

        self.dlg.findPOISButton.clicked.connect(self.getPlacesSingle)
        self.dlg.listWidget.sortItems(0)
        self.dlg.listWidget.itemSelectionChanged.connect(self.checkPlacesInput)
        self.dlg.placesAddress.editingFinished.connect(partial(self.geocodeline,[self.dlg.placesAddress,self.dlg.placeLabel, self.dlg.findPOISButton]))
        self.dlg.IsoAddress.editingFinished.connect(partial(self.geocodeline,[self.dlg.IsoAddress,self.dlg.IsoLabel, self.dlg.calcIsoButton]))
        self.dlg.metric.currentTextChanged.connect(self.selectMetric)
        self.dlg.calcIsoButton.clicked.connect(self.getIsochronesSingle)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&Hqgis'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
    def convertGeocodeResponse(self, responseAddress):
        geocodeResponse = {}
        try:
            geocodeResponse["Label"] = responseAddress["Location"]["Address"]["Label"]
        except:
            geocodeResponse["Label"] = ""
        try:
            geocodeResponse["Country"] = responseAddress["Location"]["Address"]["Country"]
        except:
            geocodeResponse["Country"] = ""
        try:
            geocodeResponse["State"] = responseAddress["Location"]["Address"]["State"]
        except:
            geocodeResponse["State"]  = ""
        try:
            geocodeResponse["County"] = responseAddress["Location"]["Address"]["County"]
        except:
            geocodeResponse["County"] = ""
        try:
            geocodeResponse["City"] = responseAddress["Location"]["Address"]["City"]
        except:
            geocodeResponse["City"] = ""
        try:
            geocodeResponse["District"] = responseAddress["Location"]["Address"]["District"]
        except:
            geocodeResponse["District"] = ""
        try:
            geocodeResponse["Street"] = responseAddress["Location"]["Address"]["Street"]
        except:
            geocodeResponse["Street"] = ""
        try:
            geocodeResponse["HouseNumber"] = responseAddress["Location"]["Address"]["HouseNumber"]
        except:
            geocodeResponse["HouseNumber"] = ""
        try:
            geocodeResponse["PostalCode"] = responseAddress["Location"]["Address"]["PostalCode"]
        except:
            geocodeResponse["PostalCode"] = ""
        try:
            geocodeResponse["Relevance"] = responseAddress["Relevance"]
        except:
            geocodeResponse["Relevance"] = None
        try:
            geocodeResponse["CountryQuality"] = responseAddress["MatchQuality"]["Country"]
        except:
            geocodeResponse["CountryQuality"] = None
        try:
            geocodeResponse["CityQuality"] = responseAddress["MatchQuality"]["City"]
        except:
            geocodeResponse["CityQuality"] = None
        try:
            geocodeResponse["StreetQuality"] = responseAddress["MatchQuality"]["Street"][0]
        except:
            geocodeResponse["StreetQuality"] = None
        try:
            geocodeResponse["NumberQuality"] = responseAddress["MatchQuality"]["HouseNumber"]
        except:
            geocodeResponse["NumberQuality"] = None
        try:
            geocodeResponse["MatchType"] = responseAddress["MatchType"]
        except:
            geocodeResponse["MatchType"] = ""
        return(geocodeResponse)

    def createGeocodedLayer(self):
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "AddressLayer",
            "memory"
        )
        layer.dataProvider().addAttributes([
            QgsField("id",QVariant.Int),
            QgsField("oldAddress",QVariant.String),
            QgsField("address",QVariant.String),
            QgsField("country",QVariant.String),
            QgsField("state",QVariant.String),
            QgsField("county",QVariant.String),
            QgsField("city",QVariant.String),
            QgsField("district",QVariant.String),
            QgsField("street",QVariant.String),
            QgsField("number",QVariant.String),
            QgsField("zip",QVariant.String),
            QgsField("relevance",QVariant.Double),
            QgsField("qu_country",QVariant.Double),
            QgsField("qu_city",QVariant.Double),
            QgsField("qu_street",QVariant.Double),
            QgsField("qu_number",QVariant.Double),
            QgsField("matchtype",QVariant.String)
        ])
        layer.updateFields()
        return(layer)
    def createPlaceLayer(self):
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "PlaceLayer",
            "memory"
        )
        layer.dataProvider().addAttributes([
            QgsField("id",QVariant.Int),
            QgsField("title",QVariant.String),
            QgsField("vicinity",QVariant.String),
            QgsField("distance",QVariant.Double),
            QgsField("category",QVariant.String),
        ])
        layer.updateFields()
        return(layer)
    def createIsoLayer(self):
        layer = QgsVectorLayer(
            "Polygon?crs=EPSG:4326",
            "isoLayer",
            "memory"
        )
        layer.dataProvider().addAttributes([
            QgsField("id",QVariant.Int),
            QgsField("range",QVariant.Int),
            QgsField("metric",QVariant.String),
            QgsField("mode",QVariant.String),
            QgsField("traffic",QVariant.String),
            QgsField("type",QVariant.String)
        ])
        layer.updateFields()
        
        return(layer)
    def createRouteLayer(self):
        layer = QgsVectorLayer(
            "Linestring?crs=EPSG:4326",
            "RouteLayer", 
            "memory"
        )
        layer.dataProvider().addAttributes([
            QgsField("id",QVariant.Int),
            QgsField("distance",QVariant.Double),
            QgsField("time",QVariant.Double),
            QgsField("mode",QVariant.String),
            QgsField("traffic",QVariant.String),
            QgsField("type",QVariant.String)
        ])
        layer.updateFields()
        return(layer)

    def messageShow(self, progress, count, max):
        if not progress:
            progressMessageBar = iface.messageBar().createMessage("Looping through " + str(max) +" records ...")
            progress = QProgressBar()
            progress.setMaximum(max)
            progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
            progressMessageBar.layout().addWidget(progress)
            iface.messageBar().pushWidget(progressMessageBar, level=1)
            iface.mainWindow().repaint()
        #    return progress
        if progress:
            progress.setValue(count)
        return(progress)

    def geocode(self):
        self.getCredentials()
        address = self.dlg.AddressInput.text()
        if address == "":
            address = "11 WallStreet, NewYork, USA"

        url = "https://geocoder.api.here.com/6.2/geocode.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&searchtext=" + address
        r = requests.get(url)
        try:
            #ass the response may hold more than one result we only use the best one:
            responseAddress = json.loads(r.text)["Response"]["View"][0]["Result"][0]
            geocodeResponse = self.convertGeocodeResponse(responseAddress)
            lat = responseAddress["Location"]["DisplayPosition"]["Latitude"]
            lng = responseAddress["Location"]["DisplayPosition"]["Longitude"]
            layer = self.createGeocodedLayer()
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lng,lat)))
            fet.setAttributes([
                0,
                address,
                geocodeResponse["Label"],
                geocodeResponse["Country"],
                geocodeResponse["State"],
                geocodeResponse["County"],
                geocodeResponse["City"],
                geocodeResponse["District"],
                geocodeResponse["Street"],
                geocodeResponse["HouseNumber"],
                geocodeResponse["PostalCode"],
                geocodeResponse["Relevance"],
                geocodeResponse["CountryQuality"],
                geocodeResponse["CityQuality"],
                geocodeResponse["StreetQuality"],
                geocodeResponse["NumberQuality"],
                geocodeResponse["MatchType"]
            ])
            #print("feature set")
            pr = layer.dataProvider()
            pr.addFeatures([fet])
            QgsProject.instance().addMapLayer(layer)
        except Exception as e:
            print(e)

    def batchGeocodeField(self):
        import time
        self.getCredentials()
        Resultlayer = self.createGeocodedLayer()
        pr = Resultlayer.dataProvider()
        layer = self.dlg.mapLayerBox.currentLayer()
        features = layer.getFeatures()
        ResultFeatureList = []

        #let's create the progress bar already with the number of features in the layer
        progressMessageBar = iface.messageBar().createMessage("Looping through " + str(layer.featureCount()) +" records ...")
        progress = QProgressBar()
        progress.setMaximum(layer.featureCount())
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        iface.messageBar().pushWidget(progressMessageBar, level=0)
        i = 0
        for feature in layer.getFeatures():
            url = "https://geocoder.api.here.com/6.2/geocode.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&searchtext=" + feature[self.dlg.fieldBox.currentField()]
            r = requests.get(url)
            try:
                responseAddress = json.loads(r.text)["Response"]["View"][0]["Result"][0]
                geocodeResponse = self.convertGeocodeResponse(responseAddress)
                lat = responseAddress["Location"]["DisplayPosition"]["Latitude"]
                lng = responseAddress["Location"]["DisplayPosition"]["Longitude"]
                ResultFet = QgsFeature()
                ResultFet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lng,lat)))
                ResultFet.setAttributes([
                    feature.id(),
                    feature[self.dlg.fieldBox.currentField()],
                    geocodeResponse["Label"],
                    geocodeResponse["Country"],
                    geocodeResponse["State"],
                    geocodeResponse["County"],
                    geocodeResponse["City"],
                    geocodeResponse["District"],
                    geocodeResponse["Street"],
                    geocodeResponse["HouseNumber"],
                    geocodeResponse["PostalCode"],
                    geocodeResponse["Relevance"],
                    geocodeResponse["CountryQuality"],
                    geocodeResponse["CityQuality"],
                    geocodeResponse["StreetQuality"],
                    geocodeResponse["NumberQuality"],
                    geocodeResponse["MatchType"]
                ])
                ResultFeatureList.append(ResultFet)
            except Exception as e:
                print(e)
            i += 1
            progress.setValue(i)

            #time.sleep(0.3)
        pr.addFeatures(ResultFeatureList)
        iface.messageBar().clearWidgets()
        QgsProject.instance().addMapLayer(Resultlayer)

    def batchGeocodeFields(self):
        import time, sys
        self.getCredentials()
        #mapping from inputs:

        Resultlayer = self.createGeocodedLayer()
        pr = Resultlayer.dataProvider()
        indexer = {}
        layer = self.dlg.mapLayerBox_2.currentLayer()
        indexer["country"]=layer.fields().indexFromName(self.dlg.CountryBox.currentField())
        indexer["state"]=layer.fields().indexFromName(self.dlg.StateBox.currentField())
        indexer["county"]=layer.fields().indexFromName(self.dlg.CountyBox.currentField())
        indexer["zip"]=layer.fields().indexFromName(self.dlg.ZipBox.currentField())
        indexer["city"]=layer.fields().indexFromName(self.dlg.CityBox.currentField())
        indexer["street"]=layer.fields().indexFromName(self.dlg.StreetBox.currentField())
        indexer["number"]=layer.fields().indexFromName(self.dlg.NumberBox.currentField())
        ResultFeatureList = [] #got result storing
        #precreate field-lists for API call:
        addressLists = {}
        for key in indexer.keys():
            if indexer[key] != -1:
                parts = []
                oldIDs = []
                features = layer.getFeatures()
                for fet in features:
                    oldIDs.append(fet.id())
                    parts.append(str(fet.attributes()[indexer[key]]))
                addressLists[key] = parts
                addressLists["oldIds"] = oldIDs

        #let's create the progress bar already with the number of features in the layer
        progressMessageBar = iface.messageBar().createMessage("Looping through " + str(layer.featureCount()) +" records ...")
        progress = QProgressBar()
        progress.setMaximum(layer.featureCount())
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        iface.messageBar().pushWidget(progressMessageBar, level=0)

        for id in range(0, layer.featureCount()-1):
            urlPart=""
            oldAddress=""
            for key in addressLists.keys():
                if key != "oldIds":
                    urlPart+="&" + key +  "=" + addressLists[key][id]
                    oldAddress += addressLists[key][id] + ","
            url = "https://geocoder.api.here.com/6.2/geocode.json?app_id=" + self.appId + "&app_code=" + self.appCode + urlPart
            r = requests.get(url)
            if r.status_code == 200:
                #sys.stdout.write("test" + url + "\\n")
                if len(json.loads(r.text)["Response"]["View"])>0:
                #as the response may hold more than one result we only use the best one:
                    responseAddress = json.loads(r.text)["Response"]["View"][0]["Result"][0]
                    geocodeResponse = self.convertGeocodeResponse(responseAddress)
                    lat = responseAddress["Location"]["DisplayPosition"]["Latitude"]
                    lng = responseAddress["Location"]["DisplayPosition"]["Longitude"]
                    ResultFet = QgsFeature()
                    ResultFet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lng,lat)))
                    ResultFet.setAttributes([
                        addressLists["oldIds"][id],
                        oldAddress,
                        geocodeResponse["Label"],
                        geocodeResponse["Country"],
                        geocodeResponse["State"],
                        geocodeResponse["County"],
                        geocodeResponse["City"],
                        geocodeResponse["District"],
                        geocodeResponse["Street"],
                        geocodeResponse["HouseNumber"],
                        geocodeResponse["PostalCode"],
                        geocodeResponse["Relevance"],
                        geocodeResponse["CountryQuality"],
                        geocodeResponse["CityQuality"],
                        geocodeResponse["StreetQuality"],
                        geocodeResponse["NumberQuality"],
                        geocodeResponse["MatchType"]
                    ])
                    ResultFeatureList.append(ResultFet)
            time.sleep(0.5)
            progress.setValue(id)
            #iface.mainWindow().repaint()
            time.sleep(0.5)
        pr.addFeatures(ResultFeatureList)
        iface.messageBar().clearWidgets()
        QgsProject.instance().addMapLayer(Resultlayer)
        self.dlg.exec_()
    def getCredentials(self):
        self.appId = self.dlg.AppId.text()
        self.appCode = self.dlg.AppCode.text()
    def getCredFunction(self):
        import webbrowser
        webbrowser.open('https://developer.here.com/')
    def saveCredFunction(self):
        print("save credits")
        self.dlg.credentialInteraction.setText("")
        fileLocation = os.path.dirname(os.path.realpath(__file__))+ os.sep + "creds"
        with open(fileLocation + os.sep + 'credentials.json', 'w') as outfile:
            stringJSON = {"ID": self.dlg.AppId.text(), "CODE":  self.dlg.AppCode.text()}
            json.dump(stringJSON, outfile)
        self.dlg.credentialInteraction.setText("credentials saved to " + fileLocation + os.sep + 'credentials.json')
    def loadCredFunction(self):
        import json, os
        #fileLocation = QFileDialog.getOpenFileName(self.dlg, "JSON with credentials",os.path.dirname(os.path.realpath(__file__))+ os.sep + "creds", "JSON(*.JSON)")
        #print(fileLocation)
        scriptDirectory = os.path.dirname(os.path.realpath(__file__))
        self.dlg.credentialInteraction.setText("")
        print(scriptDirectory)
        try:
            import os
            scriptDirectory = os.path.dirname(os.path.realpath(__file__))
            with open(scriptDirectory + os.sep + 'creds' + os.sep + 'credentials.json') as f:
                data = json.load(f)
                self.dlg.AppId.setText(data["ID"])
                self.dlg.AppCode.setText(data["CODE"])
            self.dlg.credentialInteraction.setText("credits used from " + scriptDirectory + os.sep + 'creds' + os.sep + 'credentials.json')
        except:
            self.dlg.credentialInteraction.setText("no credits found in. Check for file" + scriptDirectory + os.sep + 'creds' + os.sep + 'credentials.json')
            #self.dlg.geocodeButton.setEnabled(False)

    def loadFields(self):
        self.dlg.CountryBox.setLayer(self.dlg.mapLayerBox_2.currentLayer())
        self.dlg.StateBox.setLayer(self.dlg.mapLayerBox_2.currentLayer())
        self.dlg.CountyBox.setLayer(self.dlg.mapLayerBox_2.currentLayer())
        self.dlg.ZipBox.setLayer(self.dlg.mapLayerBox_2.currentLayer())
        self.dlg.CityBox.setLayer(self.dlg.mapLayerBox_2.currentLayer())
        self.dlg.StreetBox.setLayer(self.dlg.mapLayerBox_2.currentLayer())
        self.dlg.NumberBox.setLayer(self.dlg.mapLayerBox_2.currentLayer())
        self.dlg.CountryBox.setAllowEmptyFieldName(True)
        self.dlg.StateBox.setAllowEmptyFieldName(True)
        self.dlg.CountyBox.setAllowEmptyFieldName(True)
        self.dlg.ZipBox.setAllowEmptyFieldName(True)
        self.dlg.CityBox.setAllowEmptyFieldName(True)
        self.dlg.StreetBox.setAllowEmptyFieldName(True)
        self.dlg.NumberBox.setAllowEmptyFieldName(True)
    def loadField(self):
        self.dlg.fieldBox.setLayer(self.dlg.mapLayerBox.currentLayer())
        self.dlg.fieldBox.setAllowEmptyFieldName(True)
    def setGetMapToolCoordFrom(self):
        """ Method that is connected to the target button. Activates and deactivates map tool """
        if self.dlg.captureButton.isChecked():
            print("true FROM")
            self.iface.mapCanvas().unsetMapTool(self.getMapCoordTool)
            self.dlg.captureButton_2.setChecked(True)
            return
        if self.dlg.captureButton.isChecked() == False:
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
            print("false FROM")
            self.iface.mapCanvas().setMapTool(self.getMapCoordTool)
            self.dlg.captureButton_2.setChecked(False)
            return
    def setGetMapToolCoordTo(self):
        if self.dlg.captureButton_2.isChecked():
            print("true TO")
            self.dlg.captureButton.setChecked(True)
            self.iface.mapCanvas().unsetMapTool(self.getMapCoordTool)
            return
        if self.dlg.captureButton_2.isChecked() == False:
            print("false TO")
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
            self.dlg.captureButton.setChecked(False)
            self.iface.mapCanvas().setMapTool(self.getMapCoordTool)
            return
    def setGetMapToolCoordPlace(self):
        if self.dlg.captureButton_4.isChecked():
            self.iface.mapCanvas().unsetMapTool(self.getMapCoordTool)
            return
        if self.dlg.captureButton_4.isChecked() == False:
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
            self.iface.mapCanvas().setMapTool(self.getMapCoordTool)
            return
    def setGetMapToolCoordIso(self):
        if self.dlg.captureButton_3.isChecked():
            self.iface.mapCanvas().unsetMapTool(self.getMapCoordTool)
            return
        if self.dlg.captureButton_3.isChecked() == False:
            self.iface.mapCanvas().setCursor(Qt.CrossCursor)
            self.iface.mapCanvas().setMapTool(self.getMapCoordTool)
            return

    def geocodelineFrom(self):
        self.getCredentials()
        address = self.dlg.fromAddress.text()
        url = "https://geocoder.api.here.com/6.2/geocode.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&searchtext=" + address
        r = requests.get(url)
        try:
            #ass the response may hold more than one result we only use the best one:
            responseAddress = json.loads(r.text)["Response"]["View"][0]["Result"][0]
            #geocodeResponse = self.convertGeocodeResponse(responseAddress)
            lat = responseAddress["Location"]["DisplayPosition"]["Latitude"]
            lng = responseAddress["Location"]["DisplayPosition"]["Longitude"]
            self.dlg.FromLabel.setText(str("%.5f" % lat)+','+str("%.5f" % lng))
        except:
            print("something went wrong")
    def geocodeline(self, lineEdits):
        self.getCredentials()
        address = lineEdits[0].text()
        url = "https://geocoder.api.here.com/6.2/geocode.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&searchtext=" + address
        r = requests.get(url)
        try:
            #ass the response may hold more than one result we only use the best one:
            responseAddress = json.loads(r.text)["Response"]["View"][0]["Result"][0]
            #geocodeResponse = self.convertGeocodeResponse(responseAddress)
            lat = responseAddress["Location"]["DisplayPosition"]["Latitude"]
            lng = responseAddress["Location"]["DisplayPosition"]["Longitude"]
            lineEdits[1].setText(str("%.5f" % lat)+','+str("%.5f" % lng))
        except:
            print("something went wrong")
        try:
            if lineEdits[1].text() != "":
                lineEdits[2].setEnabled(True)
            else:
                lineEdits[2].setEnabled(False)
        except:
            print("routing")
    def geocodelinePlace(self):
        self.getCredentials()
        address = self.dlg.placesAddress.text()
        self.dlg.findPOISButton.setEnabled(True)
        print(self.dlg.findPOISButton.enabled())
        if address != "":
            url = "https://geocoder.api.here.com/6.2/geocode.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&searchtext=" + address
            r = requests.get(url)
            try:
                #ass the response may hold more than one result we only use the best one:
                responseAddress = json.loads(r.text)["Response"]["View"][0]["Result"][0]
                #geocodeResponse = self.convertGeocodeResponse(responseAddress)
                lat = responseAddress["Location"]["DisplayPosition"]["Latitude"]
                lng = responseAddress["Location"]["DisplayPosition"]["Longitude"]
                self.dlg.placeLabel.setText(str("%.5f" % lat)+','+str("%.5f" % lng))
            except:
                print("something went wrong")
    def checkPlacesInput(self):
        if self.dlg.placeLabel.text() != "" and len(self.dlg.listWidget.selectedItems())>0:
            self.dlg.findPOISButton.setEnabled(True)
        else:
            self.dlg.findPOISButton.setEnabled(False)
    def selectMetric(self):
        if self.dlg.metric.currentText() == "Time":
            self.dlg.travelDistances.setEnabled(False)
            self.dlg.travelTimes.setEnabled(True)
        else:
            self.dlg.travelDistances.setEnabled(True)
            self.dlg.travelTimes.setEnabled(False)
    def calculateRouteSingle(self):
        self.getCredentials()
        type = self.dlg.Type.currentText()
        mode = self.dlg.TransportMode.currentText()
        traffic = self.dlg.trafficMode.currentText()
        url = "https://route.api.here.com/routing/7.2/calculateroute.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&routeAttributes=shape&mode=" + type + ";" + mode + ";traffic:" + traffic + "&waypoint0=geo!"  + self.dlg.FromLabel.text() + "&waypoint1=geo!" + self.dlg.ToLabel.text()
        print(url)
        r = requests.get(url)

        if r.status_code == 200:
            try:
                self.dlg.status2.setText("distance: " + str(json.loads(r.text)["response"]["route"][0]["summary"]["distance"]) +  " time: " + str(json.loads(r.text)["response"]["route"][0]["summary"]["baseTime"]))
                if self.dlg.routeLayerCheckBox.checkState():
                    layer = self.createRouteLayer()
                    responseRoute = json.loads(r.text)["response"]["route"][0]["shape"]
                    vertices = []
                    for routePoint in responseRoute:
                        lat = float(routePoint.split(",")[0])
                        lng = float(routePoint.split(",")[1])
                        vertices.append(QgsPoint(lng,lat))
                    fet = QgsFeature()
                    fet.setGeometry(QgsGeometry.fromPolyline(vertices))
                    fet.setAttributes([
                        0,
                        json.loads(r.text)["response"]["route"][0]["summary"]["distance"],
                        json.loads(r.text)["response"]["route"][0]["summary"]["baseTime"],
                        mode,
                        traffic,
                        type
                    ])
                    pr = layer.dataProvider()
                    pr.addFeatures([fet])
                    QgsProject.instance().addMapLayer(layer)
            except Exception as e:
                print(e)
    def getPlacesSingle(self):
        self.getCredentials()
        radius = self.dlg.RadiusBox.value()
        categories = self.dlg.listWidget.selectedItems()
        categoriesList = []
        for category in categories:
            categoriesList.append(category.text())
        categories = ",".join(categoriesList)
        coordinates = self.dlg.placeLabel.text()

        url = "https://places.cit.api.here.com/places/v1/discover/explore?in=" + coordinates + ";r=" + str(radius*1000) + "&cat=" + categories +"&drilldown=false&size=10000&X-Mobility-Mode=drive&app_id=" + self.appId + "&app_code=" + self.appCode
        r = requests.get(url)
        print(url)
        if r.status_code == 200:
            if len(json.loads(r.text)["results"]["items"])>0:
                try:
                    #ass the response may hold more than one result we only use the best one:
                    responsePlaces = json.loads(r.text)["results"]["items"]
                    layer = self.createPlaceLayer()
                    features = []
                    for place in responsePlaces:
                        lat = place["position"][0]
                        lng = place["position"][1]
                        fet = QgsFeature()
                        fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lng,lat)))
                        fet.setAttributes([
                            place["id"],
                            place["title"],
                            place["vicinity"],
                            place["distance"],
                            place["category"]["title"]
                        ])
                        features.append(fet)
                    pr = layer.dataProvider()
                    pr.addFeatures(features)
                    QgsProject.instance().addMapLayer(layer)
                except Exception as e:
                    print(e)
    def getIsochronesSingle(self):
        print("get Isochrones")
        self.getCredentials()
        #getting intervals:
        if self.dlg.metric.currentText() == "Time":
            intervalArray = self.dlg.travelTimes.text().split(",")
        else:
            intervalArray = self.dlg.travelDistances.text().split(",")
        ranges = [int(x) for x in intervalArray]
        #create colors:
        layer = self.createIsoLayer()
        if len(ranges)>1:
            ranges.sort()
            rangediff = ranges[-1] - ranges[0]
            sym = QgsSymbol.defaultSymbol(layer.geometryType())
            rngs=[]
            sym.setColor(QColor(0,255,0,255))
            rng = QgsRendererRange(0, ranges[0], sym, str(0) + " - " + str(ranges[0]))
            rngs.append(rng)
            for rangeItem in range(1,len(ranges)-1):
                sym = QgsSymbol.defaultSymbol(layer.geometryType())
                #colors.append([int(0 + ((255/range)*(rangeItem-ranges[0]))),int(255-((255/range)*(rangeItem-ranges[0])),0])
                sym.setColor(QColor(int(0 + ((255/rangediff)*(ranges[rangeItem]-ranges[0]))),int(255-((255/rangediff)*(ranges[rangeItem]-ranges[0]))),0,255))
                print(int(0 + ((255/rangediff)*(ranges[rangeItem]-ranges[0]))),int(255-((255/rangediff)*(ranges[rangeItem]-ranges[0]))),0,255)
                rng = QgsRendererRange(ranges[rangeItem-1]+1, ranges[rangeItem], sym, str(ranges[rangeItem-1]+1) + " - " + str(ranges[rangeItem]))
                rngs.append(rng)
            sym = QgsSymbol.defaultSymbol(layer.geometryType())
            sym.setColor(QColor(255,0,0,255))
            rng = QgsRendererRange(ranges[-2]+1, ranges[-1], sym, str(ranges[-2]+1) + " - " + str(ranges[-1]))
            rngs.append(rng)
            field="range"
            renderer = QgsGraduatedSymbolRenderer(field, rngs)
        type = self.dlg.Type_2.currentText()
        mode = self.dlg.TransportMode_2.currentText()
        traffic = self.dlg.trafficMode_2.currentText()
        url = "https://isoline.route.api.here.com/routing/7.2/calculateisoline.json?" + \
        "app_id=" + self.appId + \
        "&app_code=" + self.appCode +\
        "&range=" + ",".join(intervalArray)+ \
        "&mode=" + type + ";" + mode + ";traffic:" + traffic + \
        "&rangetype=" + self.dlg.metric.currentText().lower() + \
        "&" + self.dlg.OriginDestination.currentText().lower() + "=geo!" + \
        self.dlg.IsoLabel.text()
        r = requests.get(url)
        print(url)

        if r.status_code == 200:
            if len(json.loads(r.text)["response"]["isoline"])>0:
                try:

                    response = json.loads(r.text)["response"]["isoline"]
                    features=[]
                    fid = 0
                    for poly in response:
                        coordinates = []
                        for vertex in poly["component"][0]["shape"]:
                            lat = float(vertex.split(",")[0])
                            lng = float(vertex.split(",")[1])
                            coordinates.append(QgsPointXY(lng,lat))
                        fet = QgsFeature()
                        fet.setGeometry(QgsGeometry.fromPolygonXY([coordinates]))
                        fet.setAttributes([
                            fid,
                            poly["range"],
                            self.dlg.metric.currentText().lower(),
                            mode,
                            traffic,
                            type
                        ])
                        features.append(fet)
                        fid+=1
                    pr = layer.dataProvider()
                    pr.addFeatures(reversed(features))
                    if len(ranges)>1:
                        layer.setRenderer(renderer)
                    layer.setOpacity(0.5)
                    QgsProject.instance().addMapLayer(layer)
                except Exception as e:
                    print(e)

    def run(self):

        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        #try to load credentials:

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            #get app code/id

            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass