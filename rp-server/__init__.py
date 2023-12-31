import rpyc
import time
from rp_decay import RPDecay
import time

class RPTTL:
    def __init__(self, state, pin, gpio):
        col, num = pin
        self._gpio = gpio(col, num, 'out')
        self.exposed_set_state(state)

    @property
    def exposed_state(self):
        return self._gpio.read()

    def exposed_set_state(self, state):
        self._gpio.write(state)

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
    def __init__(self, pin, gpio):
        col, num = pin
        self._gpio = gpio(col, num, 'in')

    @property
    def exposed_state(self):
        return self._gpio.read()

    def __str__(self):
        return str(self.state)

class OscilloscopeChannel:
    def __init__(self, osc, channel, voltage_range,
                  trigger_post=None, trigger_pre=0):
        self.osc = osc(channel, voltage_range)
        self._channel = channel
        if trigger_post is None:
            self.osc.trigger_post = self.osc.buffer_size
        else:
            self.osc.trigger_post = trigger_post
        self.osc.trigger_pre = trigger_pre
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

    def exposed_get_triggered(self, data_points=None):
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
        trig_src_dict = {'osc0':4, 'osc1':8}
        self.osc.edge = edge
        if level is None:
            level = [0.4, 0.5]
        if channel is None:
            self.osc.trig_src = 0
        elif channel in [0, 1]:
            trigger = "osc{channel}".format(channel=channel)
            self.osc.trig_src = trig_src_dict[trigger]
        else:
            print("Channel must be either 0, 1 or None")

    def exposed_set_decimation(self, decimation_exponent):
        if decimation_exponent not in range(0, 18):
            print("Warning: decimation should be a power of 2 between 0 and 17, not", decimation_exponent)
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
        from redpitaya.overlay.mercury import mercury as FPGA
        self.overlay = FPGA()
        self.gpio = FPGA.gpio
        self.osc = FPGA.osc
        self.exposed_ttls = {}
        self.rpdecay = None

    def on_connect(self, conn):
        print("RP Manager connected")

    def on_disconnect(self, conn):
        print("RP Manager disconnected")

    def exposed_create_RPTTL(self, name, config):
        state, pin = config[0], config[1:]
        ttl = RPTTL(state, pin, self.gpio)
        setattr(self, "exposed_{name}".format(name=name), ttl)
        return ttl

    def exposed_create_RPDI(self, name, pin):
        di = RPDI(pin, self.gpio)
        setattr(self, "exposed_{name}".format(name=name), di)
        return di

    def exposed_create_osc_channel(self, *, channel=None, voltage_range=None,
                                   decimation=1, trigger_post=None, trigger_pre=0):
        #try:
        #    osc_ch = getattr(self, "exposed_oscilloscope_ch{channel}".format(channel=channel))
        #    osc_ch.exposed_delete()
        #    print("Deleting oscilloscope channel {channel}".format(channel=channel))
        #    time.sleep(1)
        #except:
        #    pass

        oscilloscope_channel = OscilloscopeChannel(self.osc, channel, voltage_range,
                                                    trigger_post=trigger_post,
                                                    trigger_pre=trigger_pre)
        setattr(self, "exposed_oscilloscope_ch{channel}".format(channel=channel),
                oscilloscope_channel)
        return oscilloscope_channel

    def exposed_lifetime_experiment(self, lifetime, amount, length):
        self.rpdecay = RPDecay(self.gpio, lifetime, amount, length)
        print("starting worker...")
        self.rpdecay.start()

    def exposed_stop_lifetime_experiment(self):
        print("finish requested")
        self.rpdecay.finish_requested = True
        self.rpdecay.join()
        self.rpdecay = None

if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True

    server = ThreadedServer(RPManager(), port=18861)
    server.start()

