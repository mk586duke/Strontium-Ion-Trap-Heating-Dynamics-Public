from artiq.language.core import kernel, delay, delay_mu, parallel
#from artiq.language.types import TInt32
import include.base_experiment
import include.std_data
#from dax.util.ccb import get_ccb_tool
from artiq.experiment import *
import numpy as np
#import time

tlist = [] #list of different delay times

class Heating_Rate(include.base_experiment.base_experiment):
    """
    Heating Rate Experiment
    Continuing from Norbert and Mika's codes.
    Using for my undergraduate thesis.
    """

    """
    Initial testing starting Physics 495
    TMK Fall 2025

    Test #2
    """


    # \/ \/ \/ \/ \/ \/ build \/ \/ \/ \/ \/ \/

    def build(self):
        self.setattr_device("core")
        self.setattr_device("ccb")
        
        self.setattr_argument("bin_size",
            NumberValue(default=0.0001, ndecimals=0, step=1, unit="us"))
        
        self.setattr_argument("bin_num",
            NumberValue(default=100, ndecimals=0, step=1))
        
        self.setattr_argument("loops",
            NumberValue(default=100, ndecimals=0, step=1))

        super().build()
    
    # /\ /\ /\ /\ /\ /\ build /\ /\ /\ /\ /\ /\



    # \/ \/ \/ \/ \/ \/ prepare \/ \/ \/ \/ \/ \/

    def prepare(self):
        super().prepare()

        self.count_plot = include.std_data.StdPlot(self, 
            name = "Heating_Counts_" + str(self.scheduler.rid))

        for t in tlist:
            self.set_dataset("Counts." + str(t) + "_MASTER", np.full(self.bin_num, float(np.nan)), broadcast=True, archive=True)
            for i in range(self.loops):
                self.set_dataset("Counts." + str(t) + "_" + str(i), np.full(self.bin_num, float(np.nan)), broadcast=True, archive=True)
        
        command = "${artiq_applet}plot_xy Counts"
        self.ccb.issue("create_applet", "Counts", command)
    
    # /\ /\ /\ /\ /\ /\ prepare /\ /\ /\ /\ /\ /\



    # \/ \/ \/ \/ \/ \/ run \/ \/ \/ \/ \/ \/

    def run(self):
        for rt in tlist:
            srt = str(rt)
            for thiscount in range(self.loops):
                thisdb = "Counts." + srt + "_" + str(thiscount)
                self.krun(rt, thisdb)
                self.reset()
    
            self.analyze(rt)
            self.make_graphs(rt)
        self.make_metadataset()
        print("Finished")

    def analyze(self, rt):
        tmaster = [0] * (self.bin_num)
        for i in range(self.loops):
            thisiter = self.get_dataset("Counts." + str(rt) + "_" + str(i))
            for j in range(self.bin_num):
                tmaster[j] = tmaster[j] + thisiter[j]

        for k in range(self.bin_num):
            avgmaster = (tmaster[k]) / (self.loops)
            self.mutate_dataset("Counts." + str(rt) + "_MASTER", k, avgmaster)


    def make_graphs(self, gt):
        thismaster = self.get_dataset("Counts." + str(gt) + "_MASTER") #I think this is an NDArray???
        if thismaster.shape[0] == 1:
            thislen = thismaster.shape[1]
            xraw = list(range(thislen))
            x_list = [i * (self.bin_size) for i in xraw]
            self.count_plot.make(x = x_list, y = thismaster.tolist(), title = "Fluorescence @" + str(gt) + "ms")
        else:
            print("Data output has bad shape, is a*n not 1*n.")



    @kernel
    def krun(self, kt, thisdb):
        """
        Short for kernel run.
        Unlike the standard run(), which runs on the user's computer, krun() is run inside the device.
        It can do (almost) all of the same things run() can.
        It is an easier way to isolate the operations of the experiment (kernel-unique things) from generic operations such as initializing, resetting, looping, or making graphs.
        """

        self.init()

        self.cool_422.sw.on()
        self.repump_1092.sw.on()
        delay(2*us)
        self.all_switch_off() #if possible later implement 1092 off as last laser/device off to ensure no ions are in the dark state

        delay(kt*ms)

        self.ion_1092.sw.on()
        delay_mu(8)

        with parallel:
            gate_end_mu = self.pmt_counts.gate_rising(self.bin_size*s)
            self.cool_422.sw.on()
        count = self.pmt_counts.count(gate_end_mu)
        self.mutate_dataset(thisdb, 0, count)

        t=1
        while t < self.bin_num:
            gate_end_mu = self.pmt_counts.gate_rising(self.bin_size*s)
            count = self.pmt_counts.count(gate_end_mu)
            self.mutate_dataset(thisdb, t, count)
            t+=1

    @kernel
    def init(self):
        self.core.reset()
        self.ttl_outputs_on()
        self.std_cool_ion(time = 100*us)
    
    @kernel
    def reset(self):
        self.core.break_realtime()
        #stop all actions
        self.all_switch_off() #urukul?
        #time reset
        self.std_cool_ion(leaveon=True)

    # /\ /\ /\ /\ /\ /\ run /\ /\ /\ /\ /\ /\