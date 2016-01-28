#Name: Pause at height (printrbot)
#Info: Pause the printer at a certain height for a certain length of time.
#Depend: GCode
#Type: postprocess
#Param: pauseLevel(float:5.0) Pause height (mm)
#Param: parkDuration(int:60) Duration of pause (s)
#Param: parkX(float:0) Head park X (mm)
#Param: parkY(float:0) Head park Y (mm)
#Param: moveZ(float:0) Head move Z (mm)
#Param: retractAmount(float:5) Retraction amount (mm)

#This plugin is a slightly modified version of the original pauseAtZ written by David Braam. It is modified for the printrbot which doesn't rely on a button press to continue after the pause. The plugin will pause the printer at the given height for the given duration, one minute should be long enough for a filament change.

__copyright__ = "Copyright (C) 2013 David Braam, modified work Copyright 2015 Philip Garner - Released under terms of the AGPLv3 License"
import re
from Cura.util import profile

def getPrintZValue(lineBlock):
	'''
	look for the last z value found just before (or at the same time) G1 code in the given block
	'''
	lastZ = -1
	for line in lineBlock:
		lastZ = getValue(line, 'Z', lastZ)
		if line.startswith('G1 ') and (getValue(line, 'X', None) is not None or getValue(line, 'Y', None) is not None):
			break

	return lastZ


def getValue(line, key, default = None):
	if not key in line or (';' in line and line.find(key) > line.find(';')):
		return default
	subPart = line[line.find(key) + 1:]
	m = re.search('^[0-9]+\.?[0-9]*', subPart)
	if m is None:
		return default
	try:
		return float(m.group(0))
	except:
		return default

with open(filename, "r") as f:
	lines = f.readlines()

z = 0.
x = 0.
y = 0.
pauseState = 0
#state 0 system is not active until we get to a smaller layer than the last encountered layer (default at 99999) (print one at a time support.)
#state 1 system is active and we are looking for our target layer z
#state 2 system found the layer it need to write. We will wait for the first G1 or G0 code to write the content just before. state will be set to 0


with open(filename, "w") as f:
	lineIndex = 0
	lastLayerIndex = 99999
	layerZ = 0
	for lIndex in xrange(len(lines)):
		line = lines[lIndex]
		if line.startswith(';'):
			if line.startswith(';LAYER:'):
				currentLayer = int(line[7:].strip())

				if currentLayer < lastLayerIndex:
					pauseState = 1

				lastLayerIndex = currentLayer
				if pauseState == 1:
					layerZ = getPrintZValue(lines[lIndex:lIndex+20])
					if layerZ >= pauseLevel:
						pauseState = 2

			f.write(line)
			continue

		x = getValue(line, 'X', x)
		y = getValue(line, 'Y', y)

		if pauseState == 2:
			g = getValue(line, 'G', None)
			if g == 1 or g == 0:# We will do the pause just before printing content. We need to pause from the previous XY position. Not the current.
				z = layerZ

				pauseState = 0
				f.write(";TYPE:CUSTOM\n")
				#Retract
				f.write("M83\n")
				f.write("G1 E-%f F6000\n" % (retractAmount))

				zChanged = False
				#Change z before doing the move because the nozzle can hit the glass lock on the UM2
				if z + moveZ < 15:
					zChanged = True
					f.write("G1 Z15 F300\n")

				elif moveZ > 0:
					newZ = z + moveZ
					maxZ = profile.getMachineSettingFloat('machine_height') - 10 #For Safety Leave a 10mm space (endstop)
					if maxZ < newZ:
						newZ = maxZ

					if newZ > z:
						zChanged = True
						f.write("G1 Z%f F300\n" % (newZ))

						
				#Comment to say what we're doing
				f.write(";PAUSING PRINT\n");
				#Move the head away
				f.write("G1 X%f Y%f F9000\n" % (parkX, parkY))

				#Disable the E steppers
				f.write("M84 E0\n")
				#Pause for the desired number of seconds
				f.write("G4 P%s000\n" % (str(parkDuration)))
				#Push the filament back, and retract again, the properly primes the nozzle when changing filament.
				f.write("G1 E%f F6000\n" % (retractAmount))
				f.write("G1 E-%f F6000\n" % (retractAmount))

				#Move the head back. Move Z at the same time to prevent hitting the glass locks on the UM2
				if zChanged :
					f.write("G1 X%f Y%f Z%f F9000\n" % (x, y, z))
				else:
					f.write("G1 X%f Y%f F9000\n" % (x, y))

				f.write("G1 E%f F6000\n" % (retractAmount))
				f.write("G1 F9000\n")
				f.write("M82\n")

		f.write(line)
