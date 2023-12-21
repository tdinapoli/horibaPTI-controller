# rp-decay

The objective of the files in this directory is to perform an experiment that will be able to auto-calibrate the RedPitaya photon counting protocol.
To achieve this the RP is set to both acquire pulses from analog IN1 and a trigger signal from analog IN2, and also to send ttl pulses from digital pins n1 and n7.
The ttl pulse from n7 is ment to be a trigger signal and goes directly connected to IN2.
On the other hand, n1 sends exponentially time-distributed pulses from the moment the trigger has been sent, with a lifetime $\tau$ and untill a final time $t_f$ that is configured in the rp-sever/rp_decay_standalone.py file.

## How to acquire the data

To acquire the data, both ```__init__.py``` and rp_decay_standalone.py files have to be running on the RP.
The former opens the server to access the RP oscilloscope and the latter starts the exponentially distributed pulse simulation.
In the rp_decay_standalone.py file you configure the ```lifetime```, simulation ```length``` and maximum ```amount``` of the pulses sent in each simulation.
Every ```length``` seconds, the RP sends the trigger signal and then all the pulses whithin the ```length``` time window.

Once the server is running, the data acquisition from the client side can be run with the ```acquisition.ipynb``` notebook in the ```calibration/rp_decay``` folder.

## Analysis

The analysis of the acquired data can be done with the ```analysis.ipynb``` notebook.
The analysis notebook consists on several steps:
1. Loading of the data: both oscilloscope screens and time data from a path string.
1. Plotting of all osciloscope screens.
1. Counting the peaks by taking the derivative of the signal and detecting when that derivative exceeds a certain threshold.
1. Calculating the histogram: since each bin has been measured a different amount of times, each frequency of each bin of the histogram made with numpy histogram is then normalized for the amount of times that bin has been measured.
This is done by dividing by the output of ```calc_normalization_factor```, which outputs the amount of times the bin with left edge $t_l$ and right edge $t_r$ has bin measured by inputting the time $t$ of the bin edges.
For some bins, a time $t_{change}$ lies in the middle of them, where for $t < t_{change}$ and $t > t_{change}$ the bin has been measured a different amount of times.
The correction $f'$ for the frequency $f$ of those bins is the following $f' = f / [F_l (t_{change} - t_l)/(t_r - t_l) + F_r (1 -(t_{change} - t_l))/(t_r - t_l)]$. A binomial erorr is assigned to each bin.
1. Plotting the histogram and erorrbars.
1. Fit exponential an lineal.
1. Plot histogram heights and fit.

