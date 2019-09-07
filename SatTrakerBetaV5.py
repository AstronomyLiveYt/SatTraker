from tkinter import *
from tkinter import filedialog
import ephem
import math
import os
import cv2
import numpy as np
import sys
import time
import datetime
import re
import json
import geocoder
import serial
import io
import threading
import win32com.client
import imutils
from PIL import Image as PILImage, ImageTk
from urllib.request import urlopen

class trackSettings:
    
    objectfollow = False
    telescopetype = 'LX200'
    mounttype = 'AltAz'
    tracking = False
    boxSize = 50
    mousecoords = (320,240)
    degorhours = 'Degrees'
    mainviewX = 320
    mainviewY = 240
    setcenter = False
    imagescale = 1.0
    orbitFile = ''
    fileSelected = False
    Lat = 0.0
    Lon = 0.0
    trackingsat = False
    trackingtype = 'Features'
    minbright = 50
    clickpixel = 0
    maxpixel = 255
    flip = 'NoFlip'
    foundtarget = False
    rotate = 0
    calibratestart = False
    

class videotrak:
    
    def get_x_y(img, roibox, imageroi):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if trackSettings.trackingtype == 'Features':
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(2,2))
            img = clahe.apply(img)
        #remember how big the total image and ROI are 
        origheight, origwidth = img.shape[:2]
        roiheight, roiwidth = imageroi.shape[:2]
        #Set up the end of the maximum search time
        searchend = time.time() + 0.2
        finalroidiff = float('inf')
        difflowered = False
        keepgoing = True
        #pull the latest searchx and searchy coordinates from the last known position
        searchx1 = roibox[0][0]
        searchy1 = roibox[0][1]
        if trackSettings.trackingtype == 'Features':
            while keepgoing is True:
                for ycheck in range((searchy1-15),(searchy1+15)):
                    if time.time() > searchend:
                        break
                    for xcheck in range((searchx1-15),(searchx1+15)):
                        #check and make sure the new position of the region of interest won't put us over the border of the window, correct back to the edge of border if it would, otherwise take the new roi coordinates
                        if xcheck < 0: 
                            xcheck = 0
                        elif xcheck > (origwidth - roiwidth):
                            xcheck = (origwidth - roiwidth)
                        if ycheck < 0: 
                            ycheck = 0
                        elif ycheck > (origheight - roiheight):
                            ycheck = (origheight - roiheight)
            #set up the roi to search within the original image
                        imagecomp = img[ycheck:int(ycheck+roiheight),xcheck:int(xcheck+roiwidth)]
            #subtract the reference roi from the search area and get the difference of the arrays
                        imagecompforsub = imagecomp.astype(np.int8)
                        imageroiforsub = imageroi.astype(np.int8)
                        imagediff = imagecompforsub - imageroiforsub
                        imagediff = np.absolute(imagediff)
                        imagediff = np.sum(imagediff)
                        imagediff = (imagediff/(np.sum(imageroi)))*100
            #if we dropped to a new minimum, save the new minimum diff and save the x and y coordinates we're at.  Set diff lowered flag to true
                        if imagediff < finalroidiff:
                            finalroidiff = imagediff
                            searchx2 = xcheck
                            searchy2 = ycheck
                            difflowered = True
            #check if we ran out of time
                        if time.time() > searchend:
                            break   
            #back on the keep going loop, check if the diff lowered in the last search run.  If not, we found a local minimum and don't need to keep going.  If we did, start a new search around the new location
                if difflowered is True:
                    keepgoing = True
                    difflowered = False
                else:
                    keepgoing = False
                if time.time() > searchend:
                    print('outtatime')
                    break   
            #print(finalroidiff)
            #figure out if the difference from roi is low enough to be acceptable
            if finalroidiff < 20:
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s'):
                    need_track_feature = True
                searchx1last = searchx2
                searchy1last = searchy2
                learnimg = img[searchy1last:(searchy1last+roiheight),searchx1last:(searchx1last+roiwidth)]
                imageroi = (imageroi * 0.9) + (learnimg * 0.1)
                roibox = [(searchx1last,searchy1last), ((searchx1last+roiwidth),(searchy1last+roiheight))]
                trackSettings.foundtarget = True
            else:
                #print("Didn't find it, keep looking at last known coordinates.")
                searchx1last = roibox[0][0]
                searchy1last = roibox[0][1]
                trackSettings.foundtarget = False
        if trackSettings.trackingtype == 'Bright':
            blurred = cv2.GaussianBlur(img, (5, 5), 0)
            blurred = blurred[searchy1:int(searchy1+roiheight),searchx1:int(searchx1+roiwidth)]
            thresh = cv2.threshold(blurred, float(trackSettings.minbright), 255, cv2.THRESH_BINARY)[1]
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE)
            #cnts = cnts[0]
            cX = []
            cY = []
            #for c in cnts:
            M = cv2.moments(cnts[0])
            try:
                cX.append(int(M["m10"] / M["m00"]))
                cY.append(int(M["m01"] / M["m00"]))
                framestabilized = True
                trackSettings.foundtarget = True
            except:
                print('unable to track this frame')
                trackSettings.foundtarget = False
            if len(cX) > 0:
                cXdiff = (roiwidth/2) - cX[0]
                cYdiff = (roiheight/2) - cY[0]
                searchx1 = int(searchx1 -cXdiff)
                searchy1 = int(searchy1 -cYdiff)
                if searchx1 < 0:
                    searchx1 = 0
                if searchy1 < 0:
                    searchy1 = 0
            roibox = [(searchx1,searchy1), ((searchx1+roiwidth),(searchy1+roiheight))]
            imageroi = thresh.copy()
        return(roibox, imageroi)
    
class buttons:       
    def __init__(self, master):
        self.collect_images = False
        self.topframe = Frame(master)
        master.winfo_toplevel().title("SatTraker")
        self.topframe.pack(side=TOP)
        self.textframe = Frame(master)
        self.textframe.pack(side=BOTTOM)
        self.bottomframe = Frame(master)
        self.bottomframe.pack(side=BOTTOM)
        self.menu = Menu(master)
        master.config(menu=self.menu)
        
        master.bind("<Up>", self.goup)
        master.bind("<Left>", self.goleft)
        master.bind("<Down>", self.godown)
        master.bind("<Right>", self.goright)
        
        self.labelLat = Label(self.bottomframe, text='Latitude (N+)')
        self.labelLat.grid(row=5, column = 0)
        self.entryLat = Entry(self.bottomframe)
        self.entryLat.grid(row = 5, column = 1)
        self.labelLon = Label(self.bottomframe, text='Longitude (E+)')
        self.labelLon.grid(row=6, column = 0)
        self.entryLon = Entry(self.bottomframe)
        self.entryLon.grid(row = 6, column = 1)
        
        #self.labelBright = Label(self.bottomframe, text='Minimum Brightness')
        #self.labelBright.grid(row=8, column = 0)
        #self.entryBright = Entry(self.bottomframe)
        #self.entryBright.grid(row = 8, column = 1)
        
        try:
            config = open('Satconfig.txt', 'r')
            clines = [line.rstrip('\n') for line in config]
            trackSettings.telescopetype = str(clines[0])
            trackSettings.mainviewX = int(clines[3])
            trackSettings.mainviewY = int(clines[4])
            trackSettings.imagescale = float(clines[5])
            trackSettings.Lat = float(clines[6])
            trackSettings.Lon = float(clines[7])
            trackSettings.trackingtype = str(clines[8])
            trackSettings.minbright = float(clines[9])
            trackSettings.flip = str(clines[10])
            trackSettings.mounttype = str(clines[11])
            trackSettings.rotate = int(clines[12])
            config.close()
        except:
            print('Config file not present or corrupted.')
        
        try:
            geolocation = geocoder.ip('me')
            #self.entryLat.insert(0, geolocation.latlng[0])
            #self.entryLon.insert(0, geolocation.latlng[1])
            self.entryLat.insert(0, trackSettings.Lat)
            self.entryLon.insert(0, trackSettings.Lon)
        except:
            self.entryLat.insert(0, trackSettings.Lat)
            self.entryLon.insert(0, trackSettings.Lon)

        
        #self.entryBright.insert(0, trackSettings.minbright)
        self.startButton = Button(self.bottomframe, text='Start Camera', command=self.set_img_collect)
        self.startButton.grid(row=1, column = 0)
        self.startButton2 = Button(self.bottomframe, text='Camera Calibration', command=self.start_calibration)
        self.startButton2.grid(row=4, column = 0)
        self.startButton3 = Button(self.bottomframe, text='Set Center Point', command=self.set_center)
        self.startButton3.grid(row=4, column = 1)
        self.startButton4 = Button(self.bottomframe, text='Start Tracking Satellite', command=self.start_sat_track)
        self.startButton4.grid(row=7, column = 1)
        self.startButton5 = Button(self.bottomframe, text='Connect Scope', command=self.set_tracking)
        self.startButton5.grid(row=1, column = 1)
        self.ComLabel = Label(self.bottomframe, text='COM Port')
        self.ComLabel.grid(row = 2, column = 0)
        self.entryCom = Entry(self.bottomframe)
        self.entryCom.grid(row = 2, column = 1)
        self.textbox = Text(self.textframe, height=4, width=100)
        self.textbox.grid(row=1, column=0)
        try:
            self.entryCom.insert(0, clines[1])
        except:
            self.entryCom.insert(0, 0)
            
        self.CameraLabel = Label(self.bottomframe, text='Camera Number')
        self.CameraLabel.grid(row = 3, column = 0)
        self.entryCam = Entry(self.bottomframe)
        self.entryCam.grid(row = 3, column = 1)
        try:
            self.entryCam.insert(0, clines[2])
        except:
            self.entryCam.insert(0, 0)
        
        self.fileMenu = Menu(self.menu)
        self.menu.add_cascade(label='File', menu=self.fileMenu)
        self.fileMenu.add_command(label='Select TLE File...', command=self.filePicker)
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label='Exit and Save Configuration', command=self.exitProg)
        
        self.telescopeMenu = Menu(self.menu)
        self.menu.add_cascade(label='Telescope Type', menu=self.telescopeMenu)
        self.telescopeMenu.add_command(label='LX200 Classic Alt/Az', command=self.setLX200AltAz)
        self.telescopeMenu.add_command(label='LX200 Classic Equatorial', command=self.setLX200Eq)
        self.telescopeMenu.add_command(label='ASCOM Alt/Az', command=self.setASCOMAltAz)
        self.telescopeMenu.add_command(label='ASCOM Equatorial', command=self.setASCOMEq)
        
        self.trackingMenu = Menu(self.menu)
        self.menu.add_cascade(label='Tracking Type', menu=self.trackingMenu)
        self.trackingMenu.add_command(label='Feature Tracking', command=self.setFeatureTrack)
        self.trackingMenu.add_command(label='Brightness Tracking', command=self.setBrightTrack)
        
        self.imageMenu = Menu(self.menu)
        self.menu.add_cascade(label='Image Orientation', menu=self.imageMenu)
        self.imageMenu.add_command(label='Normal Orientation', command=self.setNoFlip)
        self.imageMenu.add_command(label='Vertical Flip', command=self.setVerticalFlip)
        self.imageMenu.add_command(label='Horizontal Flip', command=self.setHorizontalFlip)
        self.imageMenu.add_command(label='Vertical and Horizontal Flip', command=self.setVerticalHorizontalFlip)
        self.imageMenu.add_command(label='Rotate Image 0 Degrees', command=self.set0Rotate)
        self.imageMenu.add_command(label='Rotate Image 90 Degrees', command=self.setPos90Rotate)
        self.imageMenu.add_command(label='Rotate Image -90 Degrees', command=self.setNeg90Rotate)
        self.imageMenu.add_command(label='Rotate Image 180 Degrees', command=self.set180Rotate)
        
    def setNoFlip(self):
        trackSettings.flip = 'NoFlip'
    
    def setVerticalFlip(self):
        trackSettings.flip = 'VerticalFlip'    
    
    def setHorizontalFlip(self):
        trackSettings.flip = 'HorizontalFlip'
        
    def setVerticalHorizontalFlip(self):
        trackSettings.flip = 'VerticalHorizontalFlip'
        
    def set0Rotate(self):
        trackSettings.rotate = 0
    
    def setPos90Rotate(self):
        trackSettings.rotate = 90
        
    def setNeg90Rotate(self):
        trackSettings.rotate = -90
        
    def set180Rotate(self):
        trackSettings.rotate = 180
        
    def exitProg(self):
        config = open('satconfig.txt','w')
        config.write(str(trackSettings.telescopetype)+'\n')
        config.write(str(self.entryCom.get()) + '\n')
        config.write(str(self.entryCam.get()) + '\n')
        config.write(str(trackSettings.mainviewX) + '\n')
        config.write(str(trackSettings.mainviewY) + '\n')
        config.write(str(trackSettings.imagescale) + '\n')
        config.write(str(self.entryLat.get())+'\n')
        config.write(str(self.entryLon.get())+'\n')
        config.write(str(trackSettings.trackingtype) + '\n')
        config.write(str(trackSettings.minbright)+'\n')
        config.write(str(trackSettings.flip)+'\n')
        config.write(str(trackSettings.mounttype)+'\n')
        config.write(str(trackSettings.rotate)+'\n')
        config.close()
        sys.exit()
    
    def filePicker(self):
        trackSettings.orbitFile = filedialog.askopenfilename(initialdir = ".",title = "Select TLE file",filetypes = (("text files","*.txt"),("tle files","*.tle"),("all files","*.*")))
        trackSettings.fileSelected = True
        print(trackSettings.orbitFile)
        self.textbox.insert(END, str(str(trackSettings.orbitFile)+'\n'))
        self.textbox.see('end')
    
    def start_sat_track(self):
        if trackSettings.trackingsat is False:
            trackSettings.trackingsat = True
        else:
            trackSettings.trackingsat = False
            self.startButton4.configure(text='Start Tracking Satellite')
            if trackSettings.telescopetype == 'ASCOM' and trackSettings.trackingsat is False:
                self.tel.MoveAxis(0, 0.0)
                self.tel.MoveAxis(1, 0.0)
                self.tel.AbortSlew()
        if trackSettings.tracking is False:
            print('Connect the Scope First!')
            self.textbox.insert(END, 'Connect the Scope First!\n')
            self.textbox.see('end')
        if self.collect_images is False:
            print('Start Camera First!')
            self.textbox.insert(END, 'Start Camera First!\n')
            self.textbox.see('end')
        if trackSettings.fileSelected is False:
            print('Select TLE File First!')
            self.textbox.insert(END, 'Select TLE File First!\n')
            self.textbox.see('end')
        if trackSettings.tracking is True and self.collect_images is True and trackSettings.trackingsat is True and trackSettings.fileSelected is True:
            with open(trackSettings.orbitFile) as f:
                lines = [line.rstrip('\n') for line in f]
                for idx, line in enumerate(lines):
                    line1 = lines[0]
                    line2 = lines[1]
                    line3 = lines[2]
                self.observer = ephem.Observer()
                self.observer.lat = str(self.entryLat.get())
                self.observer.lon = str(self.entryLon.get())
                self.observer.elevation = 0
                self.observer.pressure = 1013
                self.sat = ephem.readtle(line1,line2,line3)
            self.sattrackthread = threading.Thread(target=self.sat_track)
            self.startButton4.configure(text='Stop Tracking Satellite')
            self.sattrackthread.start()
        
    def sat_track(self):
        firstslew = True
        altcorrect = 0
        azcorrect = 0
        deccorrect = 0
        racorrect = 0
        i = 0
        while trackSettings.trackingsat is True:
            if firstslew is True:
                self.diffazlast = 0
                self.diffaltlast = 0
                self.diffralast = 0
                self.diffdeclast = 0
                self.lasttotaldiff = 0.0
                self.sat.compute(self.observer)
                self.radalt = self.sat.alt
                self.radaz = self.sat.az 
                if trackSettings.telescopetype == 'LX200':
                    if trackSettings.mounttype == 'AltAz':
                        sataz = math.degrees(self.sat.az) + 180
                        if sataz > 360:
                            sataz = sataz - 360
                        sataz = math.radians(sataz)
                        self.radaz = sataz
                        self.rad_to_sexagesimal_alt()
                        targetcoordaz = str(':Sz ' + str(self.az_d)+'*'+str(self.az_m)+':'+str(int(self.az_s))+'#')
                        targetcoordalt = str(':Sa ' + str(self.alt_d)+'*'+str(self.alt_m)+':'+str(int(self.alt_s))+'#')
                        self.ser.write(str.encode(targetcoordaz))
                        self.ser.write(str.encode(targetcoordalt))
                        self.ser.write(str.encode(':MA#'))
                        print(targetcoordaz, targetcoordalt)
                        self.textbox.insert(END, str('Az: ' + str(targetcoordaz) + 'Alt: ' + str(targetcoordalt)+ '\n'))
                        self.textbox.see('end')
                    if trackSettings.mounttype == 'Eq':
                        satra = self.sat.ra
                        self.radra = self.sat.ra
                        self.raddec = self.sat.dec
                        self.rad_to_sexagesimal_ra()
                        targetcoordra = str(':Sr ' + str(self.ra_h)+'*'+str(self.ra_m)+':'+str(int(self.ra_s))+'#')
                        targetcoorddec = str(':Sd ' + str(self.dec_d)+'*'+str(self.dec_m)+':'+str(int(self.dec_s))+'#')
                        self.ser.write(str.encode(targetcoordra))
                        self.ser.write(str.encode(targetcoorddec))
                        self.ser.write(str.encode(':MS#'))
                        print(targetcoordra, targetcoorddec)
                        self.textbox.insert(END, str('RA: '+str(targetcoordra) + 'Dec: ' + str(targetcoorddec)+ '\n'))
                        self.textbox.see('end')
                    time.sleep(1)
                    #Do alt degrees twice to clear the buffer cause I'm too lazy to clear the buffer properly
                    self.LX200_alt_degrees()
                    self.LX200_alt_degrees()
                    currentalt = self.telalt
                    self.LX200_az_degrees()
                    currentaz = self.telaz
                    altdiff = math.degrees(self.radalt) - currentalt
                    azdiff = math.degrees(self.radaz) - currentaz
                    totaldiff = math.sqrt(altdiff**2 + azdiff**2)
                    self.lasttotaldiff = totaldiff
                    self.dlast = self.dnow
                    while totaldiff > 1:
                        self.LX200_alt_degrees()
                        self.LX200_alt_degrees()
                        currentalt = self.telalt
                        self.LX200_az_degrees()
                        currentaz = self.telaz
                        altdiff = math.degrees(self.radalt) - currentalt
                        azdiff = math.degrees(self.radaz) - currentaz
                        totaldiff = math.sqrt(altdiff**2 + azdiff**2)
                        time.sleep(1)
                firstslew = False
                if trackSettings.telescopetype == 'ASCOM':
                    self.dlast = self.dnow
                    d = datetime.datetime.utcnow()
                    self.observer.date = (d + datetime.timedelta(seconds=0))
                    self.sat.compute(self.observer)
                    if trackSettings.mounttype == 'AltAz' and trackSettings.trackingsat is True:
                        self.radalt = self.sat.alt
                        self.radaz = self.sat.az
                        self.observer.date = (d + datetime.timedelta(seconds=1))
                        self.sat.compute(self.observer)
                        self.radalt2 = self.sat.alt
                        self.radaz2 = self.sat.az
                        print(math.degrees(self.radaz), math.degrees(self.radalt))
                        self.textbox.insert(END, str('Target Az: '+str(self.radaz) + ' Target Alt: ' + str(self.radalt)+ '\n'))
                        self.textbox.see('end')
                        azrate = (math.degrees(self.radaz2 - self.radaz))
                        altrate = math.degrees(self.radalt2 - self.radalt)
                        #self.tel.Tracking = False
                        self.tel.SlewToAltAz(math.degrees(self.radaz2),math.degrees(self.radalt2))
                        print(azrate, altrate)
                        if azrate > self.axis0rate:
                            azrate = self.axis0rate
                        if azrate < (-1*self.axis0rate):
                            azrate = (-1*self.axis0rate)
                        if altrate > self.axis1rate:
                            altrate = self.axis1rate
                        if altrate < (-1*self.axis1rate):
                            altrate = (-1*self.axis1rate)
                        self.tel.MoveAxis(0, azrate)
                        self.tel.MoveAxis(1, altrate)
                    if trackSettings.mounttype == 'Eq' and trackSettings.trackingsat is True:
                        self.raddec = self.sat.dec
                        self.radra = self.sat.ra
                        self.observer.date = (d + datetime.timedelta(seconds=1))
                        self.sat.compute(self.observer)
                        self.raddec2 = self.sat.dec
                        self.radra2 = self.sat.ra
                        print(math.degrees(self.radra), math.degrees(self.raddec))
                        self.textbox.insert(END, str('Target RA: '+str(self.radra) + 'Target Dec: ' + str(self.raddec)+ '\n'))
                        self.textbox.see('end')
                        rarate = -1*(math.degrees(self.radra2 - self.radra))*math.cos(self.raddec2)
                        decrate = math.degrees(self.raddec2 - self.raddec)
                        #self.tel.Tracking = False
                        self.tel.SlewToCoordinates((math.degrees(self.radra2)/15),math.degrees(self.raddec2))
                        print(rarate, decrate)
                        if rarate > self.axis0rate:
                            rarate = self.axis0rate
                        if rarate < (-1*self.axis0rate):
                            rarate = (-1*self.axis0rate)
                        if decrate > self.axis1rate:
                            decrate = self.axis1rate
                        if decrate < (-1*self.axis1rate):
                            decrate = (-1*self.axis1rate)
                        self.tel.MoveAxis(0, rarate)
                        self.tel.MoveAxis(1, decrate)
                    time.sleep(0.001)                    
                firstslew = False
            if trackSettings.objectfollow is False:
                i = i + 1
                self.observer.date = datetime.datetime.utcnow()
                self.sat.compute(self.observer)
                self.radalt = self.sat.alt
                self.radaz = self.sat.az
                if trackSettings.telescopetype == 'ASCOM':
                    self.observer.date = datetime.datetime.utcnow()
                    d = datetime.datetime.utcnow()
                    self.sat.compute(self.observer)
                    if trackSettings.mounttype == 'AltAz' and trackSettings.trackingsat is True:
                        self.radalt = self.sat.alt
                        self.radaz = self.sat.az
                        currentaz = self.tel.Azimuth
                        currentalt = self.tel.Altitude
                        diffaz = math.degrees(self.radaz) - currentaz
                        diffalt = math.degrees(self.radalt) - currentalt
                        self.observer.date = (d + datetime.timedelta(seconds=1))
                        self.sat.compute(self.observer)
                        self.radalt2 = self.sat.alt
                        self.radaz2 = self.sat.az
                        trueazrate = (math.degrees(self.radaz2 - self.radaz))
                        truealtrate = math.degrees(self.radalt2 - self.radalt)
                        azrate = trueazrate+(diffaz*0.75)
                        altrate = truealtrate+(diffalt*0.75)
                        
                        print('diffaz, diffalt, azrate, altrate', diffaz, diffalt, azrate, altrate, end='\r')
                        self.textbox.insert(END, str('Delta Az: ' + str(diffaz) + ' Delta Alt: ' + str(diffalt) + '\n'))
                        self.textbox.see('end')
                        if azrate > self.axis0rate:
                            azrate = self.axis0rate
                        if azrate < (-1*self.axis0rate):
                            azrate = (-1*self.axis0rate)
                        if altrate > self.axis1rate:
                            altrate = self.axis1rate
                        if altrate < (-1*self.axis1rate):
                            altrate = (-1*self.axis1rate)
                        self.tel.MoveAxis(0, azrate)
                        self.tel.MoveAxis(1, altrate)
                        self.diffazlast = diffaz
                        self.diffaltlast = diffalt
                        altcorrect = 0
                        azcorrect = 0
                    if trackSettings.mounttype == 'Eq' and trackSettings.trackingsat is True:
                        self.raddec = self.sat.dec
                        self.radra = self.sat.ra
                        rahours = math.degrees(self.radra)/15
                        currentra = self.tel.RightAscension*15
                        currentrahours = currentra/15
                        directhours = self.tel.RightAscension
                        currentdec = self.tel.Declination
                        diffra = math.degrees(self.radra) - currentra
                        diffdec = math.degrees(self.raddec) - currentdec
                        self.observer.date = (d + datetime.timedelta(seconds=1))
                        self.sat.compute(self.observer)
                        self.raddec2 = self.sat.dec
                        self.radra2 = self.sat.ra
                        #rarate = (math.degrees(self.radra2 - self.radra))
                        #decrate = math.degrees(self.raddec2 - self.raddec)
                        
                        #print('Current az, current alt, azrate, altrate', currentaz, currentalt, azrate, altrate)
                        truerarate = -1*math.degrees(self.radra2 - self.radra)
                        truedecrate = math.degrees(self.raddec2 - self.raddec)
                        rarate = truerarate-(diffra*0.3)
                        decrate = truedecrate+(diffdec*0.3)
                        if rarate > self.axis0rate:
                            rarate = self.axis0rate
                        if rarate < (-1*self.axis0rate):
                            rarate = (-1*self.axis0rate)
                        if decrate > self.axis1rate:
                            decrate = self.axis1rate
                        if decrate < (-1*self.axis1rate):
                            decrate = (-1*self.axis1rate)
                        print('diffra, diffdec, rarate, decrate', diffra, diffdec, rarate, decrate, end='\r')
                        self.textbox.insert(END, str('Delta RA: ' + str(diffra) + ' Delta Dec: ' + str(diffdec) + '\n'))
                        self.textbox.see('end')
                        self.tel.MoveAxis(0, rarate)
                        self.tel.MoveAxis(1, decrate)
                        self.diffralast = diffra
                        self.diffdeclast = diffdec
                        deccorrect = 0
                        racorrect = 0
                    time.sleep(0.001)
                if trackSettings.telescopetype == 'LX200':
                    if trackSettings.mounttype == 'AltAz':
                        sataz = math.degrees(self.sat.az) + 180
                        if sataz > 360:
                            sataz = sataz - 360
                        sataz = math.radians(sataz)
                        self.radaz = sataz
                        if i > 100:
                            self.LX200_alt_degrees()
                            self.LX200_alt_degrees()
                            currentalt = math.radians(self.telalt)
                            self.LX200_az_degrees()
                            currentaz = math.radians(self.telaz)
                            altdiff = self.radalt - currentalt
                            azdiff = self.radaz - currentaz
                            altcorrect = altcorrect + (altdiff)
                            azcorrect = azcorrect + (azdiff)
                            totaldiff = math.sqrt(altdiff**2 + azdiff**2)
                            i = 0
                            print(math.degrees(totaldiff))
                            self.textbox.insert(END, str('Distance from target: ' + str(totaldiff) + '\n'))
                            self.textbox.see('end')
                            self.lasttotaldiff = totaldiff
                        
                        self.radaz = self.radaz + azcorrect
                        self.radalt = self.radalt + altcorrect
                        
                        self.rad_to_sexagesimal_alt()
                        targetcoordaz = str(':Sz ' + str(self.az_d)+'*'+str(self.az_m)+':'+str(int(self.az_s))+'#')
                        targetcoordalt = str(':Sa ' + str(self.alt_d)+'*'+str(self.alt_m)+':'+str(int(self.alt_s))+'#')
                        self.ser.write(str.encode(targetcoordaz))
                        self.ser.write(str.encode(targetcoordalt))
                        self.ser.write(str.encode(':MA#'))
                    if trackSettings.mounttype == 'Eq':
                        satra = self.sat.ra
                        self.radra = self.sat.ra
                        self.raddec = self.sat.dec
                        
                        self.LX200_dec_degrees()
                        self.LX200_dec_degrees()
                        currentdec = math.radians(self.teldec)
                        self.LX200_ra_degrees()
                        currentra = math.radians(self.telra)
                        decdiff = self.raddec - currentdec
                        radiff = self.radra - currentra
                        totaldiff = math.sqrt(decdiff**2 + radiff**2)
                        i = 0
                        print(math.degrees(totaldiff))
                        self.textbox.insert(END, str('Distance from target: ' + str(totaldiff) + '\n'))
                        self.textbox.see('end')
                        if self.lasttotaldiff < totaldiff:
                            deccorrect = deccorrect + (decdiff)
                            racorrect = racorrect + (radiff)
                        self.lasttotaldiff = totaldiff
                        
                        self.radra = self.radra + racorrect
                        self.raddec = self.raddec + deccorrect
                        
                        self.rad_to_sexagesimal_ra()
                        targetcoordra = str(':Sr ' + str(self.ra_h)+'*'+str(self.ra_m)+':'+str(int(self.ra_s))+'#')
                        targetcoorddec = str(':Sd ' + str(self.dec_d)+'*'+str(self.dec_m)+':'+str(int(self.dec_s))+'#')
                        self.ser.write(str.encode(targetcoordra))
                        self.ser.write(str.encode(targetcoorddec))
                        self.ser.write(str.encode(':MS#'))
                        print(targetcoordra, targetcoorddec)
                        
            if trackSettings.objectfollow is True:
                self.observer.date = datetime.datetime.utcnow()
                self.sat.compute(self.observer)
                self.radalt = self.sat.alt
                self.radaz = self.sat.az 
                self.raddec = self.sat.dec
                self.radra = self.sat.ra
                
                if trackSettings.telescopetype == 'ASCOM':
                    time.sleep(0.1)
                    self.observer.date = datetime.datetime.utcnow()
                    d = datetime.datetime.utcnow()
                    self.sat.compute(self.observer)
                    if trackSettings.mounttype == 'AltAz' and trackSettings.trackingsat is True:
                        self.radalt = self.sat.alt
                        self.radaz = self.sat.az
                        currentaz = self.tel.Azimuth
                        currentalt = self.tel.Altitude
                        currentaltdegrees = currentalt
                        if self.dnow > self.dlast:
                            currentalt = math.radians(currentalt)
                            currentaz = math.radians(currentaz)
                            objectvertical = -1 * ((self.targetY - trackSettings.mainviewY) * trackSettings.imagescale)
                            objecthorizontal = (self.targetX - trackSettings.mainviewX) * trackSettings.imagescale
                            objectangle = math.degrees(math.atan2(objectvertical, objecthorizontal)) - 90
                            objectangle2 = math.degrees(math.atan2(objectvertical, objecthorizontal))
                            objectdistance = math.sqrt((objecthorizontal**2) + (objectvertical**2) - 2 * (objectvertical * objecthorizontal * math.cos(math.radians(objectangle))))
                            try:
                                objectalt = 90 - math.degrees(math.acos(math.cos(math.radians(objectdistance)) * math.cos(math.radians(90 - currentaltdegrees)) + math.sin(math.radians(objectdistance)) * math.sin(math.radians(90 - currentaltdegrees)) * math.cos(math.radians(objectangle))))
                                diffinaz = math.degrees(math.acos((math.cos(math.radians(objectdistance)) - math.cos(math.radians(90 - currentaltdegrees)) * math.cos(math.radians(90 - objectalt))) / (math.sin(math.radians(90 - currentaltdegrees)) * math.sin(math.radians(90 - objectalt)))))
                                if math.fabs(objectangle2) > 90:
                                    diffinaz = -1 * diffinaz
                                altdiff = math.degrees(math.radians(objectalt) - currentalt)
                                azdiff = diffinaz
                                totaldiff = math.sqrt(altdiff**2 + azdiff**2)
                                self.observer.date = (d + datetime.timedelta(seconds=1))
                                self.sat.compute(self.observer)
                                self.radalt2 = self.sat.alt
                                self.radaz2 = self.sat.az
                                azrate = (math.degrees(self.radaz2 - self.radaz))
                                altrate = math.degrees(self.radalt2 - self.radalt)
                                #if math.fabs(self.diffazlast) < math.fabs(azdiff):
                                azrate = azrate + azdiff
                                #if math.fabs(self.diffaltlast) < math.fabs(altdiff):
                                altrate = altrate + altdiff
                                if azrate > self.axis0rate:
                                    azrate = self.axis0rate
                                if azrate < (-1*self.axis0rate):
                                    azrate = (-1*self.axis0rate)
                                if altrate > self.axis1rate:
                                    altrate = self.axis1rate
                                if altrate < (-1*self.axis1rate):
                                    altrate = (-1*self.axis1rate)
                                print('azdiff, altdiff, azrate, altrate', azdiff, altdiff, azrate, altrate, end='\r')
                                self.textbox.insert(END, str('Delta Az: ' + str(azdiff) + ' Delta Alt: ' + str(altdiff) + '\n'))
                                self.textbox.see('end')
                                self.tel.MoveAxis(0, azrate)
                                self.tel.MoveAxis(1, altrate)
                                self.diffazlast = azdiff
                                self.diffallast = altdiff
                            except:
                                print('Failed to do the math.')
                    if trackSettings.mounttype == 'Eq' and trackSettings.trackingsat is True:
                        self.raddec = self.sat.dec
                        self.radra = self.sat.ra
                        currentra = float(self.tel.RightAscension)*15
                        currentdec = self.tel.Declination
                        currentdecdegrees = currentdec
                        if self.dnow > self.dlast:
                            currentdec = math.radians(currentdec)
                            currentra = math.radians(currentra)
                            objectvertical = -1 * ((self.targetY - trackSettings.mainviewY) * trackSettings.imagescale)
                            objecthorizontal = (self.targetX - trackSettings.mainviewX) * trackSettings.imagescale
                            objectangle = math.degrees(math.atan2(objectvertical, objecthorizontal)) - 90
                            objectangle2 = math.degrees(math.atan2(objectvertical, objecthorizontal))
                            objectdistance = math.sqrt((objecthorizontal**2) + (objectvertical**2) - 2 * (objectvertical * objecthorizontal * math.cos(math.radians(objectangle))))
                            try:
                                objectdec = 90 - math.degrees(math.acos(math.cos(math.radians(objectdistance)) * math.cos(math.radians(90 - currentdecdegrees)) + math.sin(math.radians(objectdistance)) * math.sin(math.radians(90 - currentdecdegrees)) * math.cos(math.radians(objectangle))))
                                diffinra = math.degrees(math.acos((math.cos(math.radians(objectdistance)) - math.cos(math.radians(90 - currentdecdegrees)) * math.cos(math.radians(90 - objectdec))) / (math.sin(math.radians(90 - currentdecdegrees)) * math.sin(math.radians(90 - objectdec)))))
                                if math.fabs(objectangle2) > 90:
                                    diffinra = -1 * diffinra
                                decdiff = math.radians(objectdec) - currentdec
                                radiff = math.radians(diffinra)
                                totaldiff = math.sqrt(decdiff**2 + radiff**2)
                                self.observer.date = (d + datetime.timedelta(seconds=1))
                                self.sat.compute(self.observer)
                                self.raddec2 = self.sat.dec
                                self.radra2 = self.sat.ra
                                rarate = (math.degrees(self.radra2 - self.radra))
                                decrate = math.degrees(self.raddec2 - self.raddec)
                                #if math.fabs(self.diffralast) < math.fabs(radiff):
                                rarate = rarate + math.degrees(radiff)
                                #if math.fabs(self.diffdeclast) < math.fabs(decdiff):
                                decrate = decrate + math.degrees(decdiff)
                                if rarate > self.axis0rate:
                                    rarate = self.axis0rate
                                if rarate < (-1*self.axis0rate):
                                    rarate = (-1*self.axis0rate)
                                if decrate > self.axis1rate:
                                    decrate = self.axis1rate
                                if decrate < (-1*self.axis1rate):
                                    decrate = (-1*self.axis1rate)
                                self.tel.MoveAxis(0, rarate)
                                self.tel.MoveAxis(1, decrate)
                                self.diffralast = radiff
                                self.diffdeclast = decdiff
                            except:
                                print('Failed to do the math.')
                if trackSettings.telescopetype == 'LX200':
                    if trackSettings.mounttype == 'AltAz':
                        sataz = math.degrees(self.sat.az) + 180
                        if sataz > 360:
                            sataz = sataz - 360
                        sataz = math.radians(sataz)
                        self.radaz = sataz
                        #check if it's time to correct and that we have a newer frame than last time
                        if self.dnow > self.dlast:
                            self.LX200_alt_degrees()
                            self.LX200_alt_degrees()
                            currentalt = math.radians(self.telalt)
                            self.LX200_az_degrees()
                            currentaz = math.radians(self.telaz)
                            objectvertical = -1 * ((self.targetY - trackSettings.mainviewY) * trackSettings.imagescale)
                            objecthorizontal = (self.targetX - trackSettings.mainviewX) * trackSettings.imagescale
                            objectangle = math.degrees(math.atan2(objectvertical, objecthorizontal)) - 90
                            objectangle2 = math.degrees(math.atan2(objectvertical, objecthorizontal))
                            objectdistance = math.sqrt((objecthorizontal**2) + (objectvertical**2) - 2 * (objectvertical * objecthorizontal * math.cos(math.radians(objectangle))))
                            try:
                                objectalt = 90 - math.degrees(math.acos(math.cos(math.radians(objectdistance)) * math.cos(math.radians(90 - self.telalt)) + math.sin(math.radians(objectdistance)) * math.sin(math.radians(90 - self.telalt)) * math.cos(math.radians(objectangle))))
                                diffinaz = math.degrees(math.acos((math.cos(math.radians(objectdistance)) - math.cos(math.radians(90 - self.telalt)) * math.cos(math.radians(90 - objectalt))) / (math.sin(math.radians(90 - self.telalt)) * math.sin(math.radians(90 - objectalt)))))
                                if math.fabs(objectangle2) > 90:
                                    diffinaz = -1 * diffinaz
                                altdiff = math.radians(objectalt) - currentalt
                                azdiff = math.radians(diffinaz)
                                totaldiff = math.sqrt(altdiff**2 + azdiff**2)
                                #if total dist to target is increasing since last frame we need to correct!
                                if self.lasttotaldiff < totaldiff:
                                    altcorrect = altcorrect + (altdiff)
                                    azcorrect = azcorrect + (azdiff)
                                print(math.degrees(totaldiff))
                                self.textbox.insert(END, str('Distance from target: ' + str(totaldiff) + '\n'))
                                self.textbox.see('end')
                                self.lasttotaldiff = totaldiff
                            except:
                                print('Failed to do the math.')
                            #print(math.degrees(altcorrect), math.degrees(azcorrect), math.degrees(altdiff), math.degrees(azdiff), math.degrees(currentalt), math.degrees(currentaz))
                        self.dlast = self.dnow
                        self.radaz = self.radaz + azcorrect
                        self.radalt = self.radalt + altcorrect
                        
                        self.rad_to_sexagesimal_alt()
                        targetcoordaz = str(':Sz ' + str(self.az_d)+'*'+str(self.az_m)+':'+str(int(self.az_s))+'#')
                        targetcoordalt = str(':Sa ' + str(self.alt_d)+'*'+str(self.alt_m)+':'+str(int(self.alt_s))+'#')
                        self.ser.write(str.encode(targetcoordaz))
                        self.ser.write(str.encode(targetcoordalt))
                        self.ser.write(str.encode(':MA#'))
                    if trackSettings.mounttype == 'EQ':
                        self.raddec = self.sat.dec
                        self.radra = self.sat.ra 
                        #check if it's time to correct and that we have a newer frame than last time
                        if self.dnow > self.dlast:
                            self.LX200_dec_degrees()
                            self.LX200_dec_degrees()
                            currentdec = math.radians(self.teldec)
                            self.LX200_ra_degrees()
                            currentra = math.radians(self.telra)
                            objectvertical = -1 * ((self.targetY - trackSettings.mainviewY) * trackSettings.imagescale)
                            objecthorizontal = (self.targetX - trackSettings.mainviewX) * trackSettings.imagescale
                            objectangle = math.degrees(math.atan2(objectvertical, objecthorizontal)) - 90
                            objectangle2 = math.degrees(math.atan2(objectvertical, objecthorizontal))
                            objectdistance = math.sqrt((objecthorizontal**2) + (objectvertical**2) - 2 * (objectvertical * objecthorizontal * math.cos(math.radians(objectangle))))
                            try:
                                objectalt = 90 - math.degrees(math.acos(math.cos(math.radians(objectdistance)) * math.cos(math.radians(90 - self.teldec)) + math.sin(math.radians(objectdistance)) * math.sin(math.radians(90 - self.teldec)) * math.cos(math.radians(objectangle))))
                                diffinaz = math.degrees(math.acos((math.cos(math.radians(objectdistance)) - math.cos(math.radians(90 - self.teldec)) * math.cos(math.radians(90 - objectalt))) / (math.sin(math.radians(90 - self.teldec)) * math.sin(math.radians(90 - objectalt)))))
                                if math.fabs(objectangle2) > 90:
                                    diffinra = -1 * diffinra
                                decdiff = math.radians(objectdec) - currentdec
                                radiff = math.radians(diffinra)
                                totaldiff = math.sqrt(decdiff**2 + radiff**2)
                                #if total dist to target is increasing since last frame we need to correct!
                                if self.lasttotaldiff < totaldiff:
                                    deccorrect = deccorrect + (decdiff)
                                    racorrect = racorrect + (radiff)
                                print(math.degrees(totaldiff))
                                self.textbox.insert(END, str('Distance from Target: ' + str(totaldiff) + '\n'))
                                self.textbox.see('end')
                                self.lasttotaldiff = totaldiff
                            except:
                                print('Failed to do the math.')
                            #print(math.degrees(altcorrect), math.degrees(azcorrect), math.degrees(altdiff), math.degrees(azdiff), math.degrees(currentalt), math.degrees(currentaz))
                        self.dlast = self.dnow
                        self.radra = self.radra + racorrect
                        self.raddec = self.raddec + deccorrect
                        
                        self.rad_to_sexagesimal_ra()
                        targetcoordra = str(':Sr ' + str(self.ra_h)+'*'+str(self.ra_m)+':'+str(int(self.ra_s))+'#')
                        targetcoorddec = str(':Sd ' + str(self.dec_d)+'*'+str(self.dec_m)+':'+str(int(self.dec_s))+'#')
                        self.ser.write(str.encode(targetcoordra))
                        self.ser.write(str.encode(targetcoorddec))
                        self.ser.write(str.encode(':MS#'))
            time.sleep(0.005)
        #stop moving the telescope if the user is on ASCOM and requested stop tracking.
        if trackSettings.telescopetype == 'ASCOM' and trackSettings.trackingsat is False:
            self.tel.AbortSlew()
    
    def set_center(self):
        trackSettings.setcenter = True
    
    def setLX200AltAz(self):
        trackSettings.telescopetype = 'LX200'
        trackSettings.mounttype = 'AltAz'
        
    def setLX200Eq(self):
        trackSettings.telescopetype = 'LX200'
        trackSettings.mounttype = 'Eq'
    
    def setFeatureTrack(self):
        trackSettings.trackingtype = 'Features'
    
    def setBrightTrack(self):
        trackSettings.trackingtype = 'Bright'    
        
    def setASCOMAltAz(self):
        trackSettings.telescopetype = 'ASCOM'
        trackSettings.mounttype = 'AltAz'
    
    def setASCOMEq(self):
        trackSettings.telescopetype = 'ASCOM'
        trackSettings.mounttype = 'Eq'
    
    def set_img_collect(self):
        if self.collect_images is False:
            self.collect_images = True
            print('Starting Camera.')
            self.textbox.insert(END, 'Starting Camera.\n')
            self.textbox.see('end')
            self.cap = cv2.VideoCapture(int(self.entryCam.get()))
            self.displayimg = Label(self.topframe, bg="black")
            self.startButton.configure(text='Stop Camera')
            imagethread = threading.Thread(target=self.prepare_img_for_tkinter)
            imagethread.start()
        else:
            self.cap.release()
            self.collect_images = False
            self.startButton.configure(text='Start Camera')
    
    def read_to_hash(self):
        self.resp = self.ser.read()
        self.resp = self.resp.decode("utf-8", errors="ignore")
        try:
            while self.resp[-1] != '#':
                self.resp += self.ser.read().decode("utf-8", errors="ignore")
        except:
            print('Unable to read line')
            self.textbox.insert(END, 'Unable to read line.\n')
            self.textbox.see('end')
        #print(self.resp)
        if trackSettings.degorhours == 'Degrees':
            self.deg = int(self.resp[0:3])
            self.min = int(self.resp[3:5])
            self.sec = int(self.resp[6:8])
            self.respdegrees = ((((self.sec/60)+self.min)/60)+self.deg)
            #print(self.resp, self.respdegrees)
        if trackSettings.degorhours == 'Hours':
            self.hr = int(self.resp[0:2])
            self.min = int(self.resp[3:5])
            self.sec = int(self.resp[6:8])
            self.resphours = ((((self.sec/60)+self.min)/60)+self.hr)*15
        return
    
    def set_tracking(self):
        if trackSettings.tracking is False:
            trackSettings.tracking = True
            print('Connecting to Scope.')
            self.textbox.insert(END, 'Connecting to Scope.\n')
            self.textbox.see('end')
            if trackSettings.telescopetype == 'LX200':
                try:
                    self.comport = str('COM'+str(self.entryCom.get()))
                    self.ser = serial.Serial(self.comport, baudrate=9600, timeout=1, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, xonxoff=False, rtscts=False)
                    self.ser.write(str.encode(':U#'))
                    self.serialconnected = True
                    self.startButton5.configure(text='Disconnect Scope')
                except:
                    print('Failed to connect on ' + self.comport)
                    self.textbox.insert(END, str('Failed to connect on ' + str(self.comport) + '\n'))
                    self.textbox.see('end')
                    trackSettings.tracking = False
                    return
            elif trackSettings.telescopetype == 'ASCOM':
                self.x = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
                self.x.DeviceType = 'Telescope'
                driverName=self.x.Choose("None")
                self.tel=win32com.client.Dispatch(driverName)
                if self.tel.Connected:
                    print("Telescope was already connected")
                    self.textbox.insert(END, str('Telescope was already connected.\n'))
                    self.textbox.see('end')
                    self.startButton5.configure(text='Disconnect Scope')
                else:
                    self.tel.Connected = True
                    if self.tel.Connected:
                        print("Connected to telescope now")
                        self.textbox.insert(END, str('Connected to telescope now.\n'))
                        self.textbox.see('end')
                        axis = self.tel.CanMoveAxis(0)
                        axis2 = self.tel.CanMoveAxis(1)
                        if axis is False or axis2 is False:
                            print('This scope cannot use the MoveAxis method, aborting.')
                            self.textbox.insert(END, str('This scope cannot use the MoveAxis method, aborting.\n'))
                            self.textbox.see('end')
                            self.tel.Connected = False
                        else:
                            self.axis0rate = float(self.tel.AxisRates(0).Item(1).Maximum)
                            self.axis1rate = float(self.tel.AxisRates(1).Item(1).Maximum)
                            print(self.axis0rate)
                            print(self.axis1rate)
                            self.textbox.insert(END, str('Axis 0 max rate: '+str(self.axis0rate)+' Axis 1 max rate: '+ str(self.axis1rate)+'\n'))
                            self.textbox.see('end')
                            self.startButton5.configure(text='Disconnect Scope')
                    else:
                        print("Unable to connect to telescope, expect exception")
                        self.textbox.insert(END, str('Unable to connect to telescope, expect exception.\n'))
                        self.textbox.see('end')
        else:
            print('Disconnecting the Scope.')
            self.textbox.insert(END, str('Disconnecting the scope.\n'))
            self.textbox.see('end')
            if trackSettings.telescopetype == 'LX200' and self.serialconnected is True:
                self.ser.write(str.encode(':Q#'))
                self.ser.write(str.encode(':U#'))
                self.ser.close()
                self.serialconnected = False
            elif trackSettings.telescopetype == 'ASCOM':
                self.tel.AbortSlew()
                self.tel.Connected = False
            trackSettings.tracking = False
            self.startButton5.configure(text='Connect Scope')
    
    def rad_to_sexagesimal_alt(self):
        self.azdeg = math.degrees(self.radaz)
        self.altdeg = math.degrees(self.radalt)
        self.az_d = math.trunc((self.azdeg))
        self.az_m = math.trunc((((self.azdeg)) - self.az_d)*60)
        self.az_s = (((((self.azdeg)) - self.az_d)*60) - self.az_m)*60
        
        self.alt_d = math.trunc(self.altdeg)
        self.alt_m = math.trunc((abs(self.altdeg) - abs(self.alt_d))*60)
        self.alt_s = (((abs(self.altdeg) - abs(self.alt_d))*60) - abs(self.alt_m))*60
    
    def rad_to_sexagesimal_ra(self):
        self.rahour = math.degrees(self.radra)/15
        self.decdeg = math.degrees(self.raddec)
        self.ra_h = math.trunc((self.rahour))
        self.ra_m = math.trunc((((self.rahour)) - self.ra_h)*60)
        self.ra_s = (((((self.rahour)) - self.ra_h)*60) - self.ra_m)*60
        
        self.dec_d = math.trunc(self.decdeg)
        self.dec_m = math.trunc((abs(self.decdeg) - abs(self.dec_d))*60)
        self.dec_s = (((abs(self.decdeg) - abs(self.dec_d))*60) - abs(self.dec_m))*60
    
    def start_calibration(self):
        calibthread = threading.Thread(target=self.set_calibration)
        calibthread.start()
    
    def set_calibration(self):
        if trackSettings.calibratestart is False:
            trackSettings.calibratestart = True
        else:
            self.tel.MoveAxis(1, 0.0)
            #self.tel.AbortSlew()
            trackSettings.calibratestart = False
        if trackSettings.tracking is False:
            print('Connect the Scope First!')
            self.textbox.insert(END, str('Connect the Scope First!\n'))
            self.textbox.see('end')
        if self.collect_images is False:
            print('Start Camera First!')
            self.textbox.insert(END, str('Start Camera First!\n'))
            self.textbox.see('end')
        if trackSettings.objectfollow is False:
            print('Pick a stationary calibration object first!')
            self.textbox.insert(END, str('Pick a stationary target first!\n'))
            self.textbox.see('end')
        if trackSettings.tracking is True and self.collect_images is True and trackSettings.objectfollow is True and trackSettings.calibratestart is True:
            if trackSettings.telescopetype == 'ASCOM':
                if trackSettings.mounttype == 'AltAz':
                    self.X1 = math.radians(self.tel.Azimuth)
                    self.Y1 = math.radians(self.tel.Altitude)
                    startx = self.targetX
                    starty = self.targetY
                    if starty < (self.height/2):
                        distmoved = 0
                        self.tel.MoveAxis(1, 0.1)
                        while distmoved < 100 and trackSettings.calibratestart is True:
                            self.tel.MoveAxis(1, 0.1)
                            currentx = self.targetX
                            currenty = self.targetY
                            distmoved = math.sqrt((startx-currentx)**2+(starty-currenty)**2)
                            time.sleep(0.01)
                        self.tel.MoveAxis(1, 0.0)
                        #self.tel.AbortSlew()
                        self.X2 = math.radians(self.tel.Azimuth)
                        self.Y2 = math.radians(self.tel.Altitude)
                        self.separation_between_coordinates()
                        self.imagescale = self.separation/distmoved
                        print(self.imagescale, ' degrees per pixel.')
                        self.textbox.insert(END, str('Image scale: '+str(self.imagescale)+' degrees per pixel.\n'))
                        self.textbox.see('end')
                    else:
                        distmoved = 0
                        self.tel.MoveAxis(1, -0.1)
                        while distmoved < 100 and trackSettings.calibratestart is True:
                            self.tel.MoveAxis(1, -0.1)
                            currentx = self.targetX
                            currenty = self.targetY
                            distmoved = math.sqrt((startx-currentx)**2+(starty-currenty)**2)
                            time.sleep(0.01)
                        self.tel.MoveAxis(1, 0.0)
                        #self.tel.AbortSlew()
                        self.X2 = math.radians(self.tel.Azimuth)
                        self.Y2 = math.radians(self.tel.Altitude)
                        self.separation_between_coordinates()
                        self.imagescale = self.separation/distmoved
                        print(self.imagescale, ' degrees per pixel.')
                        self.textbox.insert(END, str('Image scale: '+str(self.imagescale)+' degrees per pixel.\n'))
                        self.textbox.see('end')
                if trackSettings.mounttype == 'Eq':
                    self.X1 = math.radians(float(self.tel.RightAscension)*15)
                    self.Y1 = math.radians(float(self.tel.Declination))
                    startx = self.targetX
                    starty = self.targetY
                    if starty < (self.height/2):
                        distmoved = 0
                        self.tel.MoveAxis(1, 0.1)
                        while distmoved < 100 and trackSettings.calibratestart is True:
                            self.tel.MoveAxis(1, 0.1)
                            currentx = self.targetX
                            currenty = self.targetY
                            distmoved = math.sqrt((startx-currentx)**2+(starty-currenty)**2)
                            time.sleep(0.01)
                        self.tel.MoveAxis(1, 0.0)
                        #self.tel.AbortSlew()
                        self.X2 = math.radians(self.tel.RightAscension*15)
                        self.Y2 = math.radians(self.tel.Declination)
                        self.separation_between_coordinates()
                        #print('x1 ', self.X1, 'y1 ', self.Y1, 'separation ', self.separation, 'distance moved ', distmoved)
                        self.imagescale = self.separation/distmoved
                        print(self.imagescale, ' degrees per pixel.')
                        self.textbox.insert(END, str('Image scale: '+str(self.imagescale)+' degrees per pixel.\n'))
                        self.textbox.see('end')
                    else:
                        distmoved = 0
                        self.tel.MoveAxis(1, -0.1)
                        while distmoved < 100 and trackSettings.calibratestart is True:
                            self.tel.MoveAxis(1, -0.1)
                            currentx = self.targetX
                            currenty = self.targetY
                            distmoved = math.sqrt((startx-currentx)**2+(starty-currenty)**2)
                            time.sleep(0.01)
                        self.tel.MoveAxis(1, 0.0)
                        #self.tel.AbortSlew()
                        self.X2 = math.radians(self.tel.RightAscension*15)
                        self.Y2 = math.radians(self.tel.Declination)
                        self.separation_between_coordinates()
                        #print('x1 ', self.X1, 'y1 ', self.Y1, 'separation ', self.separation, 'distance moved ', distmoved)
                        self.imagescale = self.separation/distmoved
                        print(self.imagescale, ' degrees per pixel.')
                        self.textbox.insert(END, str('Image scale: '+str(self.imagescale)+' degrees per pixel.\n'))
                        self.textbox.see('end')
                trackSettings.imagescale = self.imagescale            
            if trackSettings.telescopetype == 'LX200':
                self.LX200_az_degrees()
                self.X1 = math.radians(self.respdegrees)
                self.LX200_alt_degrees()
                self.Y1 = math.radians(self.respdegrees)
                startx = self.targetX
                starty = self.targetY
                
                if starty < (self.height/2):
                    distmoved = 0
                    self.ser.write(str.encode(':RC#'))
                    while distmoved < 100:
                        self.ser.write(str.encode(':Mn#'))
                        currentx = self.targetX
                        currenty = self.targetY
                        distmoved = math.sqrt((startx-currentx)**2+(starty-currenty)**2)
                        time.sleep(0.01)
                    self.ser.write(str.encode(':Qn#'))
                    self.LX200_az_degrees()
                    self.X2 = math.radians(self.respdegrees)
                    self.LX200_alt_degrees()
                    self.Y2 = math.radians(self.respdegrees)
                    self.separation_between_coordinates()
                    self.imagescale = self.separation/distmoved
                    print(self.imagescale, ' degrees per pixel.')
                    self.textbox.insert(END, str('Image scale: '+str(self.imagescale)+' degrees per pixel.\n'))
                    self.textbox.see('end')
                else:
                    distmoved = 0
                    self.ser.write(str.encode(':RC#'))
                    while distmoved < 100:
                        self.ser.write(str.encode(':Ms#'))
                        currentx = self.targetX
                        currenty = self.targetY
                        distmoved = math.sqrt((startx-currentx)**2+(starty-currenty)**2)
                        time.sleep(0.01)
                    self.ser.write(str.encode(':Qs#'))
                    self.LX200_az_degrees()
                    self.X2 = math.radians(self.respdegrees)
                    self.LX200_alt_degrees()
                    self.Y2 = math.radians(self.respdegrees)
                    self.separation_between_coordinates()
                    self.imagescale = self.separation/distmoved
                    print(self.imagescale, ' degrees per pixel.')
                    self.textbox.insert(END, str('Image scale: '+str(self.imagescale)+' degrees per pixel.\n'))
                    self.textbox.see('end')
                trackSettings.imagescale = self.imagescale
            trackSettings.calibratestart = False    
    
    def separation_between_coordinates(self):
        self.separation = math.degrees(math.acos(math.sin(self.Y1)*math.sin(self.Y2) + math.cos(self.Y1)*math.cos(self.Y2)*math.cos(self.X1-self.X2)))


    def LX200_alt_degrees(self):
        self.ser.write(str.encode(':GA#'))
        bytesToRead = self.ser.inWaiting()
        while bytesToRead == 0:
            bytesToRead = self.ser.inWaiting()
        #print('Receiving Altitude')
        trackSettings.degorhours = 'Degrees'
        self.read_to_hash()
        self.telalt = self.respdegrees
    
    def LX200_dec_degrees(self):
        self.ser.write(str.encode(':GD#'))
        bytesToRead = self.ser.inWaiting()
        while bytesToRead == 0:
            bytesToRead = self.ser.inWaiting()
        #print('Receiving Altitude')
        trackSettings.degorhours = 'Degrees'
        self.read_to_hash()
        self.teldec = self.respdegrees

    def LX200_az_degrees(self):
        self.ser.write(str.encode(':GZ#'))
        bytesToRead = self.ser.inWaiting()
        while bytesToRead == 0:
            bytesToRead = self.ser.inWaiting()
        #print('Receiving Azimuth')
        trackSettings.degorhours = 'Degrees'
        self.read_to_hash()
        self.telaz = self.respdegrees

    def LX200_ra_degrees(self):
        self.ser.write(str.encode(':GR#'))
        bytesToRead = self.ser.inWaiting()
        while bytesToRead == 0:
            bytesToRead = self.ser.inWaiting()
        #print('Receiving Righ Ascension')
        trackSettings.degorhours = 'Hours'
        self.read_to_hash()
        self.telra = float(self.resphours)*15
        #print(self.resphours)
    
    def _on_mousewheel(self, event):
        trackSettings.boxSize = trackSettings.boxSize + (event.delta/24)
        if trackSettings.boxSize < 5:
            trackSettings.boxSize = 5
        print(trackSettings.boxSize)
        self.textbox.insert(END, str('Tracking box size: '+str(trackSettings.boxSize)+'\n'))
        self.textbox.see('end')
    
    def mouse_position(self, event):
        trackSettings.mousecoords = (event.x, event.y)
    
    def left_click(self, event):
        if trackSettings.setcenter is True:
            trackSettings.mainviewX = trackSettings.mousecoords[0]
            trackSettings.mainviewY = trackSettings.mousecoords[1]
            trackSettings.setcenter = False
        else:
            self.trackimg = Label(self.topframe, bg="black")
            self.imgtk = self.img.copy()
            self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            #Set up a CLAHE histogram equalization for contrast enhancement of tracked feature
            if trackSettings.trackingtype == 'Features':
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(2,2))
                self.img = clahe.apply(self.img)
            self.imageroi = self.img[self.mousebox[0][1]:self.mousebox[1][1],self.mousebox[0][0]:self.mousebox[1][0]]
            #self.imageroi = cv2.cvtColor(self.imageroi, cv2.COLOR_BGR2GRAY)
            self.roibox = self.mousebox
            self.roiboxlast = self.roibox
            self.dnow = datetime.datetime.now()
            #self.dlast = self.dnow - datetime.timedelta(seconds=0.01)
            #find brightness of the clicked pixel and use the median between that and the brightest pixel in the ROI as the threshhold cutoff for brightness
            trackSettings.clickpixel = self.img[trackSettings.mousecoords[1],trackSettings.mousecoords[0]]
            roiheight, roiwidth = self.imageroi.shape[:2]
            blurred = cv2.GaussianBlur(self.imageroi.copy(), (5, 5), 0)
            pixellast = 0
            for y in range(0,roiheight):
                for x in range(0,roiwidth):
                    pixel = blurred[y,x]
                    if pixel > pixellast:
                        pixellast = pixel
            trackSettings.minbright = ((pixellast - trackSettings.clickpixel)/2)+trackSettings.clickpixel
            #self.entryBright.delete(0, END)
            #self.entryBright.insert(0, trackSettings.minbright)
            
            trackSettings.objectfollow = True
    
    def right_click(self, event):
        trackSettings.objectfollow = False
        self.roibox = []
        self.roiboxlast = []
        self.imageroi = []
    
    def goup(self, event):
        trackSettings.mainviewY -= 1
    
    def godown(self, event):
        trackSettings.mainviewY += 1
        
    def goleft(self, event):
        trackSettings.mainviewX -= 1
    
    def goright(self, event):
        trackSettings.mainviewX +=1
    
    def prepare_img_for_tkinter(self):
        if self.collect_images is True:
            self.imgtk = []
            self.img = []
            ret, self.img = self.cap.read()
            if ret is True:
                if trackSettings.flip == 'VerticalFlip':
                    self.img = cv2.flip(self.img, 0)
                if trackSettings.flip == 'HorizontalFlip':
                    self.img = cv2.flip(self.img, 1)
                if trackSettings.flip == 'VerticalHorizontalFlip':
                    self.img = cv2.flip(self.img, -1)
                self.img = imutils.rotate(self.img, trackSettings.rotate)
                #remember current time of the frame
                self.dnow = datetime.datetime.now()
                self.height, self.width = self.img.shape[:2]
                self.displayimg.bind("<MouseWheel>", self._on_mousewheel)
                self.displayimg.bind("<Motion>", self.mouse_position)
                self.displayimg.bind("<Button-1>", self.left_click)
                self.displayimg.bind("<Button-3>", self.right_click)
                self.mousebox = [(int(trackSettings.mousecoords[0]-(trackSettings.boxSize/2)),int(trackSettings.mousecoords[1]-(trackSettings.boxSize/2))),
                    (int(trackSettings.mousecoords[0]+(trackSettings.boxSize/2)),int(trackSettings.mousecoords[1]+(trackSettings.boxSize/2)))]
                self.centerbox = [(int(trackSettings.mainviewX-5),int(trackSettings.mainviewY - 5)),
                    (int(trackSettings.mainviewX+5),int(trackSettings.mainviewY+5))]
#make sure mouse coordinates are within bounds
                for idx, coord in enumerate(self.mousebox):
                    if coord[0] < 0:
                        x = 0
                    elif coord[0] > self.width:
                        x = self.width
                    else:
                        x = coord[0]
                    if coord[1] < 0:
                        y = 0
                    elif coord[1] > self.height:
                        y = self.height
                    else:
                        y = coord[1]
                    self.mousebox[idx] = (x,y)
                self.imgtk = self.img.copy()
                cv2.rectangle(self.imgtk,self.mousebox[0],self.mousebox[1],(255,0,0),2)
                cv2.rectangle(self.imgtk,self.centerbox[0],self.centerbox[1],(0,0,255),1)
                if trackSettings.objectfollow is True:
                    #trackSettings.minbright = self.entryBright.get()
                    self.roibox, self.imageroi = videotrak.get_x_y(self.img, self.roibox, self.imageroi)
                    #now check how much it's moved and calculate velocity.
                    self.xmotion = self.roibox[0][0] - self.roiboxlast[0][0]
                    self.ymotion = self.roibox[0][1] - self.roiboxlast[0][1]
                    #self.timedelta = self.dnow - self.dlast
                    #xpixelspersecond = self.xmotion/self.timedelta.total_seconds()
                    #ypixelspersecond = self.ymotion/self.timedelta.total_seconds()
                    #print(int(xpixelspersecond), ' pixels per second in X.', int(-1*ypixelspersecond), ' pixels per second in Y.', end='\r')
                    
                    self.roiboxlast = self.roibox
                    #self.dlast = self.dnow
                    cv2.rectangle(self.imgtk,self.roibox[0],self.roibox[1],(0,255,0),2)
                    self.roiheight, self.roiwidth = self.imageroi.shape[:2]
                    self.targetX = self.roibox[0][0]+(self.roiwidth/2)
                    self.targetY = self.roibox[0][1]+(self.roiheight/2)

                    self.tracktkimg = PILImage.fromarray(self.imageroi)
                    self.tracktkimg = ImageTk.PhotoImage(image=self.tracktkimg)
                    self.trackimg.config(image=self.tracktkimg)
                    self.trackimg.img = self.tracktkimg
                    self.trackimg.grid(row = 0, column = 1)
                    
                self.b,self.g,self.r = cv2.split(self.imgtk)
                self.tkimg = cv2.merge((self.r,self.g,self.b))
                self.tkimg = PILImage.fromarray(self.tkimg)
                self.tkimg = ImageTk.PhotoImage(image=self.tkimg)
                self.displayimg.config(image=self.tkimg)
                self.displayimg.img = self.tkimg
                self.displayimg.grid(row = 0, column = 0)
            After = root.after(10,self.prepare_img_for_tkinter)
        else:
            print('Stopping Camera.')
            self.textbox.insert(END, str('Stopping Camera.\n'))
            self.textbox.see('end')        
After = None
root = Tk()
b = buttons(root)
root.mainloop()
