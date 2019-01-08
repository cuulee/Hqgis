# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HEREqgis
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
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog
from PyQt5 import QtGui, QtWidgets, QtNetwork

# Initialize Qt resources from file resources.py
from .resources import *
from .GetMapCoordinates import GetMapCoordinates
# Import the code for the dialog
from .hereqgis_dialog import HEREqgisDialog
import os.path
import requests, json, urllib
from PyQt5.QtCore import QVariant
from qgis.core import QgsPointXY, QgsGeometry, QgsVectorLayer, QgsProject, QgsFeature, QgsField, QgsMessageLog, QgsNetworkAccessManager
from qgis.PyQt.QtWidgets import QProgressBar
from qgis.PyQt.QtCore import *
from qgis.utils import iface


class HEREqgis:
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
            'HEREqgis_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = HEREqgisDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&HEREqgis')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'HEREqgis')
        self.toolbar.setObjectName(u'HEREqgis')
        self.getMapCoordinates = GetMapCoordinates(self.iface)
        self.getMapCoordTool=None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):

        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('HEREqgis', message)


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


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&HEREqgis'),
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
            """Point?
            crs=epsg:4326
            &index=yes""",
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
            time.sleep(0.3)
            progress.setValue(i)
            time.sleep(0.3)
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
    def geocodelineTo(self):
        self.getCredentials()
        address = self.dlg.toAddress.text()
        url = "https://geocoder.api.here.com/6.2/geocode.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&searchtext=" + address
        r = requests.get(url)
        try:
            #ass the response may hold more than one result we only use the best one:
            responseAddress = json.loads(r.text)["Response"]["View"][0]["Result"][0]
            #geocodeResponse = self.convertGeocodeResponse(responseAddress)
            lat = responseAddress["Location"]["DisplayPosition"]["Latitude"]
            lng = responseAddress["Location"]["DisplayPosition"]["Longitude"]
            self.dlg.ToLabel.setText(str("%.5f" % lat)+','+str("%.5f" % lng))
        except:
            print("something went wrong")
    def calculateRouteSingle(self):
        self.getCredentials()
        type = self.dlg.Type.currentText()
        mode = self.dlg.TransportMode.currentText()
        traffic = self.dlg.trafficMode.currentText()
        url = "https://route.api.here.com/routing/7.2/calculateroute.json?app_id=" + self.appId + "&app_code=" + self.appCode + "&mode=" + type + ";" + mode + ";traffic:" + traffic + "&waypoint0=geo!"  + self.dlg.FromLabel.text() + "&waypoint1=geo!" + self.dlg.ToLabel.text()
        print(url)
        r = requests.get(url)
        self.dlg.status2.setText("distance: " + str(json.loads(r.text)["response"]["route"][0]["summary"]["distance"]) +  " time: " + str(json.loads(r.text)["response"]["route"][0]["summary"]["baseTime"]))

    def getPlacesSingle(self):
        print(places)

    def run(self):
        from qgis.core import QgsProject
        from qgis.core import QgsMapLayerProxyModel
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        #try to load credentials:
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
        self.dlg.captureButton.pressed.connect(self.setGetMapToolCoordFrom)
        self.dlg.captureButton_2.pressed.connect(self.setGetMapToolCoordTo)
        self.dlg.fromAddress.editingFinished .connect(self.geocodelineFrom)
        self.dlg.toAddress.editingFinished .connect(self.geocodelineTo)
        #self.dlg.captureButton.setChecked(True)
        self.getMapCoordTool=self.getMapCoordinates
        self.getMapCoordTool.setButton(self.dlg.captureButton)
        self.getMapCoordTool.setButton(self.dlg.captureButton_2)
        self.getMapCoordTool.setWidget(self.dlg)
        self.iface.mapCanvas().setMapTool(self.getMapCoordTool)
        self.dlg.findPOISButton.clicked.connect(self.getPlacesSingle)
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            #get app code/id

            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
