from ucnpexp import abstract
import numpy as np
import pandas as pd

class DummyMonochromator:
    def __init__(self):
        self._home_wavelength = 256.5
        self.min_wl = 200
        self.max_wl = 750
        self.wl_step_ratio = 0.5


    def goto_wavelength(self, wl):
        print(f'goin to {wl}')
        self.set_wavelength(wl)

    def set_wavelength(self, wl):
        self._wavelength = wl

    def home(self):
        self.set_wavelength(self._home_wavelength)

class DummySpectrometer(abstract.Spectrometer):

    def __init__(self, lamp, monochromator):
        self.lamp = lamp
        self.monochromator = monochromator

    def set_wavelength(self, wavelength: float):
        self.monochromator.set_wavelength(wavelength)
    
    def goto_wavelength(self, wavelength):
        self.monochromator.goto_wavelength(wavelength)

    def get_emission(self, integration_time, excitation_wavelength=None,
            iterator=False, starting_wavelength=0, ending_wavelength=0,
            wavelength_step=0, emission_wavelength=None):
        wls = np.arange(starting_wavelength, ending_wavelength, wavelength_step) 
        n = len(wls)
        data = pd.DataFrame({
            "wavelength":[0.0]*n,
            "counts":[0]*n,
            "integration time":[0.0]*n
        })
        data["wavelength"] = wls
        data["counts"] = np.random.randint(0, 1000, size=n)
        data["integration time"] = np.ones_like(wls) * integration_time
        return data
        #if iterator:
        #    for i, wl in enumerate(wls):
        #        photons = np.random.randint(0, 1000)
        #        data.at[i, "wavelength"] = wl
        #        data.at[i, "counts"] = photons
        #        data.at[i, "integration time"] = integration_time
        #        yield data
        #else:
        #    for i, wl in enumerate(wls):
        #        photons = np.random.randint(0, 1000)
        #        data.at[i, "wavelength"] = wl
        #        data.at[i, "counts"] = photons
        #        data.at[i, "integration time"] = integration_time
        #    return data
    
    def get_excitation(self, *args, **kwargs):
        return self.get_emission(*args, **kwargs)
        
    @classmethod
    def constructor_default(cls):
        lamp = DummyMonochromator()
        monochromator = DummyMonochromator()
        return DummySpectrometer(lamp, monochromator)