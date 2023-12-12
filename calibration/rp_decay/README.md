# rp-decay

The objective of the files in this directory is to perform an experiment that will be able to auto-calibrate the RedPitaya photon counting protocol.
To achieve this the RP is set to both acquire pulses from analog IN1 and a trigger signal from analog IN2, and also to send ttl pulses from digital pins n1 and n7.
The ttl pulse from n7 is ment to be the trigger signal and goes directly connected to IN2.
On the other hand, n1 sends exponentially time-distributed pulses from the moment the trigger has been sent, with a lifetime $\tau$ and untill a final time $t_f$ that is configured in the rp-sever/rp_decay_standalone.py file.

## How to acquire the data

To acquire the data, both __init__.py and rp_decay_standalone.py files have to be running on the RP.
The former opens the server to access the RP oscilloscope and the latter starts the exponentially distributed pulse simulation.
In the rp_decay_standalone.py file you configure the ```lifetime```, simulation ```length``` and maximum ```amount``` of pulses sent in each simulation.
Every ```length``` seconds, the RP sends the trigger signal and then all the pulses whithin the ```length``` time window.

Once the server is running, the data acquisition from the client side can be run with the ```acquisition.ipynb``` notebook in the ```calibration/rp_decay``` folder.

