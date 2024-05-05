import time
import keyboard
from gtts import gTTS
import os

def play_message():
    tts = gTTS(text="Hey Mommy", lang='en')
    tts.save("hey_mommy.mp3")
    os.system("afplay hey_mommy.mp3")  # Change this line based on your OS's default audio player

def main():
    duration = 10 * 60  # 10 minutes in seconds
    interval = 3  # interval between messages in seconds
    start_time = time.time()

    print("Press Ctrl-Z to stop. None of them work. If you find one that works man, don't hog it. Share it. Sharing is caring.")

    while time.time() - start_time < duration:
        play_message()
        time.sleep(interval)

    print("Press any button you like to stop. None of them work. If you find one that works man, don't hog it. Share it. Sharing is caring.")

    # Loop until Ctrl-Z is pressed
    while True:
        try:
            keyboard.wait('ctrl+z')
            break
        except keyboard.KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
