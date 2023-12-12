import time
import numpy as np
import scipy.stats as ss
from redpitaya.overlay.mercury import mercury

class RPDecayStandalone:
    def __init__(self, gpio):
        self.trigger_pin = gpio('n', 7, 'out')
        self.signal_pin = gpio('n', 1, 'out')
        self.trigger_pin.write(True)
        self.signal_pin.write(False)
        self.experiment_number = 0

    def run_experiment(self, lifetime, amount, length, pulse_width=0.001):
        while True:
            sample = self.generate_exponential_sample(lifetime, amount, length)
            dead_time = length - np.cumsum(sample)[-1]
            self.experiment_number += 1
            print("Beginning emission", self.experiment_number)
            t0 = time.monotonic()
            self.trigger()
            for time_untill in sample:
                time.sleep(time_untill)
                self.pulse(pulse_width)
            time.sleep(dead_time)
            print("Ending emission. Total duration", time.monotonic() - t0)

    def generate_exponential_sample(self, lifetime, amount, length):
        rv = ss.expon(scale=lifetime)
        sample = np.diff(np.sort(rv.rvs(amount)))
        return sample[np.cumsum(sample) < length]

    def trigger(self, width=0.001):
        self.trigger_pin.write(False)
        time.sleep(width) 
        self.trigger_pin.write(True)

    
    def pulse(self, width):
        self.signal_pin.write(True)
        time.sleep(width)
        self.signal_pin.write(False)

if __name__ == "__main__":
    fpga = mercury()
    gpio = fpga.gpio
    rpexp = RPDecayStandalone(gpio)
    lifetime = 3.0
    amount = 30
    length = 9.0
    rpexp.run_experiment(lifetime, amount, length)