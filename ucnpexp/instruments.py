from . import abstract
import yaml
import rpyc
from . import user_interface as ui
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy as sp
import pyvisa
import time
from dataclasses import dataclass

class ITC4020:
    def __init__(self, config_path):
        self.RESOURCE_STRING = 'USB0::4883::32842::M00404162::0::INSTR'
        self.TIMEOUT = 100000
        self.ID = 'Thorlabs,ITC4001,M00404162,1.8.0/1.5.0/2.3.0\n'
        rm = pyvisa.ResourceManager('@py')
        self.itc = rm.open_resource(self.RESOURCE_STRING)
        self._establish_connection()
        #self.load_configuration(config_path)

    def query(self, *args, **kwargs):
        return self.itc.query(*args, **kwargs)

    def _establish_connection(self):
        start = time.time()
        while time.time() - start < self.TIMEOUT:
            try:
                msg = self.itc.query('*IDN?')
                if msg == self.ID:
                    print(f"Connection established as expected\n{msg}")
                    return True
                else:
                    print(f"Connection established to unknown instrument\n{msg}")
            except Exception as e:
                print(e)
        raise TimeoutError
    
    def load_configuration(self, path, verbose=False):
        try:
            with open(path, 'r') as f:
                self._configuration = yaml.safe_load(f)
        except FileNotFoundError as e:
            print(f"Error: configuration file '{path}' not found.")
            return
        for menu_name, menu_vals in self._configuration.items():
            if verbose: print(f"Setting {menu_name} vals:")
            for parameter, value in menu_vals.items():
                if hasattr(self, parameter):
                    setattr(self, parameter, value)
                    if verbose: print("{parameter} = {value}")
                else:
                    print(f"ITC4020 has no attribute {parameter}")

    def turn_on_laser(self):
        if self.keylock_tripped:
            print("Please unlock safety key")
            return
        if self.modulation and self.qcw_mode == 'PULS':
            print("Both modulation and QCW mode are on.")
            print("Turn one off before turning on the LASER.")
            return
        self.tec_output = True
        while self.temp_tripped:
            print("Waiting for laser to cool")
            time.sleep(1)
        self.ld_output = True

    # esto hay que cambiarlo para que no dependa de una config file
    def get_configuration(self, path):
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError as e:
            print(f"Error: configuration file '{path}' not found.")
            return
        for menu_name, menu_params in config.items():
            print(f"{menu_name} values:")
            for param in menu_params:
                print(f"{param} = {getattr(self, param)}")

    @property
    def ld_output(self):
        return bool(int(self.itc.query('output:state?')))

    @ld_output.setter
    def ld_output(self, state):
        try:
            state = int(state)
            if state not in [0, 1]:
                print("state should be either 0 or 1, not {state}")
                return
            self.itc.write(f'output:state {int(state)}')
        except ValueError as e:
            print(e)

    @property
    def tec_output(self):
        return bool(int(self.itc.query('output2:state?')))

    @tec_output.setter
    def tec_output(self, state):
        try:
            state = int(state)
            if state not in [0, 1]:
                print("state should be either 0 or 1, not {state}")
                return
            self.itc.write(f'output2:state {int(state)}')
        except ValueError as e:
            print(e)

    @property
    def temp_tripped(self):
        return bool(int(self.itc.query('sense3:temperature:protection:tripped?')))

    @property
    def polarity(self):
        return self.itc.query('output:polarity?')

    @polarity.setter
    def polarity(self, polarity_value):
        if polarity_value in ["CG", "AG"]:
            self.itc.write(f'output:polarity {polarity_value}')
        else:
            print("Wrong polarity value")
    
    @property
    def voltage_protection(self):
        return self.itc.query('output:protection:voltage?')

    @voltage_protection.setter
    def voltage_protection(self, voltage_limit):
        self.itc.query(f'output:protection:voltage {voltage_limit}')
    
    @property
    def operating_mode(self):
        return self.itc.query('source:function:mode?')

    @operating_mode.setter
    def operating_mode(self, mode):
        if mode in ["current", "power"]:
            self.itc.write(f'source:function:mode {mode}')
        else:
            print("Wrong operating mode")
        
    @property
    def laser_current_limit(self):
        return self.itc.query('source:current:limit?')
    
    @laser_current_limit.setter
    def laser_current_limit(self, limit):
        self.itc.write(f'source:current:limit {limit}')

    @property
    def optical_power_limit(self):
        return self.itc.query('sense:power:protection?')

    @optical_power_limit.setter
    def optical_power_limit(self, limit):
        self.itc.write(f'sense:power:protection {limit}')

    @property
    def optical_power(self):
        return float(self.itc.query('measure:power2?')[:-1])
    
    @property
    def temperature(self):
        return float(self.itc.query('measure:temperature?')[:-1])

    @property
    def laser_current(self):
        return float(self.itc.query('source:current?')[:-1])
    
    @laser_current.setter
    def laser_current(self, current):
        self.itc.write(f'source:current {current}')

    @property
    def modulation(self):
        return bool(int(self.itc.query('source:am:state?')[:-1]))
    
    @modulation.setter
    def modulation(self, state):
        # revisar: agregar para que apague qcw
        state = bool(state)*1
        self.itc.write(f'source:am:state {state}')

    @property
    def qcw_mode(self):
        resp = self.itc.query('source:function:shape?')[:-1]
        if resp == 'PULS':
            return True
        else:
            return False

    @qcw_mode.setter
    def qcw_mode(self, mode):
        # mode = False -> dc
        # mode = True -> pulse
        print(f"{self.qcw_mode=}, {mode=}")
        if mode == self.qcw_mode:
            print("Already in that mode")
            return
        # revisar: agregar para que apague modulation
        if mode:
            print(f"{self.qcw_mode=}, {mode=}")
            self.itc.query(f'source:function:shape pulse')
        else:
            print(f"{self.qcw_mode=}, {mode=}")
            self.itc.query(f'source:function:shape dc')

    @property
    def trigger_source(self):
        return self.itc.query('trigger:source?')

    @trigger_source.setter
    def trigger_source(self, source):
        if source in ["internal", "external"]:
            print(self.itc.query(f'trigger:source {source}'))
        else:
            print(f"Source {source} not supported")
    
    @property
    def frequency(self):
        val = float(self.itc.query("source:pulse:period?"))
        return 1/val
    
    @frequency.setter
    def frequency(self, value):
        self.itc.write(f'source:pulse:period {1/value}')

    @property
    def duty_cycle(self):
        return float(self.itc.query('source:pulse:dcycle?')[:-1])

    @duty_cycle.setter
    def duty_cycle(self, dc):
        self.itc.write(f'source:pulse:dcycle {dc}')

    @property
    def hold(self):
        return self.itc.query('source:pulse:hold?')

    @hold.setter
    def hold(self, value):
        if value in ['width', 'dcycle']:
            self.itc.write(f'source:pulse:hold {value}')
        else:
            print(f"Hold parameter {value} is not supported")
    
    @property
    def keylock_tripped(self):
        return bool(int(self.itc.query('output:protection:keylock:tripped?')))


class OscilloscopeChannel:
    def __init__(self, conn, *, channel= 0, voltage_range=20.0,
                  decimation=1, trigger_post=2**14, trigger_pre=0):
        self._maximum_sampling_rate = 125e6
        self.osc = conn.root.create_osc_channel(channel=channel,
                                                voltage_range=voltage_range,
                                                decimation=decimation,
                                                trigger_post=trigger_post,
                                                trigger_pre=trigger_pre)

    def set_measurement_time(self, seconds, offset=0, verbose=False):
        if offset < -self.buffer_size / (self._maximum_sampling_rate/2**16) or (seconds + offset) <= 0:
            print(f"Offset {offset}s not valid for {seconds}s measurement time.")
            return
        decimation_exponent = int(np.ceil(np.log2(
            self._maximum_sampling_rate * seconds / self.buffer_size
            )))
        self.decimation = decimation_exponent
        if offset < 0:
            self.trigger_pre = int(abs(offset) * self.sampling_rate)
            self.trigger_post = (seconds + offset) * self.sampling_rate if (seconds + offset) > 0 else 1
        else:
            self.trigger_pre = 0
            self.trigger_post = int((seconds + offset) * self.sampling_rate)
        self._amount_datapoints = int(seconds * self.sampling_rate)
        if verbose:
            print(f"Setting decimation exponent to {decimation_exponent}")
            print(f"The sampling rate is {self._maximum_sampling_rate/self.decimation} Hz")
            print(f"Setting trigger_pre to {self.trigger_pre}")
            print(f"Setting trigger_post to {self.trigger_post}")
            print(f"A total of {self.amount_datapoints} data points will be taken")
            print(f"Measurement time will be {self.get_measurement_time()}")

    def get_measurement_time(self):
        return self.amount_datapoints / self.sampling_rate

    # Debería cambiarle el nombre a trigger no?
    def measure(self, transit_seconds=0.0):
        return self.osc.measure(data_points=self.amount_datapoints,
                                transit_seconds=transit_seconds)

    def get_triggered(self, data_points=None):
        if data_points is None:
            data_points = self.amount_datapoints
        return self.osc.get_triggered(data_points)

    @property
    def amount_datapoints(self):
        if self._amount_datapoints is None:
            print("Measurement time not set yet")
            return
        if self._amount_datapoints > self.buffer_size:
            print("Warning: amount of data points is greater than buffer size")
        return self._amount_datapoints
    
    @property
    def channel(self):
        return self.osc.channel()

    @property
    def buffer_size(self):
        return self.osc.buffer_size()

    @property
    def sampling_rate(self):
        return self._maximum_sampling_rate/self.decimation

    @property
    def trigger_pre(self):
        return self.osc.trigger_pre()

    @trigger_pre.setter
    def trigger_pre(self, amount):
        self.osc.set_trigger_pre(amount)

    @property
    def trigger_post(self):
        return self.osc.trigger_post()

    @trigger_post.setter
    def trigger_post(self, amount):
        self.osc.set_trigger_post(amount)

    @property
    def decimation(self):
        return self.osc.decimation()
    
    @decimation.setter
    def decimation(self, amount):
        self.osc.set_decimation(amount)

    @property
    def trig_src(self):
        return self.osc.trig_src()
    
    def set_trigger(self, channel, edge='pos', level=None):
        self.osc.set_trigger(channel, edge, level)
    # Esto tira algún tipo de warning que después 
    # Tengo que ver qué significa
    # Pero por ahora parece que funciona
    def __del__(self):
        self.osc.delete()

class RPTTL(abstract.TTL):
    def __init__(self, state, pin, gpio):
        column, number = pin
        self._gpio = gpio(column, number, 'out')
        super().__init__(state)
        
    def _get_state(self):
        return self._gpio.read()
        
    def _set_state(self, state):
        self._gpio.write(state)

class A4988(abstract.MotorDriver):
    ttls: dict
    # Mientras se use la shell para el pololu esto está 
    # fijo en "full step".
    # Sin embargo, Por algún motivo 400 pasos es aprox 360 grados
    _MODES = (
                (False, False, False), #Full step
                (True, False, False) , #Half 
                (False, True, False) , #Quarter
                (True, True, False)  , #Eighth
                (True, True, True)   , #Sixteenth
               )

    def __init__(self, ttls: dict, mode: int = 0):
        for ttl in ttls:
            setattr(self, ttl, ttls[ttl])

    def set_stepping(self, mode: int):
        s1, s2, s3 = self._MODES[mode]
        self.ms1.set_state(s1)
        self.ms2.set_state(s2)
        self.ms3.set_state(s3)

    def get_stepping(self):
        return self._MODES.index((self.ms1.state, self.ms2.state, self.ms3.state))

    #Obs: creo que la minima duracion del pulso es 1 micro segundo
    #Obs2: para q funcione el step debe ir de low a high. Si se 
    # Desconfigura a mano el step (por ejemplo poniendo 
    # driver.step.state = True), esta driver.step() no va a hacer lo
    # esperado (pensar cómo solucionar).
    def step(self, ontime=10e-3, offtime=10e-3, amount=1):
        self.pin_step.pulse(ontime, offtime, amount)
    
class M061CS02(abstract.Motor):
    _STEPS_MODE = (200, 400, 800, 1600, 3200)

    def __init__(self, driver, steps: int = 400, angle: float = 0.0):
        self._driver = driver
        self._angle = angle
        self._angle_relative = angle % 360
        self.steps = steps
        self._min_angle = 360.0/self.steps
        self._min_offtime = 10e-3
        self._min_ontime = 10e-3

    def rotate(self, angle: float):
        relative_angle = angle - self._angle
        angle_rotated = self.rotate_relative(relative_angle)
        return angle_rotated

    def rotate_relative(self, angle: float, change_angle: bool = True):
        cw, angle = angle > 0, abs(angle)
        self._driver.direction.set_state(cw)
        steps = int(angle/self.min_angle)
        self.rotate_step(steps, cw, change_angle=change_angle)
        angle_rotated = (2 * cw - 1) * self.min_angle * steps
        return angle_rotated

    def rotate_step(self, steps: int, cw: bool, change_angle: bool = True):
        self._driver.direction.set_state(cw)
        self._driver.step(ontime = self._min_ontime,
                          offtime= self._min_offtime,
                          amount = steps)
        if change_angle:
            angle_change_sign = (int(cw)*2 - 1)
            self._angle = round(self._angle + angle_change_sign * self.min_angle * steps, 5)

    @property
    def angle(self):
        return self._angle

    @property
    def angle_relative(self):
        return self._angle % 360

    @property
    def min_angle(self):
        return 360 / self.steps

    @property
    def steps(self, steps: int = 200):
        return self._STEPS_MODE[self._driver.get_stepping()]

    @steps.setter
    def steps(self, steps: int = 200):
        self._driver.set_stepping(self._STEPS_MODE.index(steps))

    def set_origin(self, angle: float = 0):
        self._angle = angle

class GPIO_helper:
    def __init__(self, column: str, pin: int, io: str):
        self.column = column
        self.pin = pin
        self.io = io
        self.set_state(True)

    def write(self, state: bool):
        self.set_state(state)

    def read(self):
        return self.state

class Monochromator:
    def __init__(self, motor: abstract.Motor, limit_switch: RPTTL = None):
                 # A esto por ahora lo pongo así, pero debería implementarlo
                 # en la calibraición mejor
        self.CALIB_ATTRS = [ '_wl_step_ratio',
                    '_greater_wl_cw',
                    '_max_wl',
                    '_min_wl',
                    '_home_wavelength']
        self._motor = motor
        self._limit_switch = limit_switch

    @classmethod
    def constructor_default(cls, conn, pin_step, pin_direction, limit_switch, MOTOR_DRIVER=A4988,
                             MOTOR=M061CS02):
        ttls = {
                'notenable' :   conn.root.create_RPTTL('notenable', (False, 'n', 0)),
                'ms1'       :   conn.root.create_RPTTL('ms1', (False, 'n', 1)),
                'ms2'       :   conn.root.create_RPTTL('ms2', (False, 'n', 2)),
                'ms3'       :   conn.root.create_RPTTL('ms3', (False, 'n', 3)),
                'notreset'  :   conn.root.create_RPTTL('notreset', (True, 'n', 4)),
                'pin_step'  :   conn.root.create_RPTTL('pin_step', (False, 'p', pin_step)),
                'direction' :   conn.root.create_RPTTL('direction', (True, 'p', pin_direction)),
                }
        driver = MOTOR_DRIVER(ttls)
        motor = MOTOR(driver)
        limit_switch = conn.root.create_RPDI('limit_switch', ("p", limit_switch)) 
        return cls(motor, limit_switch=limit_switch)

    @property
    def wavelength(self):
        try:
            return self._wavelength
        except:
            return None

    @property
    def min_wl(self):
        return self._min_wl

    @property
    def max_wl(self):
        return self._max_wl

    @property
    def greater_wl_cw(self):
        return self._greater_wl_cw

    @property
    def wl_step_ratio(self):
        return self._wl_step_ratio

    @property
    def home_wavelength(self):
        return self._home_wavelength

    def set_wavelength(self, wavelength: float):
        if self.check_safety(wavelength):
            self._wavelength = wavelength
        else:
            print(f"Wavelength must be between {self._min_wl} and {self._max_wl}")

    def check_safety(self, wavelength):
        return self._min_wl <= wavelength <= self._max_wl

    def goto_wavelength(self, wavelength: float):
        if self.check_safety(wavelength):
            steps = abs(int((wavelength - self.wavelength)/self._wl_step_ratio))
            cw = (wavelength - self.wavelength) > 0
            cw = not (cw ^ self.greater_wl_cw)
            self._motor.rotate_step(steps, cw)
            self._wavelength = wavelength
        else:
            print(f"Wavelength must be between {self._min_wl} and {self._max_wl}")
        return self._wavelength

    @property
    def limit_switch(self):
        return self._limit_switch

    def load_calibration(self, path): #wavelength
        with open(path, 'r') as f:
            self._calibration = yaml.safe_load(f)
        for param in self._calibration:
            setattr(self, f"_{param}", self._calibration[param])
        calibration_complete = True
        for param in self.CALIB_ATTRS:
            if not hasattr(self, param):
                calibration_complete = False
                print(f"Calibration parameter {param[1:]} is missing.")
        if not calibration_complete:
            print("Calibration is incomplete.")

    def calibrate(self):
        ui.SpectrometerCalibrationInterface(self).cmdloop()
        # Esto no se hace pero por ahora lo resuelvo así. Cambiar
        self.load_calibration(self.calibration_path)

    def swipe_wavelengths(self,
                          starting_wavelength: float=None,
                          ending_wavelength: float=None,
                          wavelength_step: float=None,
                          ):
        if starting_wavelength is None:
            starting_wavelength = self.monochromator.min_wl
        if ending_wavelength is None:
            ending_wavelength = self.max_wl
        if wavelength_step is None:
            wavelength_step = self.wl_step_ratio

        n_measurements = int((ending_wavelength - starting_wavelength)/wavelength_step)
        for i in range(n_measurements):
            yield self.goto_wavelength(starting_wavelength + i * wavelength_step)

    def home(self, set_wavelength=True):
        steps_done = 0
        steps_limit = self.home_wavelength/self.wl_step_ratio
        while self.limit_switch.state and steps_done < abs(steps_limit):
            self._motor.rotate_step(1, not self._greater_wl_cw)
            steps_done += 1
        if set_wavelength:# and steps_done < steps_limit:
            self.set_wavelength(self.home_wavelength)
        elif steps_done >= abs(steps_limit):
            print("Danger warning:")
            print(f"Wavelength could not be set. Call home method again if and only if wavelength is greater than {self.home_wavelength}")
        

class Spectrometer(abstract.Spectrometer):

    def __init__(self, monochromator: Monochromator,
                  osc: OscilloscopeChannel,
                  lamp: Monochromator,
                  monochromator_calibration_path = None,
                  lamp_calibration_path = None,
                  conn = None):
        self.monochromator = monochromator
        self._osc = osc
        self.lamp = lamp
        if monochromator_calibration_path:
            self.monochromator.load_calibration(monochromator_calibration_path)
        if lamp_calibration_path:
            self.lamp.load_calibration(lamp_calibration_path)


    @classmethod
    def constructor_default(cls, conn = None, MONOCHROMATOR=Monochromator,
                             OSCILLOSCOPE_CHANNEL=OscilloscopeChannel):
        while not conn:
            try:
                conn = rpyc.connect('rp-f05512.local', port=18861)
            except Exception as e:
                print(e)
                print("Connection to 'rp-f05512.local' at port 18861")
        monochromator = MONOCHROMATOR.constructor_default(conn,
                        pin_step=4, pin_direction=5, limit_switch=3)
        osc = OSCILLOSCOPE_CHANNEL(conn, channel=0, voltage_range=20.0,
                        decimation=1, trigger_post=None, trigger_pre=0)
        lamp = MONOCHROMATOR.constructor_default(conn,
                        pin_step=6, pin_direction=7, limit_switch=2)
        common_path = '/home/tomi/Documents/facultad/tesis/horibaPTI-controller'
        lamp_calibration_path = f'{common_path}/excitation_calibration.yaml'
        monochromator_calibration_path = f'{common_path}/emission_calibration.yaml'
        return cls(monochromator, osc, lamp,
                   lamp_calibration_path=lamp_calibration_path,
                   monochromator_calibration_path=monochromator_calibration_path)

    # Esto se hace o directamente dejo el self.monochromator.goto_wavelength?
    def goto_wavelength(self, wavelength):
        return self.monochromator.goto_wavelength(wavelength)
    
    def goto_excitation_wavelength(self, wavelength):
        return self.lamp.goto_wavelength(wavelength)

    def get_emission(self, integration_time: float, excitation_wavelength: float = None,
                     iterator: bool = False, **kwargs):
        if excitation_wavelength:
            self.lamp.goto_wavelength(excitation_wavelength)
        spectrum_iterator  = self._get_spectrum(monochromator=self.monochromator,
                                                integration_time=integration_time,
                                                **kwargs)
        if iterator:
            return spectrum_iterator
        else:
            last_df = None
            for df in spectrum_iterator:
                last_df = df
            return last_df

    def get_excitation(self, integration_time: float, emission_wavelength: float = None,
                       iterator: bool = False, **kwargs):
        if emission_wavelength:
            self.monochromator.goto_wavelength(emission_wavelength)
        spectrum_iterator = self._get_spectrum(monochromator=self.lamp,
                                                integration_time=integration_time,
                                                **kwargs)
        if iterator:
            return spectrum_iterator
        else:
            last_df = None
            for df in spectrum_iterator:
                last_df = df
            return last_df

    def _get_spectrum(self,
                     monochromator: Monochromator,
                     integration_time: float,
                     starting_wavelength: float = None,
                     ending_wavelength: float = None,
                     wavelength_step: float = None,
                     rounds: int = 1
                     ):
        n_measurements = int((ending_wavelength - starting_wavelength)/wavelength_step)
        data = pd.DataFrame({
            "wavelength":[0.0]*n_measurements,
            "counts":[0]*n_measurements,
            "integration time":[0.0]*n_measurements
            })
        for i, wl in enumerate(monochromator.swipe_wavelengths(
            starting_wavelength=starting_wavelength,
            ending_wavelength=ending_wavelength,
            wavelength_step=wavelength_step)):
            photons, time_measured = self.get_intensity(integration_time, rounds)
            data.at[i, "wavelength"] = wl
            data.at[i, "counts"] = photons
            data.at[i, "integration time"] = time_measured
            yield data

    def get_intensity(self, seconds, rounds: int = 1):
        intensity_accum = 0
        intensity_squared_accum = 0
        # Este loop sería ideal que esté lo más cerca de la RP posible
        # el problema es que igual no podemos medir de forma continua ahora
        # así que da igual un delay de 10ms con uno de 100ms. 
        #times = np.linspace(0, seconds, self._osc.amount_datapoints)
        photons = 0
        for _ in range(rounds):
            photons += self.integrate(seconds)
        time_measured = rounds * self._osc.amount_datapoints/self._osc.sampling_rate
        return photons, time_measured

    def integrate(self, seconds):
        self._osc.set_measurement_time(seconds)
        osc_screen = np.array(self._osc.measure())
        return self._count_photons(osc_screen)
    
    # Esto tiene que contar fotones cuando lo calibre bien
    def _count_photons(self, osc_screen):
        # La altura hay que calibrarla
        times, heights = self._find_signal_peaks(-osc_screen, -3.5, 1)
        return len(times)

    def _find_signal_peaks(self, osc_screen, min_height, max_heigth):
        return sp.signal.find_peaks(osc_screen, height=(min_height,max_heigth))

    def set_wavelength(self, wavelength: float):
        return self.monochromator.set_wavelength(wavelength)

    def set_excitation_wavelength(self, wavelength: float):
        return self.lamp.set_wavelength(wavelength)

    def home(self):
        self.lamp.home()
        self.monochromator.home()
        print(f"Lamp wavelength should be {self.lamp.home_wavelength}")
        print(f"Monochromator wavelength should be {self.monochromator.home_wavelength}")
        print(f"If they are wrong, set them with spec.lamp.set_wavelength() and spec.monochromator.set_wavelength()")

    @property
    def decay_configuration(self):
        if self._osc.channel == 0 and self._osc.trig_src == 8:
            state = True
        elif self._osc.channel == 1 and self._osc.trig_src == 4:
            state = True
        else:
            state = False
        return state

    @decay_configuration.setter
    def decay_configuration(self, switch):
        # Poner en calibracion o hacer funcion de auto calibracion
        self._osc.decimation = 0
        self._osc.trigger_pre = 0
        self._osc.trigger_post = self._osc.buffer_size
        if switch:
            # todo esto va en la configuración de calibracion (los números)
            self._osc.set_trigger(channel=1,
                                 edge='pos', level=[0.4, 0.5])
        else:
            self._osc.set_trigger(channel=None)
    
    def aquire_decay(self, amount_windows=1, amount_buffers=1):
        self.decay_configuration = True
        counts = np.array([])
        for window in range(amount_windows):
            buff_offset = window * self._osc.amount_datapoints
            for _ in range(amount_buffers):
                screen = np.array(self._osc.get_triggered())
                # Aca también, cambiar los números por calibracion/configuracion
                peak_positions, _ = self._find_signal_peaks(screen, 0.16, 0.18)
                times = (peak_positions + buff_offset) / self._osc.sampling_rate
                counts = np.hstack((counts, times))
        return counts    
