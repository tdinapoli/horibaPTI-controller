import rpyc
import time
import rp
import numpy as np

#from redpitaya.overlay.mercury import mercury as FPGA
#gpio = FPGA
#signal_pin = gpio('n', 1, 'out')

#RP_DIO0_N

class RPTTL:
    def __init__(self, state, pin):
        col, num = pin
        self.pin = getattr(rp, f"RP_DIO{num}_{col.upper()}")
        rp.rp_DpinSetDirection(self.pin, rp.RP_OUT)
        self.exposed_set_state(state)

    @property
    def exposed_state(self):
        return rp.rp_DpinGetState(self.pin)[-1]

    def exposed_set_state(self, state):
        rp.rp_DpinSetState(self.pin, bool(state))

    def exposed_toggle(self):
        self.exposed_set_state(not self.exposed_state)

    def exposed_pulse(self, ontime, offtime, amount=1):
        for _ in range(amount):
            self.exposed_toggle()
            time.sleep(ontime)
            self.exposed_toggle()
            time.sleep(offtime)

    def __str__(self):
        return str(self.state)

class RPDI:
    def __init__(self, pin):
        col, num = pin
        self.pin = getattr(rp, f"RP_DIO{num}_{col.upper()}")
        rp.rp_DpinSetDirection(self.pin, rp.RP_IN)

    @property
    def exposed_state(self):
        return rp.rp_DpinGetState(self.pin)[-1]

    def __str__(self):
        return str(self.state)

class RPOSC:
    def __init__(self, ch, gain, trigger_level = 0,
                 trig_dly = None, trig_src = None):

        self._GAINS_LOW = (1, 1.0, 'LV', 'lv')
        self._GAINS_HIGH = (20, 20.0, 'HV', 'hv')
        self._CHANNELS = (1,2)
        self._buffer_size = int(2**14)

        if ch not in self._CHANNELS:
            raise ValueError(f"Channel should be one of {self._CHANNELS}, not {ch}")
        self.ch = getattr(rp, f"RP_CH_{ch}")
        
        self.reset()

        if gain not in self._GAINS_LOW + self._GAINS_HIGH:
            raise ValueError(f"Gain should be one of {self._GAINS_LOW + self._GAINS_HIGH}, not {ch}")
        elif gain in self._GAINS_HIGH:
            self.gain = rp.RP_GAIN_5X
        elif gain in self._GAINS_LOW:
            self.gain = rp.RP_GAIN_1X
        else:
            raise Exception

        rp.rp_AcqSetGain(self.ch, self.gain)

        rp.rp_AcqSetTriggerLevel(rp.RP_T_CH_1, trigger_level)

        if trig_dly is None:
            self.trig_dly = self.buffer_size//2 
        else:
            self.trig_dly = trig_dly
        rp.rp_AcqSetTriggerDelay(self.trig_dly)

        if trig_src is None:
            self.trig_src = getattr(rp, f"RP_TRIG_SRC_CHA_PE")

    # The relation between trigger_pre, trigger_post, trig and
    # trig_dly assumes the following equations are true:
    # N = buffer_size
    # trigger_pre + trigger_post = N
    # trig = N//2 - trig_dly
    # trigger_post = N - trig
    @property
    def trigger_pre(self):
        return self.buffer_size - self.trigger_post

    @trigger_pre.setter
    def trigger_pre(self, val):
        self.trigger_post = self.buffer_size - val
    
    @property
    def trigger_post(self):
        return self.buffer_size - self.trig

    @trigger_post.setter
    def trigger_post(self, val):
        self.trig = self.buffer_size - val

    @property
    def trig_dly(self):
        return rp.rp_AcqGetTriggerDelay()[-1]

    @trig_dly.setter
    def trig_dly(self, dly):
        rp.rp_AcqSetTriggerDelay(dly)

    @property
    def trig(self):
        return self._buffer_size - self.trig_dly
    
    @trig.setter
    def trig(self, val):
        self.trig_dly = self.buffer_size//2 - val

    @property
    def buffer_size(self):
        return self._buffer_size

    def reset(self):
        rp.rp_AcqReset()

    def start(self):
        rp.rp_AcqStart()

    def trigger(self):
        rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_NOW)

    def status_run(self):
        return rp.rp_AcqGetTriggerState()[1] != rp.RP_TRIG_STATE_TRIGGERED

    def data(self, amount_datapoints = None):
        if amount_datapoints is None:
            amount_datapoints = self.buffer_size
        fbuff = rp.fBuffer(self.buffer_size)
        return np.fromiter(fbuff, dtype=float, count=self.buffer_size)[:amount_datapoints]

    @property
    def level(self):
        return rp.rp_AcqGetTriggerLevel(self.ch)[-1]
    
    def level(self, new_level):
        rp.rp_AcqSetTriggerLevel(self.ch, new_level)

    @property
    def trig_src(self):
        return self._trig_src
    
    @trig_src.setter
    def trig_src(self, trig_src):
        rp.rp_AcqSetTriggerSrc(trig_src)
        self._trig_src = trig_src

    @property
    def decimation(self):
        return 2**rp.rp_AcqGetDecimation()[-1]
    
    @decimation.setter
    def decimation(self, dec):
        dec = getattr(rp, f"RP_DEC_{int(dec)}")
        return rp.rp_AcqSetDecimation(dec)


class OscilloscopeChannel:
    def __init__(self, osc, channel, voltage_range,
                  trigger_post=None, trigger_pre=0):

        self.osc = osc(channel, voltage_range)
        if trigger_post is None:
            self.osc.trigger_post = self.osc.buffer_size
        else:
            self.osc.trigger_post = trigger_post

        self.osc.trigger_pre = trigger_pre

        self._channel = channel
        self._maximum_sampling_rate = 125e6

    def exposed_measure(self, data_points=None, transit_seconds=0):
        if data_points is None:
            data_points = self.osc.buffer_size
        if data_points > self.osc.buffer_size:
            print("Warning: the amount of data points {data_points} asked for is greater than the buffer size".format(data_points=data_points))
        self.osc.reset()
        self.osc.start()
        time.sleep(transit_seconds)
        # acá probablemente tenga que agregar un sleep o algo así pq
        # Si trigger_pre es >0 debería dejar al osciloscopio correr un rato
        # Antes de apretar el trigger para que tome datos.
        time.sleep(self.osc.trigger_pre * self.osc.decimation / self._maximum_sampling_rate)
        self.osc.trigger()
        while (self.osc.status_run()):
            pass
        return self.osc.data(data_points)

    #def get_triggered_itc(self):
    #    self.osc.reset()
    #    self.osc.start()
    #    while self.osc.status_run():
    #        time.sleep(0.1)
    #        signal_pin.write(True)
    #        time.sleep(0.1)
    #        signal_pin.write(False)
    #    return self.osc.data(self.osc.buffer_size)

    def exposed_get_triggered(self, data_points=None, itc=False):
        #if itc:
        #    return self.get_triggered_itc()
        if data_points is None:
            data_points = self.osc.buffer_size
        if data_points > self.osc.buffer_size:
            print("Warning: the amount of data points {data_points} asked for is greater than the buffer size".format(data_points=data_points))
        self.osc.reset()
        self.osc.start()
        while self.osc.status_run():
            pass
        return self.osc.data(data_points)
    
    def exposed_set_trigger(self, channel, edge='pos', level=None):
        trig_src_dict = {(1, 'pos'):rp.RP_TRIG_SRC_CHA_PE,
                         (1, 'neg'):rp.RP_TRIG_SRC_CHA_NE,
                         (2, 'pos'):rp.RP_TRIG_SRC_CHB_PE,
                         (2, 'neg'):rp.RP_TRIG_SRC_CHB_NE,
                         (3, 'pos'):rp.RP_TRIG_SRC_EXT_PE,
                         (3, 'neg'):rp.RP_TRIG_SRC_EXT_NE
                         }
        if level is None:
            self.osc.level = 0.5
        else:
            self.osc.level = level

        if channel is None:
            self.osc.trig_src = trig_src_dict[(1, 'pos')]
        elif channel in (1, 2, 3):
            trigger = (channel, edge)
            self.osc.trig_src = trig_src_dict[trigger]
        elif channel in trig_src_dict.keys():
            self.osc.trig_src = trig_src_dict[channel]
        else:
            print("Wrong channel")


    def exposed_set_decimation(self, decimation_exponent):
        if decimation_exponent not in range(0, 18):
            raise ValueError(f"Decimation exponent should be in range(0, 18), not {decimation_exponent}")
        self.osc.decimation = 2**decimation_exponent
    
    def exposed_set_trigger_pre(self, trigger_pre):
        self.osc.trigger_pre = int(trigger_pre)

    def exposed_set_trigger_post(self, trigger_post):
        self.osc.trigger_post = int(trigger_post)

    def exposed_decimation(self):
        return self.osc.decimation

    def exposed_buffer_size(self):
        return self.osc.buffer_size

    def exposed_trigger_pre(self):
        return self.osc.trigger_pre
    
    def exposed_trigger_post(self):
        return self.osc.trigger_post

    def exposed_decimation(self):
        return self.osc.decimation

    def exposed_buffer_size(self):
        return self.osc.buffer_size

    def exposed_trig_src(self):
        return self.osc.trig_src
    
    def exposed_channel(self):
        return self._channel

    # Esto tira algún tipo de warning que después 
    # Tengo que ver qué significa
    # Pero por ahora parece que funciona
    def exposed_delete(self):
        del self.osc

class RPManager(rpyc.Service):
    def __init__(self):
        rp.rp_Init()
        self.exposed_ttls = {}
        self.osc = RPOSC

    def on_connect(self, conn):
        print("RP Manager connected")

    def on_disconnect(self, conn):
        print("RP Manager disconnected")

    def exposed_create_RPTTL(self, name, config):
        state, pin = config[0], config[1:]
        ttl = RPTTL(state, pin)
        setattr(self, "exposed_{name}".format(name=name), ttl)
        return ttl

    def exposed_create_RPDI(self, name, pin):
        di = RPDI(pin, self.gpio)
        setattr(self, "exposed_{name}".format(name=name), di)
        return di

    def exposed_create_osc_channel(self, *, channel=None, voltage_range=None,
                                   decimation=1, trigger_post=None, trigger_pre=0):

        oscilloscope_channel = OscilloscopeChannel(self.osc, channel, voltage_range,
                                                    trigger_post=trigger_post,
                                                    trigger_pre=trigger_pre)
        setattr(self, "exposed_oscilloscope_ch{channel}".format(channel=channel),
                oscilloscope_channel)
        return oscilloscope_channel


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True

    server = ThreadedServer(RPManager(), port=18861)
    server.start()

