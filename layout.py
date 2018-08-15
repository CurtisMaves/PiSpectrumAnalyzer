#!/usr/bin/python3
from bibliopixel import animation, colors, log, Strip, Matrix
import neopixel 
from bibliopixel.drivers.PiWS281X import PiWS281X
from bibliopixel.drivers.driver_base import ChannelOrder
import alsaaudio as aa
import librosa
from numpy import ndarray, int16, average, absolute, log10
from math import ceil
from time import sleep

#log.setLogLevel(log.DEBUG)
basechange = log10(1.2201845430196)

class SGram():
	def __init__(self):
		#setup audio input stream from Pulseaudio ALSA
		self.istream = aa.PCM(type=aa.PCM_CAPTURE, mode=aa.PCM_NORMAL, device='pulse')
		self.chunk = 2048 #<- This is how many samples it collects for each update
		self.istream.setperiodsize(self.chunk) #self.chunk / 44100 is how long it will sample for
		self.istream.setrate(44100)
		self.istream.setchannels(1)
		self.colors = [colors.Red, colors.Yellow, colors.Green, colors.Blue]
	def get(self):
		#read from audio input stream
		dlen, data = self.istream.read()
		#break data up into array of ints representing audio wave
		soundarray = ndarray(buffer=data, shape = (self.chunk,), dtype=int16)

		#compute Fast Fourier Transform, 
		#breaking it into 200 discrete bins (frequencies, 438 / 2 + 1)
		fft = librosa.core.stft(soundarray, n_fft = 438)
		#absolute to get power of each frequency
		sgram = absolute(fft)	
		value = [0.0, 0.0, 0.0, 0.0]
		#get average power over the whole time interval
		bins = average(sgram, axis=1)

		value[0] = bins[0:2].max() #SUB (0, 200Hz)
		value[1] = bins[2:5].max()  #Woofer (200, 500Hz)
		value[2] = bins[5:20].max() #midrange (500, 2000Hz)
		value[3] = bins[20:220].max() #tweeter (2000, 20000Hz)

		#convert power to Bell (volume)
		value = (2 * log10(value))  

		#compute four different bars, adjusting for human loudness contours
		value[0] -= 2
		value[1] -= .75
		value[2] -= .25
		value[3] -= .5

		#compress range and normalize to 0, 1
		value = (value - 6) / 4.8 # (db - 4.8 - 1.2) / 9.6 * 2
		#print(value)
		return value
	
class Spectrum(animation.BaseMatrixAnim):
	def __init__(self, led, length = 300):
		super(Spectrum, self).__init__(led)
		self.input = SGram()
		self.colors = [colors.Red, colors.Yellow, colors.Green, colors.Blue]
		self.half_length = int(ceil(length / 2))
		self.seg_length = int(ceil(self.half_length / 4))

	def step(self, amt = 1):
		value = self.input.get()
		for y in range(4):
			if value[y] == float("-inf"):
				db = 0
			else:
				db = int(value[y] * self.seg_length)# / basechange)
			if db > self.seg_length:
				db = 12
			elif db < 1:
				db = 1
			for x in range(db):
				self._led.set(x, y, self.colors[y])
			for x in range(db, self.seg_length):
				self._led.set(x, y, colors.Black)

class StripSpectrum(animation.BaseStripAnim):
	def __init__(self, led, length = 300):
		super(StripSpectrum, self).__init__(led)
		self.input = SGram()
		self.length = length
		self.last = length - 1
		self.half_length = int(ceil(length / 2))
		self.seg_length = int(ceil(self.half_length / 4))
		self.colors = [colors.Red, colors.Yellow, colors.Green, colors.Blue]
	def step(self, amt = 1):
		value = self.input.get()
		count = 0	
		led = [None] * self.half_length
		for y in range(4):
			if value[y] == float("-inf"):
				db = 0
			else:
				db = int(value[y] * self.seg_length)
			#print(db, end=" ")
			if db > self.seg_length:
				db = self.seg_length
			elif db < 1:
				db = 1
			for x in range(db):
				led[count] = self.colors[y]
				count += 1
		
		#print("\n",count)
		for x in range(count, self.length- count):
			self._led.set(x, colors.Black)
		for x in range(count):
			self._led.set(x, led[x])
			self._led.set(self.last - x, led[x])

def main():
	length = 300
	npdriver = PiWS281X(length, c_order = ChannelOrder.RGB)
	#striplayout = Matrix(spidriver, width = 12, height = 4, serpentine = False, threadedUpdate=True)
	striplayout = Strip(npdriver, threadedUpdate=True, brightness = 50)
	print(aa.pcms(aa.PCM_CAPTURE))

	anim = StripSpectrum(striplayout, length=length)
	anim.run()

if __name__ == "__main__":
    main()
