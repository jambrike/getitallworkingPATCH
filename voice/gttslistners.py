import os
import pygame
from gtts import gTTS


import sys

pygame.mixer.init()

def speak(text):
	tts = gTTS(text=text, lang='en')
	filename = os.path.join(os.path.dirname(__file__), "ai_tts_output.mp3")
	try:
		tts.save(filename)
		pygame.mixer.music.load(filename)
		pygame.mixer.music.play()
		while pygame.mixer.music.get_busy():
			pygame.time.Clock().tick(10)
	finally:
		if os.path.exists(filename):
			os.remove(filename)

if __name__ == "__main__":
	if len(sys.argv) > 1:
		text = ' '.join(sys.argv[1:])
		speak(text)
	else:
		print("No text provided for TTS.")
