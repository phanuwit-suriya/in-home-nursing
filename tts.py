import pyttsx3


class Synthesizer:
    def __init__(self, rate=200, volume=1.0):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', volume)

    def run(self, text):
        self.engine.say(text)
        self.engine.runAndWait()


if __name__ == '__main__':
    syn = Synthesizer()
    syn.run("I have a male voice but I don't have a gender identity. I'm just a computer program")
