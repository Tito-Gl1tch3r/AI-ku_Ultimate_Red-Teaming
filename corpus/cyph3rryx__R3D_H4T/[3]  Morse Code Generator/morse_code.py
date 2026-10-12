import pygame
import time

# Morse code dictionary
morse_code_dict = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.',
    'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.',
    'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-',
    'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--', 'Z': '--..',
    '1': '.----', '2': '..---', '3': '...--', '4': '....-', '5': '.....',
    '6': '-....', '7': '--...', '8': '---..', '9': '----.', '0': '-----',
    ' ': ' ',  # Space
}

# Function to convert text to Morse code
def text_to_morse(text):
    text = text.upper()
    morse_code = ""
    for char in text:
        if char in morse_code_dict:
            morse_code += morse_code_dict[char] + ' '
    return morse_code

# Function to play Morse code as audio
def play_morse_code_audio(morse_code):
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.5)
    for symbol in morse_code:
        if symbol == '.':
            pygame.mixer.music.load('dot.wav')  # Replace with the path to your dot.wav file
        elif symbol == '-':
            pygame.mixer.music.load('dash.wav')  # Replace with the path to your dash.wav file
        elif symbol == ' ':
            time.sleep(0.2)  # Pause for inter-character gap
            continue
        pygame.mixer.music.play()
        time.sleep(0.2)  # Adjust this duration as needed for timing
        while pygame.mixer.music.get_busy():
            pass
        time.sleep(0.2)  # Pause for inter-symbol gap

if __name__ == "__main__":
    text_input = input("Enter text to transmit in Morse code: ")
    morse_code = text_to_morse(text_input)
    print("Morse code representation:", morse_code)
    play_morse_code_audio(morse_code)
