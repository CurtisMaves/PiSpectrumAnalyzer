#!/usr/bin/python3

from rpi_ws281x import PixelStrip, WS2812_STRIP, Color
import alsaaudio as aa
import librosa
from numpy import ndarray, int16, average, absolute, log10, array, zeros
from math import ceil
from time import sleep
from concurrent.futures import ThreadPoolExecutor, wait


class SGram():
	def __init__(self):
		#setup audio input stream from Pulseaudio ALSA
		self.istream = aa.PCM(type=aa.PCM_CAPTURE, mode=aa.PCM_NORMAL, device='pulse')
		self.chunk = 2048 #<- This is how many samples it collects for each update
		self.istream.setperiodsize(self.chunk) #self.chunk / 44100 is how long it will sample for
		self.istream.setrate(44100)
		self.istream.setchannels(1)
		self.istream.setformat(aa.PCM_FORMAT_S16_LE)

		# compute A_weights for each frequency
		a_weight = zeros((220,))
		for i in range(0, 220):
			a_weight[i] = 50 + i * 100
		self.a_weight = librosa.core.A_weighting(a_weight).reshape(220, 1)

	def get(self):
		#read from audio input stream
		dlen, data = self.istream.read()
		#break data up into array of ints representing audio wave
		soundarray = ndarray(buffer=data, shape = (self.chunk,), dtype=int16)
		# convert to float
		soundarray = librosa.util.buf_to_float(soundarray)

		#compute Fast Fourier Transform, 
		#breaking it into 220 discrete bins (frequencies, 438 / 2 + 1)
		fft = librosa.core.stft(soundarray, n_fft = 438)
		# convert to db
		sgram = librosa.core.amplitude_to_db(abs(fft), top_db=120)
		# do A-weighting
		w_sgram = sgram + self.a_weight
		#get average db over the whole time interval
		a_sgram = average(w_sgram, axis=1)
		#a_sgram = average(sgram, axis=1)
		

		#sgram = absolute(fft)	
		value = zeros((4,))
		value[0] = a_sgram[0:2].max() #SUB (0, 200Hz)
		value[1] = a_sgram[2:5].max()  #Woofer (200, 500Hz)
		value[2] = a_sgram[5:20].max() #midrange (500, 2000Hz)
		value[3] = a_sgram[20:220].max() #tweeter (2000, 20000Hz)

		# normalize to approx (-27/70, 1) by adding add 70 and dividing by 70
		value += 60
		value /= 80
		return value
	
class StripSpectrum():
	def __init__(self, led):
		self.input = SGram()
		self._led = led
		self.length = led.numPixels()
		self.last = self.length - 1
		self.half_length = self.length // 2
		self.seg_length = self.half_length // 4
		self.colors = [(255, 0, 0), (185, 185, 0), (0, 255, 0), (0, 0, 255)]
		self.cur_color = ((0,0,0),) * self.half_length
		self.tar_color = ((0,0,0),) * self.half_length

		# setup thread pool
		self._thread_pool = ThreadPoolExecutor(max_workers=1)
		self._future = None

	def set_color(self, leds):
		self.tar_color = leds

		self.cur_color = [tuple((int((self.tar_color[x][y]  + self.cur_color[x][y] * 2) / 3) for y in range(3)))for x in range(self.half_length)]
		for x in enumerate(self.cur_color):
			self._led.setPixelColor(x[0], Color(*x[1]))
			self._led.setPixelColor(self.last - x[0], Color(*x[1]))
			

	def update(self, amt = 1):
		value = self.input.get()
		print(value)
		count = 0	
		led = [(0,0,0)] * self.half_length
		for y in range(4):
			db = int(value[y] * self.seg_length)
			#print(db, end=" ")
			if db > self.seg_length:
				db = self.seg_length
			elif db < 1:
				db = 1
			for x in range(db):
				led[count] = self.colors[y]
				count += 1
				if count >= self.half_length:
					break

		self.set_color(led)

	def iterate(self):
		# wait for update to complete
		if self._future != None:
			self._future.result()
		self.update()
		# start pixel update in background
		self._future = self._thread_pool.submit(self._led.show)

	def iterate_forever(self):
		while True:
			self.iterate()
		
			

def main():
	length = 300
	strip = PixelStrip(length, 18, strip_type=WS2812_STRIP)
	strip.begin()
	anim = StripSpectrum(strip)
	anim.iterate_forever()

if __name__ == "__main__":
    main()
