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
		self.istream = aa.PCM(type=aa.PCM_CAPTURE, mode=aa.PCM_NORMAL, device='pulse')
		self.chunk = 1024
		self.istream.setperiodsize(self.chunk)
		self.istream.setrate(44100)
		self.istream.setchannels(1)
		self.colors = [colors.Red, colors.Yellow, colors.Green, colors.Blue]

		
	def step(self, values, amt = 1):
		dlen, data = self.istream.read()
		soundarray = ndarray(buffer=data, shape = (self.chunk,), dtype=int16)

		fft = librosa.core.stft(soundarray, n_fft = 198)
		sgram = absolute(fft)	
		value = [0.0, 0.0, 0.0, 0.0]
		value[0] = (average(sgram[0]) + average(sgram[1])) / 2 #Subwoofer frequencies
		value[1] = (average(sgram[2]) + average(sgram[3]) + average(sgram[4])) / 3 #Woofer

		for i in range(5, 20):
			value[2] += average(sgram[i])
		value[2] /=  15 #Mid-range

		for i in range(20, 100):
			value[3] += average(sgram[i])
		value[3] /= 80 #Tweeter
		

		value = log10(value) 
		for y in range(4):
			if value[y] == float("-inf"):
				db = 0
			else:
				db = int((value[y] - 3) * 3)# / basechange)
			if db > 12:
				db = 12
			elif db < 1:
				db = 1
			for x in range(db):
				self._led.set(x, y, self.colors[y])
#				self._led.set(y, x, self.colors[y])
			for x in range(db, 12):
				self._led.set(x, y, colors.Black)
#				self._led.set(y, x, colors.Black)
				
				
				

		
			


def main():
	spidriver = SPI(1, 48, spi_speed = 1, c_order = ChannelOrder.BRG, dev = "/dev/spidev0.0", interface = "PERIPHERY")
	striplayout = Matrix(spidriver, width = 12, height = 4, serpentine = False, threadedUpdate=True)
	print(aa.pcms(aa.PCM_CAPTURE))

	anim = Spectrum(striplayout)
	anim.run()

if __name__ == "__main__":
    main()
