import scipy.stats as ss
import numpy as np
import time
from threading import Thread, Event

class RPDecay(Thread):
    def __init__(self, gpio, lifetime, amount, length):
        super().__init__()
        self.trigger_pin = gpio('n', 7, 'out')
        self.signal_pin = gpio('n', 1, 'out')
        self.lifetime = lifetime
        self.length = length
        self.amount = amount
        self.trigger_pin.write(True)
        self.signal_pin.write(False)
        self.done = False
        self.finish_requested = False
        self._stop_event = Event()

    def run(self):
        time.sleep(0.1)
        self.run_experiment(self.lifetime, self.amount, self.length)
        
    def generate_exponential_sample(self, lifetime, amount, length):
        rv = ss.expon(scale=lifetime)
        sample = np.diff(np.sort(rv.rvs(amount)))
        return sample[np.cumsum(sample) < length]

    def trigger(self, width=0.001):
        self.trigger_pin.write(False)
        time.sleep(width) 
        self.trigger_pin.write(True)
        
    def run_experiment(self, lifetime, amount, length, pulse_width=0.001):
        #out = []
        sample = self.generate_exponential_sample(lifetime, amount, length)
        self.trigger()
        start = time.monotonic()
        for time_untill in sample:
            time.sleep(time_untill)
            #out.append(time.monotonic() - start)
            self.pulse(pulse_width)
            print("finish req", self.finish_requested)
            if self.finish_requested:
                print("breaking")
                self._stop_event.set()
                break
        self.done = True

    def pulse(self, width):
        self.signal_pin.write(True)
        time.sleep(width)
        self.signal_pin.write(False)

    def pulse_after_trigger(self, seconds, pulse_width=0.001):
        self.trigger()
        time.sleep(seconds)
        self.pulse(pulse_width)


