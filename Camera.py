# -*- coding: ascii -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

try:
	import cv2 as cv
except ImportError:
	cv = None

try:
	from Tkinter import *
except ImportError:
	from tkinter import *

try:
	from PIL import Image, ImageTk
except ImportError:
	cv = None

import Utils

#-------------------------------------------------------------------------------
def hasOpenCV(): return cv is not None

#===============================================================================
# Camera processing class
# A wrapper to opencv needed functions
#===============================================================================
class Camera:
	#-----------------------------------------------------------------------
	# prefix is the prefix to get configuration parameters from ini
	#-----------------------------------------------------------------------
	def __init__(self, prefix=""):
		if cv is None: return
		self.prefix  = prefix
		self.idx     = Utils.getInt("Camera", prefix)
		self.camera  = None
		self.image   = None
		self.frozen  = None
		self.imagetk = None

	#-----------------------------------------------------------------------
	def isOn(self):
		if cv is None: return False
		return self.camera is not None and self.camera.isOpened()

	#-----------------------------------------------------------------------
	def start(self):
		if cv is None: return
		self.camera = cv.VideoCapture(self.idx)
		if self.camera is None: return
		if not self.camera.isOpened():
			self.stop()
			return False
		self.set()
		return True

	#-----------------------------------------------------------------------
	def stop(self):
		if cv is None or self.camera is None: return
		self.camera.release()
#		del self.camera
		self.camera = None

	#-----------------------------------------------------------------------
	def set(self):
		width = Utils.getInt("Camera", self.prefix+"_width",  0)
		if width: self.camera.set(3, width)
		height = Utils.getInt("Camera", self.prefix+"_height",  0)
		if height: self.camera.set(4, height)
		self.angle = Utils.getInt("Camera", self.prefix+"_angle")//90 % 4
#		self.camera.set(38, 3) # CV_CAP_PROP_BUFFERSIZE

	#-----------------------------------------------------------------------
	# Read one image and rotated if needed
	#-----------------------------------------------------------------------
	def read(self):
		s,self.image = self.camera.read()
		if s:
			self.image = self.rotate90(self.image)
		else:
			self.stop()
		self.original = self.image

		if self.frozen is not None:
			self.image = cv.addWeighted(self.image, 0.7, self.frozen, 0.3, 0.0)
		return s

	#-----------------------------------------------------------------------
	# Save image to file
	#-----------------------------------------------------------------------
	def save(self, filename):
		cv.imwrite(filename, self.original)

	#-----------------------------------------------------------------------
	# Rotate image in steps of 90deg
	#-----------------------------------------------------------------------
	def rotate90(self, image):
		if self.angle == 1:	# 90 deg
			return cv.transpose(image)
		elif self.angle == 2: # 180 deg
			return cv.flip(image,-1)
		elif self.angle == 3: # 270 deg
			return cv.flip(cv.transpose(image), 1)
		else:
			return image

	#-----------------------------------------------------------------------
	# Resize image up to a maximum width,height
	#-----------------------------------------------------------------------
	def resize(self, factor, maxwidth, maxheight):
		if factor==1.0: return
		h,w = self.image.shape[:2]
		wn = int(w*factor)
		hn = int(h*factor)
		if wn>maxwidth or hn>maxheight:
			# crop the image to match max
			wn = int(maxwidth/factor)//2
			hn = int(maxheight/factor)//2
			w2 = w//2
			h2 = h//2
			left  = max(w2-wn,0)
			right = min(w2+wn,w-1)
			top   = max(h2-hn,0)
			bottom = min(h2+hn,h-1)
			self.image = self.image[top:bottom,left:right]
		try:
			self.image = cv.resize(self.image, (0,0), fx=factor, fy=factor)
		except:
			# FIXME Too much zoom out, results in void image!
			#self.image = None
			pass

	#-----------------------------------------------------------------------
	# Canny edge detection
	#-----------------------------------------------------------------------
	def canny(self, threshold1, threshold2):
		edge = cv.cvtColor(cv.Canny(self.image, threshold1, threshold2), cv.COLOR_GRAY2BGR)
		self.image = cv.addWeighted(self.image, 0.9, edge, 0.5, 0.0)

	#-----------------------------------------------------------------------
	# Freeze and overlay image
	#-----------------------------------------------------------------------
	def freeze(self, f):
		if f:
			self.frozen = self.image.copy()
		else:
			self.frozen = None

	#-----------------------------------------------------------------------
	# Return center portion of the image to be used as a template
	#-----------------------------------------------------------------------
	def getCenterTemplate(self, r):
		h,w = self.original.shape[:-1]
		w2 = w//2
		h2 = h//2
		return self.original[h2-r:h2+r, w2-r:w2+r]

	#-----------------------------------------------------------------------
	# return location of matching template
	#-----------------------------------------------------------------------
	def matchTemplate(self, template):
		method = cv.TM_CCOEFF_NORMED
		res = cv.matchTemplate(self.original, template, method)
		min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

		h,w = self.original.shape[:-1]
		w2 = w//2
		h2 = h//2

		h,w = template.shape[:-1]
		r = w//2

		# If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
		if method in (cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED):
			top_left = min_loc
		else:
			top_left = max_loc
		#bottom_right = (top_left[0]+2*r, top_left[1]+2*r)
		dx= w2-r - top_left[0]
		dy= h2-r - top_left[1]
		#cv.rectangle(img, top_left, bottom_right, 255, 2)
		#print "Match=",dx,dy
		return dx,dy

	#-----------------------------------------------------------------------
	# Convert to Tk image
	#-----------------------------------------------------------------------
	def toTk(self):
		self.imagetk = ImageTk.PhotoImage(
					image=Image.fromarray(
						cv.cvtColor(self.image, cv.COLOR_BGR2RGB), "RGB"))
		return self.imagetk
