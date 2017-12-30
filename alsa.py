#!/usr/bin/python
import alsaaudio as aa
import librosa
import sys
from numpy import ndarray, int16, average, absolute, log10
from time import sleep

print(aa.pcms(aa.PCM_CAPTURE))

stream = aa.PCM(type=aa.PCM_CAPTURE, mode=aa.PCM_NORMAL, device='pulse')
chunk = 1024
stream.setperiodsize(chunk)
stream.setrate(44100)
stream.setchannels(1)

dlen, data = stream.read()
print(data)
max = -sys.maxsize
min = sys.maxsize
count = 0
dlen, data = stream.read()
soundarray = ndarray(buffer=data, shape = (chunk,), dtype=int16)
sfft = librosa.core.stft(soundarray, n_fft = 14)
sgram = absolute(sfft)

for array in sgram:
	for i in array:
		if max < i:
			max = i
		if min > i:
			min = i	

print(max)
print(min)
print(log10(1.2201845))



exit()

