import numpy as np
import scipy.stats as ss

class RPDecayStandaloneSimulator:
    def __init__(self, amount_datapoints):
        self.amount_datapoints = amount_datapoints

    def generate_real_timeline(self, length, datapoints, resolution=10):
        return np.linspace(0, length, resolution * datapoints)

    def run_experiment(self, lifetime, amount, length, pulse_width=0.001):
        self.real_timeline = np.linspace(0, length, self.amount_datapoints)
        self.real_signal = np.zeros_like(self.real_timeline)
        self.i = 0
        sample = self.generate_exponential_sample(lifetime, amount, length)

        acum_time = 0
        for time_untill in sample:
            while self.i < self.amount_datapoints and self.real_timeline[self.i] < acum_time + time_untill:
                self.i = self.i + 1
            if self.i >= self.amount_datapoints:
                break
            acum_time = self.real_timeline[self.i]
            self.pulse(pulse_width)
        return self.real_timeline, self.real_signal

    def generate_exponential_sample(self, lifetime, amount, length):
        rv = ss.expon(scale=lifetime)
        sample = np.diff(np.sort(rv.rvs(amount)))
        return sample[np.cumsum(sample) < length]

    def pulse(self, width):
        t0 = self.real_timeline[self.i]
        while self.i < self.amount_datapoints and self.real_timeline[self.i] < t0 + width:
            self.real_signal[self.i] = 5
            self.i = self.i + 1

class RPOscSim:
    def __init__(self, amount_datapoints, mes_time):
        self.amount_datapoints = amount_datapoints
        self.mes_time = mes_time
        self.sampling_rate = amount_datapoints/mes_time

    def measure_screen(self, real_time, real_screen, offset=0):
        window = real_time < self.mes_time + offset
        window = window & (offset < real_time)

        subsampling = int(len(real_time)/self.amount_datapoints)
        time = real_time[window]
        time = time[0::subsampling]
        screen = real_screen[window]
        screen = screen[0::subsampling]
        return time, screen

def acquire_decay(osc, rpsim, lifetime, amount_windows=1,
                  amount_buffers=1, pct_overlap=0,
                  measurement_length=9.0, path=None, threshold=2):
    counts = np.array([]) 
    for window in range(amount_windows):
        offset = (1 - pct_overlap)*window*osc.mes_time
        if offset + osc.mes_time > measurement_length:
            print("Offset and measurement time exceed simulated length")
            print("returning...")
            return
        time_axis = np.arange(0, osc.amount_datapoints, 1.0)/osc.sampling_rate + offset
        for buffer in range(amount_buffers):
            print(f"asking for window {window} and buffer {buffer}")
            real_time, real_screen = rpsim.run_experiment(lifetime, 30, measurement_length)
            time, screen = osc.measure_screen(real_time, real_screen, offset=offset)
            #plt.plot(real_time, real_screen, alpha=0.8)
            #plt.plot(time, screen, alpha=0.8)
            #plt.plot(time[1:], (np.diff(screen) > threshold)*1)
            #plt.show()
            #return

            #peaks = np.where(np.diff(screen) > threshold)[0]
            times = time[1:][np.diff(screen) > threshold]
            #times = peaks/osc.sampling_rate + offset
            counts = np.hstack((counts, times))
    return counts

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    amount_datapoints = 11444
    sampling_rate = 3814.697265625
    mes_time = 2.999975936
    rpsim = RPDecayStandaloneSimulator(10*amount_datapoints)
    rposcsim = RPOscSim(amount_datapoints, mes_time)
    lifetime = 3.0
    amount = 30
    length = 9.0

    
    counts = acquire_decay(rposcsim, rpsim, lifetime,
            amount_windows=5, amount_buffers=100, pct_overlap=0.5)
    bins = np.linspace(0, 3*lifetime, 50)
    freq, bins = np.histogram(counts, density=True, bins=bins)
    bin_width = bins[1] - bins[0]
    bin_centres = bins[1:] - bin_width/2
    plt.stairs(freq, bins)
    plt.plot(bin_centres, freq, '.')
    plt.show()