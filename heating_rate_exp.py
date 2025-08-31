from artiq.language.core import kernel, delay, delay_mu, parallel
#from artiq.language.types import TInt32
import include.base_experiment
import include.std_data
#from dax.util.ccb import get_ccb_tool
from artiq.experiment import *
import numpy as np
#import time

tlist = [] #list of different delay times
loopcount = 10 #placeholder

class Heating_Rate(include.base_experiment.base_experiment):
    """
    Continuing from Norbert and Mika's codes.
    Using for my undergraduate thesis.

    TMK Fall 2025. Still untested.
    """

    """
    Initial testing starting Physics 495
    """


    # \/ \/ \/ \/ \/ \/ build \/ \/ \/ \/ \/ \/

    def build(self):
        self.setattr_device("core")
        self.setattr_device("ccb")

        self.setattr_argument("t_heat",
            NumberValue(default=0.1, unit="ms"))
        
        self.setattr_argument("bin_size",
            NumberValue(default=0.0001, ndecimals=0, step=1, unit="us"))
        
        self.setattr_argument("bin_num",
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
            for i in range(loopcount):
                self.set_dataset("Counts." + str(t) + "_" + str(i), np.full(self.bin_num, float(np.nan)), broadcast=True, archive=True)
        
        command = "${artiq_applet}plot_xy Counts"
        self.ccb.issue("create_applet", "Counts", command)
    
    # /\ /\ /\ /\ /\ /\ prepare /\ /\ /\ /\ /\ /\



    # \/ \/ \/ \/ \/ \/ run \/ \/ \/ \/ \/ \/

    def run(self):

        for rt in tlist:
            self.krun(rt)
            self.make_graphs(rt)
            self.reset()

        self.make_metadataset()
        print("Finished")


    @kernel
    def krun(self, kt):
        """
        Short for kernel run.
        Unlike the standard run(), which runs on the user's computer, krun() is run inside the device.
        It can do (almost) all of the same things run() can.
        It is an easier way to isolate the actual operation of the experiment (kernel-unique things) from generic operations such as initializing, resetting, or making graphs.
        """

        dev = self.cool_422
        dev_repump = self.repump_1092

        thiskrun_master = [0] * self.bin_num

        self.init()

        thiscount = 0
        while thiscount in range(loopcount):

            thisdb = "Counts." + str(kt) + "_" + str(thiscount)
            dev.sw.on()
            dev_repump.sw.on()
            delay(2*us)
            self.all_switch_off() #if possible later implement 1092 off as last laser/device off to ensure no ions are in the dark state

            delay(self.t_heat)

            self.ion_1092.sw.on()
            delay_mu(8)

            with parallel:
                gate_end_mu = self.pmt_counts.gate_rising(self.bin_size*s)
                self.cool_422.sw.on()
            
            t=0
            while t < self.bin_num:
                count = self.pmt_counts.count(gate_end_mu)
                self.mutate_dataset(thisdb, t, count)
                thiskrun_master[t] = thiskrun_master[t] + count

                t+=1
            
            thiscount+=1
        
        for masteritem in thiskrun_master:
            avgmaster = masteritem / loopcount
            self.mutate_dataset("Counts." + str(kt) + "_MASTER", thiskrun_master.index(masteritem), avgmaster)


#    @kernel
#    def analyze(self):


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
    
    @kernel
    def make_graphs(self, gt):
        for thist in tlist:
            thismaster = self.get_dataset("Counts." + str(thist) + "_MASTER") #I think this is an NDArray???
            if thismaster.shape[0] == 1:
                thislen = thismaster.shape[1]
                x_list = list(range(thislen)) * self.bin_size
                self.count_plot.make(x = x_list, y = thismaster.tolist(), title = "Fluorescence @" + str(gt) + "ms")
            else:
                print("Data output has bad shape, is a*n not 1*n.")
    # /\ /\ /\ /\ /\ /\ run /\ /\ /\ /\ /\ /\