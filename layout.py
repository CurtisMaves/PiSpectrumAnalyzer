#!/usr/bin/python3
from bibliopixel import animation, colors, log, Strip, Matrix
from bibliopixel.drivers.SPI import SPI
from bibliopixel.drivers.driver_base import ChannelOrder
import alsaaudio as aa
import librosa
from numpy import ndarray, int16, average, absolute, log10
log.setLogLevel(log.DEBUG)
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
		#breaking it into 200 discrete bins (frequencies, 398 / 2 + 1)
		fft = librosa.core.stft(soundarray, n_fft = 398)
		#absolute to get power of each frequency
		sgram = absolute(fft)	
		value = [0.0, 0.0, 0.0, 0.0]
		#get average power over the whole time interval
		bins = average(sgram, axis=1)

		#compute four different bars, adjusting for human loudness contours
		value[0] = bins[0:2].max() #SUB (0, 200Hz)
		value[1] = bins[2:5].max()  #Woofer (200, 500Hz)
		value[2] = bins[5:20].max() #midrange (500, 2000Hz)
		value[3] = bins[20:200].max() #tweeter (2000, 20000Hz)

		#convert power to Bell (volume)
		value = log10(value) 
		return value
	
class Spectrum(animation.BaseMatrixAnim):
	def __init__(self, led, width = 12, height = 4):
		super(Spectrum, self).__init__(led)
		self.input = SGram()
		self.colors = [colors.Red, colors.Yellow, colors.Green, colors.Blue]

		
	def step(self, amt = 1):
		value = self.input.get()
		for y in range(4):
			if value[y] == float("-inf"):
				db = 0
			else:
				db = int((value[y] - 4.5) * 9)# / basechange)
			if db > 12:
				db = 12
			elif db < 1:
				db = 1
			for x in range(db):
				self._led.set(x, y, self.colors[y])
			for x in range(db, 12):
				self._led.set(x, y, colors.Black)
class StripSpectrum(animation.BaseStripAnim):
	def __init__(self, led, length = 48, sections = 2):
		super(StripSpectrum, self).__init__(led)
		self.input = SGram()
		self.length = length
		self.sections = sections
		self.colors = [colors.Red, colors.Yellow, colors.Green, colors.Blue]
	def step(self, amt = 1):
		value = self.input.get()
		count = 0	
		led = [(0,0,0)] * self.length
		for y in range(4):
			if value[y] == float("-inf"):
				db = 0
			else:
				db = int((value[y] - 4.5) * 9)# / basechange)
			if db > 12:
				db = 12
			elif db < 1:
				db = 1
			for x in range(db):
				led[count] = self.colors[y]
				count += 1

		for x in range(count, self.length):
			led[x] = colors.Black
		for x in range(self.length):
			self._led.set(x, led[x])
			self._led.set(95 - x, led[x])

def main():
	spidriver = SPI(1, 98, spi_speed = 1, c_order = ChannelOrder.BRG, dev = "/dev/spidev0.0", interface = "PERIPHERY")
	#striplayout = Matrix(spidriver, width = 12, height = 4, serpentine = False, threadedUpdate=True)
	striplayout = Strip(spidriver, threadedUpdate=True)
	print(aa.pcms(aa.PCM_CAPTURE))

	anim = StripSpectrum(striplayout)
	anim.run()

if __name__ == "__main__":
    main()
