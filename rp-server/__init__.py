import rpyc
import time
from rp_decay import RPDecay
from rp_decay_hernan import MyThread
import time
import queue

#from redpitaya.overlay.mercury import mercury as FPGA
#gpio = FPGA
#signal_pin = gpio('n', 1, 'out')

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
                  trigger_post=None, trigger_pre=0,
                  sync_channels=True):

        self._osc_sync_num, self.osc = self.init_channel(osc, channel,
                                voltage_range, trigger_post, trigger_pre)
        self.sync_channels = sync_channels

        if sync_channels:
            self.alt_channel = (channel-1)%2
            self._alt_osc_sync_num, self.alt_osc = self.init_channel(osc,
                self.alt_channel, voltage_range, trigger_post,
                trigger_pre)
            self.alt_osc.sync_src = self._osc_sync_num

        self._channel = channel
        self._maximum_sampling_rate = 125e6

    def init_channel(self, osc, channel, voltage_range, trigger_post,
                     trigger_pre):
        if channel == 0:
            ch = osc(channel, voltage_range)
            sync_num = 2
        elif channel == 1:
            ch = osc(channel, voltage_range)
            sync_num = 3
        else:
            raise ValueError("Wrong channel number. Should be either 0 or 1")
        
        if trigger_post is None:
            ch.trigger_post = osc.buffer_size
        else:
            ch.trigger_post = trigger_post
        ch.trigger_pre = trigger_pre
        return sync_num, ch
        
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
        print(self.osc.level, self.alt_osc.level)
        print(self.osc.sync_src, self.alt_osc.sync_src)
        print(self.osc.trig_src, self.alt_osc.trig_src)
        print(self.osc.show_regset())
        self.osc.reset()
        self.osc.start()
        while self.osc.status_run():
            pass
        return self.osc.data(data_points)
    
    def exposed_set_trigger(self, channel, edge='pos', level=None):
        trig_src_dict = {'osc0':4, 'osc1':8, 'gen0':1, 'gen1':2,
                          'la':32, 'lg':16}
        self.osc.edge = edge
        if level is None:
            self.osc.level = [0.48, 0.5]
        else:
            print(level, self.osc.level)
            self.osc.level = level
        if channel is None:
            self.osc.trig_src = 0
        elif channel in (0, 1):
            trigger = "osc{channel}".format(channel=channel)
            self.osc.trig_src = trig_src_dict[trigger]
        elif channel in trig_src_dict.keys():
            self.osc.trig_src = trig_src_dict[channel]
        else:
            print("Setting channel", channel)
            self.osc.trig_src = channel
            #print("Channel must be either 0, 1 or None")

        if self.sync_channels:
            self.alt_osc.edge = edge
            self.alt_osc.level = self.osc.level
            self.alt_osc.trig_src = self.osc.trig_src

    def exposed_set_decimation(self, decimation_exponent):
        if decimation_exponent not in range(0, 18):
            print("Warning: decimation should be a power of 2 between 0 and 17, not", decimation_exponent)
        self.osc.decimation = 2**decimation_exponent
        if self.sync_channels:
            self.alt_osc.decimation = 2**decimation_exponent
    
    def exposed_set_trigger_pre(self, trigger_pre):
        self.osc.trigger_pre = int(trigger_pre)
        if self.sync_channels:
            self.alt_osc.trigger_pre = int(trigger_pre)

    def exposed_set_trigger_post(self, trigger_post):
        self.osc.trigger_post = int(trigger_post)
        if self.sync_channels:
            self.alt_osc.trigger_post = int(trigger_post)

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

    def exposed_edge(self):
        if self.sync_channels:
            return [self.osc.edge, self.alt_osc.edge]
        else:
            return self.osc.edge
    
    def exposed_set_edge(self, edge):
        if edge in ['pos', 'neg']:
            self.osc.edge = edge
        else:
            print("Wrong edge type")
            return
        if self.sync_channels:
            self.alt_osc.edge = edge

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
                                   decimation=1, trigger_post=None, trigger_pre=0,
                                   sync_channels=True):
        #try:
        #    osc_ch = getattr(self, "exposed_oscilloscope_ch{channel}".format(channel=channel))
        #    osc_ch.exposed_delete()
        #    print("Deleting oscilloscope channel {channel}".format(channel=channel))
        #    time.sleep(1)
        #except:
        #    pass

        oscilloscope_channel = OscilloscopeChannel(self.osc, channel, voltage_range,
                                                    trigger_post=trigger_post,
                                                    trigger_pre=trigger_pre,
                                                    sync_channels=sync_channels)
        setattr(self, "exposed_oscilloscope_ch{channel}".format(channel=channel),
                oscilloscope_channel)
        return oscilloscope_channel

    def exposed_create_lifetime_experiment(self, lifetime, amount, length):
        print("Creating lifetime experiment with new parameters")
        print("lifetime", lifetime)
        print("amount", amount)
        print("length", length)
        self.queue = queue.Queue()
        #self.rpdecay = MyThread(self.queue, self.gpio, lifetime, amount, length)
        self.rpdecay = RPDecay(self.gpio, self.queue, lifetime, amount, length)
        self.rpdecay.start()

if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True

    server = ThreadedServer(RPManager(), port=18861)
    server.start()

