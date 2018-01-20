#!/usr/bin/python3
from bibliopixel import animation, colors, log, Strip, Matrix
from bibliopixel.drivers.SPI import SPI
from bibliopixel.drivers.driver_base import ChannelOrder
import alsaaudio as aa
import librosa
from numpy import ndarray, int16, average, absolute, log10
log.setLogLevel(log.DEBUG)
basechange = log10(1.2201845430196)
class Strip1(animation.BaseStripAnim):
    def __init__(self, led, start=0, end=-1):
        #The base class MUST be initialized by calling super like this
        super(Strip1, self).__init__(led, start, end)
        #Create a color array to use in the animation
        self._colors = [colors.Red, colors.Orange, colors.Yellow, colors.Green, colors.Blue, colors.Indigo]

    def step(self, amt = 1):
        #Fill the strip, with each sucessive color
        for i in range(self._led.numLEDs):
        #    print("Pixel ", str(i), ": ", str(self._colors[(self._step + i) % len(self._colors)]), sep="")
            self._led.set(i, self._colors[(self._step + i) % len(self._colors)])
        #Increment the internal step by the given amount
        self._step += amt


class Spectrum(animation.BaseMatrixAnim):
	def __init__(self, led, width = 12, height = 4):
		super(Spectrum, self).__init__(led)
		#setup audio input stream from Pulseaudio ALSA
		self.istream = aa.PCM(type=aa.PCM_CAPTURE, mode=aa.PCM_NORMAL, device='pulse')
		self.chunk = 2048 #<- This is how many samples it collects for each update
		self.istream.setperiodsize(self.chunk) #self.chunk / 44100 is how long it will sample for
		self.istream.setrate(44100)
		self.istream.setchannels(1)
		self.colors = [colors.Red, colors.Yellow, colors.Green, colors.Blue]

		
	def step(self, values, amt = 1):
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
		value[0] = max((bins[0] * 2 / 3, bins[1] * 3 / 4)) #SUB (0, 200Hz)
		value[1] = max((bins[2] * 8 / 9, bins[3] * 12 /13, bins[4] * 24 / 25)) #Woofer (200, 500Hz)
		value[2] = bins[5:20].max()#midrange (500, 2000Hz)
		value[3] = bins[20:200].max()#tweeter (2000, 20000Hz)

		#convert power to Bell (volume)
		value = log10(value) 
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

def main():
	spidriver = SPI(1, 48, spi_speed = 1, c_order = ChannelOrder.BRG, dev = "/dev/spidev0.0", interface = "PERIPHERY")
	striplayout = Matrix(spidriver, width = 12, height = 4, serpentine = False, threadedUpdate=True)
	print(aa.pcms(aa.PCM_CAPTURE))

	anim = Spectrum(striplayout)
	anim.run()

if __name__ == "__main__":
    main()
