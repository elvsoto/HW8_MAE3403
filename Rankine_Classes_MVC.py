#region imports
import math
from Calc_state import *
from UnitConversions import UnitConverter as UC
import numpy as np
from matplotlib import pyplot as plt
from copy import deepcopy as dc
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from Rankine_GUI import Ui_Form  # This assumes that your PyQt5 UI class is in a file named Rankine_GUI.py.

#these imports are necessary for drawing a matplot lib graph on my GUI
#no simple widget for this exists in QT Designer, so I have to add the widget in code.
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
#endregion

#region class definitions
class rankineModel():
    def __init__(self):
        '''
        Constructor for rankine power cycle data (in the Model-View-Controller design pattern).  This class
        is for storing data only.  The Controller class should update the model depending on input from the user.
        The View class should display the model data depending on the desired output.
        :param p_low: the low pressure isobar for the cycle in kPa
        :param p_high: the high pressure isobar for the cycle in kPa
        :param t_high: optional temperature for State1 (turbine inlet) in degrees C
        :param eff_turbine: isentropic efficiency of the turbine
        :param name: a convenient name
        '''
        self.p_low=None
        self.p_high=None
        self.t_high=None
        self.name=None
        self.efficiency=None
        self.turbine_eff=None
        self.turbine_work=None
        self.pump_work=None
        self.heat_added=None
        self.steam=Steam_SI()  # Instantiate a steam object for calculating state
        # Initialize the states as stateProps objects (i.e., stateProperties)
        self.state1 = stateProps()
        self.state2s = stateProps()
        self.state2 = stateProps()
        self.state3 = stateProps()
        self.state4 = stateProps()
        self.SI=True  # If False, convert pressures from psi to kPa and T from F to C for inputs
        #the following are a place to store data for plotting
        self.satLiqPlotData = StateDataForPlotting()
        self.satVapPlotData = StateDataForPlotting()
        self.upperCurve = StateDataForPlotting()
        self.lowerCurve = StateDataForPlotting()

    def buildVaporDomeData(self, nPoints=500):
        """
        Populates the model with data points along the saturated liquid and vapor lines.
        Assumes self.steam is an instance of Steam_SI or a similar class.
        """

        steam = self.steam  # Assuming steam is a Steam_SI object initialized in the model
        tp = triplePt_PT()  # Make sure this function or class is defined and returns the triple point
        cp = criticalPt_PT()  # Make sure this function or class is defined and returns the critical point

        if not hasattr(self, 'steam') or self.steam is None:
            print("Steam property calculator not initialized.")
            return

        # Assuming triplePt_PT and criticalPt_PT return triple point and critical point data respectively
        tp = triplePt_PT()
        cp = criticalPt_PT()

        # Generate pressures from just above the triple point to just below the critical point
        pressures = np.logspace(np.log10(tp.p * 1.001), np.log10(cp.p * 0.99), nPoints)

        # Reset or initialize storage for vapor dome data
        self.satLiqPlotData = StateDataForPlotting()
        self.satVapPlotData = StateDataForPlotting()

        # Loop over each pressure, calculate saturated properties, and store them
        for p in pressures:
            satLiq = self.steam.getState(P=p, x=0.0)  # Saturated liquid
            satVap = self.steam.getState(P=p, x=1.0)  # Saturated vapor

            self.satLiqPlotData.addPt((satLiq.t, satLiq.p, satLiq.u, satLiq.h, satLiq.s, satLiq.v))
            self.satVapPlotData.addPt((satVap.t, satVap.p, satVap.u, satVap.h, satVap.s, satVap.v))

        # Critical point (assumes critProps is a stateProps object or similar with critical state properties)
        critProps = self.steam.getState(P=cp.p)  # Or however you obtain critical point properties
        self.satLiqPlotData.addPt((critProps.t, critProps.p, critProps.u, critProps.h, critProps.s, critProps.v))
        self.satVapPlotData.addPt((critProps.t, critProps.p, critProps.u, critProps.h, critProps.s, critProps.v))

        print("Vapor dome data built successfully.")


class rankineView():
    def __init__(self):
        """
        Empty constructor by design
        """

    def setWidgets(self, *args):
        #create class variables for the input widgets
        self.rb_SI, self.le_PHigh, self.le_PLow, self.le_TurbineInletCondition, self.rdo_Quality, self.le_TurbineEff, self.cmb_XAxis, self.cmb_YAxis, self.chk_logX, self.chk_logY=args[0]
        #create class variables for the display widgets
        self.lbl_PHigh, self.lbl_PLow, self.lbl_SatPropLow,self.lbl_SatPropHigh, self.lbl_TurbineInletCondition, self.lbl_H1, self.lbl_H1Units, self.lbl_H2, self.lbl_H2Units, self.lbl_H3, self.lbl_H3Units, self.lbl_H4, self.lbl_H4Units, self.lbl_TurbineWork, self.lbl_TurbineWorkUnits, self.lbl_PumpWork, self.lbl_PumpWorkUnits, self.lbl_HeatAdded, self.lbl_HeatAddedUnits, self.lbl_ThermalEfficiency, self.canvas, self.figure, self.ax=args[1]

    def selectQualityOrTHigh(self, Model=None):
        """
        Action to take when selecting one of the radio buttons for Quality or THigh
        :return:
        """
        # region Code for P1.1
        SI = self.rb_SI.isChecked()
        if self.rdo_Quality.isChecked():
            self.le_TurbineInletCondition.setText("1.0")
            self.le_TurbineInletCondition.setEnabled(False)
        else:
            PCF = 1 if SI else UC.psi_to_bar
            satPHigh = Model.steam.getsatProps_p(float(self.le_PHigh.text() * PCF))
            Tsat = satPHigh.tsat
            Tsat = Tsat if SI else UC.C_to_F(Tsat)
            CurrentT = float(self.le_TurbineInletCondition.text())
            CurrentT = max(CurrentT, Tsat)
            self.le_TurbineInletCondition.setText("{:0.2f}".format(CurrentT))
            self.le_TurbineInletCondition.setEnabled(True)
        # endregion
        x = self.rdo_Quality.isChecked()
        self.lbl_TurbineInletCondition.setText(
            ("Turbine Inlet: {}{} =".format('x' if x else 'THigh', '' if x else ('(C)' if SI else '(F)'))))

    def setNewPHigh(self, Model=None):
        """
                 This function checks the self.rb_SI.isChecked() to see which units are used.
                 Then, it sets the text of lbl_SatPropHigh using SatPropsIsobar(float(self.le_PHigh.text())*PCF, SI=SI).txtOut
                 here, PCF is the pressure conversion factor
                 finally, we need to call the function self.SelectQualityOrTHigh()
                 :return:
                 """
        SI = self.rb_SI.isChecked()
        PCF = 1 if SI else UC.psi_to_bar
        satProp = Model.steam.getsatProps_p(float(self.le_PHigh.text()) * PCF)
        self.lbl_SatPropHigh.setText(satProp.getTextOutput(SI=SI))
        self.SelectQualityOrTHigh(Model)

    def setNewPLow(self, Model=None):
        SI = self.rb_SI.isChecked()
        PCF = 1 if SI else UC.psi_to_bar
        satProp = Model.steam.getsatProps_p(float(self.le_PLow.text()) * PCF)
        self.lbl_SatPropLow.setText(satProp.getTextOutput(SI=SI))

    def outputToGUI(self, Model=None):
        #unpack the args
        if Model.state1 is None:  # means the cycle has not been evaluated yet
            return
        #update the line edits and labels
        HCF=1 if Model.SI else UC.kJperkg_to_BTUperlb # Enthalpy conversion factor (HCF)
        self.lbl_H1.setText("{:0.2f}".format(Model.state1.h * HCF))
        self.lbl_H2.setText("{:0.2f}".format(Model.state2.h * HCF))
        self.lbl_H3.setText("{:0.2f}".format(Model.state3.h * HCF))
        self.lbl_H4.setText("{:0.2f}".format(Model.state4.h * HCF))
        self.lbl_TurbineWork.setText("{:0.2f}".format(Model.turbine_work*HCF))
        self.lbl_PumpWork.setText("{:0.2f}".format(Model.pump_work*HCF))
        self.lbl_HeatAdded.setText("{:0.2f}".format(Model.heat_added*HCF))
        self.lbl_ThermalEfficiency.setText("{:0.2f}".format(Model.efficiency))
        satPropsLow=Model.steam.getsatProps_p(p=Model.p_low)
        satPropsHigh=Model.steam.getsatProps_p(p=Model.p_high)
        self.lbl_SatPropLow.setText(satPropsLow.getTextOutput(SI=Model.SI))
        self.lbl_SatPropHigh.setText(satPropsHigh.getTextOutput(SI=Model.SI))



        #update the plot
        self.plot_cycle_XY(Model=Model)

    def updateUnits(self, Model=None):
        """
        Updates the units on the GUI to match choice of SI or English
        :param Model:  a reference to the model
        :return:
        """
        #Step 0. update the outputs
        self.outputToGUI(Model=Model)
        # Update units displayed on labels
        #Step 1. Update pressures for PHigh and PLow
        pCF=1 if Model.SI else UC.bar_to_psi
        self.le_PHigh.setText("{:0.2f}".format(pCF * Model.p_high))
        self.le_PLow.setText("{:0.2f}".format(pCF * Model.p_low))
        #Step 2. Update THigh if it is not None
        if not self.rdo_Quality.isChecked():
            T=float(self.le_TurbineInletCondition.text())
            T = UC.F_to_C(T) if Model.SI else UC.C_to_F(T)
            TUnits = "C" if Model.SI else "F"
            self.le_TurbineInletCondition.setText("{:0.2f}".format(T))
            self.lbl_TurbineInletCondition.setText("Turbine Inlet: THigh ({}):".format(TUnits))
        #Step 3. Update the units for labels
        self.lbl_PHigh.setText("P High ({})".format('bar' if Model.SI else 'psi'))
        self.lbl_PLow.setText("P Low ({})".format('bar' if Model.SI else 'psi'))
        HUnits="kJ/kg" if Model.SI else "BTU/lb"
        self.lbl_H1Units.setText(HUnits)
        self.lbl_H2Units.setText(HUnits)
        self.lbl_H3Units.setText(HUnits)
        self.lbl_H4Units.setText(HUnits)
        self.lbl_TurbineWorkUnits.setText(HUnits)
        self.lbl_PumpWorkUnits.setText(HUnits)
        self.lbl_HeatAddedUnits.setText(HUnits)

    def print_summary(self, Model=None):
        """
        Prints to CLI.
        :param Model: a rankineModel object
        :return: nothing
        """
        if Model.efficiency==None:
            Model.calc_efficiency()
        print('Cycle Summary for: ', Model.name)
        print('\tEfficiency: {:0.3f}%'.format(Model.efficiency))
        print('\tTurbine Eff:  {:0.2f}'.format(Model.turbine_eff))
        print('\tTurbine Work: {:0.3f} kJ/kg'.format(Model.turbine_work))
        print('\tPump Work: {:0.3f} kJ/kg'.format(Model.pump_work))
        print('\tHeat Added: {:0.3f} kJ/kg'.format(Model.heat_added))
        Model.state1.print()
        Model.state2.print()
        Model.state3.print()
        Model.state4.print()

    def plot_cycle_TS(self, axObj=None, Model=None):
        """
        I want to plot the Rankine cycle on T-S coordinates along with the vapor dome and shading in the cycle.
        I notice there are several lines on the plot:
        saturated liquid T(s) colored blue
        saturated vapor T(s) colored red
        The high and low isobars and lines connecting state 1 to 2, and 3 to saturated liquid at phigh
        step 1:  build data for saturated liquid line
        step 2:  build data for saturated vapor line
        step 3:  build data between state 3 and sat liquid at p_high
        step 4:  build data between sat liquid at p_high and state 1
        step 5:  build data between state 1 and state 2
        step 6:  build data between state 2 and state 3
        step 7:  put together data from 3,4,5 for top line and build bottom line
        step 8:  make and decorate plot

        Note:  will plot using pyplot if axObj is None else just returns

        :param axObj:  if None, used plt.subplot else a MatplotLib axes object.
        :return:
        """
        SI=Model.SI
        steam=Model.steam
        #region step 1&2:
        ts, ps, hfs, hgs, sfs, sgs, vfs, vgs = np.loadtxt('sat_water_table.txt', skiprows=1,
                                                          unpack=True)  # use np.loadtxt to read the saturated properties
        ax = plt.subplot() if axObj is None else axObj

        hCF = 1 if Model.SI else UC.kJperkg_to_BTUperlb
        pCF = 1 if Model.SI else UC.kpa_to_psi
        sCF = 1 if Model.SI else UC.kJperkgK_to_BTUperlbR
        vCF = 1 if Model.SI else UC.kgperm3_to_lbperft3

        sfs *= sCF
        sgs *= sCF
        hfs *= hCF
        hgs *= hCF
        vfs *= vCF
        vgs *= vCF
        ps *= pCF
        ts = [t if Model.SI else UC.C_to_F(t) for t in ts]

        xfsat = sfs
        yfsat = ts
        xgsat = sgs
        ygsat = ts

        ax.plot(xfsat, yfsat, color='blue')
        ax.plot(xgsat, ygsat, color='red')
        #endregion

        #step 3:  I'll just make a straight line between state3 and state3p
        st3p=steam.getState(Model.p_high,x=0) #saturated liquid state at p_high
        svals=np.linspace(Model.state3.s, st3p.s, 20)
        hvals=np.linspace(Model.state3.h, st3p.h, 20)
        pvals=np.linspace(Model.p_low, Model.p_high,20)
        vvals=np.linspace(Model.state3.v, st3p.v, 20)
        tvals=np.linspace(Model.state3.T, st3p.T, 20)
        line3=np.column_stack([svals, tvals])

        #step 4:
        sat_pHigh=steam.getState(Model.p_high, x=1.0)
        st1=Model.state1
        svals2p=np.linspace(st3p.s, sat_pHigh.s, 20)
        hvals2p = np.linspace(st3p.h, sat_pHigh.h, 20)
        pvals2p = [Model.p_high for i in range(20)]
        vvals2p = np.linspace(st3p.v, sat_pHigh.v, 20)
        tvals2p=[st3p.T for i in range(20)]
        line4=np.column_stack([svals2p, tvals2p])
        if st1.T>sat_pHigh.T:  #need to add data points to state1 for superheated
            svals_sh=np.linspace(sat_pHigh.s,st1.s, 20)
            tvals_sh=np.array([steam.getState(Model.p_high,s=ss).T for ss in svals_sh])
            line4 =np.append(line4, np.column_stack([svals_sh, tvals_sh]), axis=0)
        #plt.plot(line4[:,0], line4[:,1])

        #step 5:
        svals=np.linspace(Model.state1.s, Model.state2.s, 20)
        tvals=np.linspace(Model.state1.T, Model.state2.T, 20)
        line5=np.array(svals)
        line5=np.column_stack([line5, tvals])
        #plt.plot(line5[:,0], line5[:,1])

        #step 6:
        svals=np.linspace(Model.state2.s, Model.state3.s, 20)
        tvals=np.array([Model.state2.T for i in range(20)])
        line6=np.column_stack([svals, tvals])
        #plt.plot(line6[:,0], line6[:,1])

        #step 7:
        topLine=np.append(line3, line4, axis=0)
        topLine=np.append(topLine, line5, axis=0)
        xvals=topLine[:,0]
        y1=topLine[:,1]
        y2=[Model.state3.T for s in xvals]

        if not SI:
            xvals*=UC.kJperkgK_to_BTUperlbR
            for i in range(len(y1)):
                y1[i]=UC.C_to_F(y1[i])
            for i in range(len(y2)):
                y2[i]=UC.C_to_F(y2[i])

        ax.plot(xvals, y1, color='darkgreen')
        ax.plot(xvals, y2, color='black')
        # ax.fill_between(xvals, y1, y2, color='gray', alpha=0.5)

        if SI:
            ax.plot(Model.state1.s, Model.state1.T, marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state2.s, Model.state2.T, marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state3.s, Model.state3.T, marker='o', markeredgecolor='k', markerfacecolor='w')
        else:
            ax.plot(Model.state1.s * UC.kJperkgK_to_BTUperlbR, UC.C_to_F(Model.state1.T), marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state2.s * UC.kJperkgK_to_BTUperlbR, UC.C_to_F(Model.state2.T), marker='o', markeredgecolor='k', markerfacecolor='w')
            ax.plot(Model.state3.s * UC.kJperkgK_to_BTUperlbR, UC.C_to_F(Model.state3.T), marker='o', markeredgecolor='k', markerfacecolor='w')

        tempUnits=r'$\left(^oC\right)$' if SI else r'$\left(^oF\right)$'
        entropyUnits=r'$\left(\frac{kJ}{kg\cdot K}\right)$' if SI else r'$\left(\frac{BTU}{lb\cdot ^oR}\right)$'
        ax.set_xlabel(r's '+entropyUnits, fontsize=18)  #different than plt
        ax.set_ylabel(r'T '+tempUnits, fontsize=18)  #different than plt
        ax.set_title(Model.name)  #different than plt
        ax.grid(visible='both', alpha=0.5)
        ax.tick_params(axis='both', direction='in', labelsize=18)

        sMin=min(sfs)
        sMax=max(sgs)
        ax.set_xlim(sMin, sMax)  #different than plt

        tMin=min(ts)
        tMax=max(max(ts),st1.T)
        ax.set_ylim(tMin,tMax*1.05)  #different than plt

        energyUnits=r'$\frac{kJ}{kg}$' if SI else r'$\frac{BTU}{lb}$'
        energyCF = 1 if SI else UC.kJperkg_to_BTUperlb

        if axObj is None:  # this allows me to show plot if not being displayed on a figure
            plt.show()

    def plot_cycle_XY(self, Model=None):
        """
        I want to plot any two thermodynamic properties on X and Y
        """
        ax = self.ax
        X = self.cmb_XAxis.currentText()
        Y = self.cmb_YAxis.currentText()
        logx = self.chk_logX.isChecked()
        logy = self.chk_logY.isChecked()
        SI = Model.SI
        if X == Y:
            return

        QTPlotting = True  # assumes we are plotting onto a QT GUI form
        if ax is None:
            ax = plt.subplot()
            QTPlotting = False  # actually, we are just using CLI and showing the plot

        ax.clear()
        ax.set_xscale('log' if logx else 'linear')
        ax.set_yscale('log' if logy else 'linear')
        YF = Model.satLiqPlotData.getDataCol(Y, SI=SI)
        YG = Model.satVapPlotData.getDataCol(Y, SI=SI)
        XF = Model.satLiqPlotData.getDataCol(X, SI=SI)
        XG = Model.satVapPlotData.getDataCol(X, SI=SI)

        # Check if any of the sequences are empty to avoid "ValueError: min() arg is an empty sequence"
        print(f"XF Length: {len(XF)}, XG Length: {len(XG)}, YF Length: {len(YF)}, YG Length: {len(YG)}")

        # Check if any of the sequences are empty to avoid plotting errors
        if len(XF) == 0 or len(XG) == 0 or len(YF) == 0 or len(YG) == 0:
            print("Data is missing for plotting. Cannot plot graph.")
            return

        ax = self.ax  # Assuming 'self.ax' is the Axes object you're plotting on

        # Apply logarithmic scales if indicated
        if logx:  # Assuming 'logx' is a boolean indicating if X-axis should be log scale
            ax.set_xscale('log')
        if logy:  # Assuming 'logy' is a boolean indicating if Y-axis should be log scale
            ax.set_yscale('log')

        # plot the vapor dome
        ax.plot(XF, YF, color='b')
        ax.plot(XG, YG, color='r')
        # plot the upper and lower curves
        ax.plot(Model.lowerCurve.getDataCol(X, SI=SI), Model.lowerCurve.getDataCol(Y, SI=SI), color='k')
        ax.plot(Model.upperCurve.getDataCol(X, SI=SI), Model.upperCurve.getDataCol(Y, SI=SI), color='g')

        # add axis labels
        ax.set_ylabel(Model.lowerCurve.getAxisLabel(Y, SI=SI), fontsize='large' if QTPlotting else 'medium')
        ax.set_xlabel(Model.lowerCurve.getAxisLabel(X, SI=SI), fontsize='large' if QTPlotting else 'medium')
        # put a title on the plot
        Model.name = 'Rankine Cycle - ' + Model.state1.region + ' at Turbine Inlet'
        ax.set_title(Model.name, fontsize='large' if QTPlotting else 'medium')

        # modify the tick marks
        ax.tick_params(axis='both', which='both', direction='in', top=True, right=True,
                       labelsize='large' if QTPlotting else 'medium')

        # plot the circles for states 1, 2, 3, and 4
        ax.plot(Model.state1.getVal(X, SI=SI), Model.state1.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')
        ax.plot(Model.state2.getVal(X, SI=SI), Model.state2.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')
        ax.plot(Model.state3.getVal(X, SI=SI), Model.state3.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')
        ax.plot(Model.state4.getVal(X, SI=SI), Model.state4.getVal(Y, SI=SI), marker='o', markerfacecolor='w',
                markeredgecolor='k')

        # set limits on x and y after confirming data is not empty
        xmin = min(min(XF), min(XG), min(Model.upperCurve.getDataCol(X, SI=SI)))
        xmax = max(max(XF), max(XG), max(Model.upperCurve.getDataCol(X, SI=SI)))
        ymin = min(min(YF), min(YG), min(Model.upperCurve.getDataCol(Y, SI=SI)))
        ymax = max(max(YF), max(YG), max(Model.upperCurve.getDataCol(Y, SI=SI))) * 1.1
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)

        # show the plot
        if not QTPlotting:
            plt.show()
        else:
            self.canvas.draw()

    def getCycleData(self):
        # This method should return a list of dictionaries, each representing a state in the cycle
        # For demonstration, let's assume it returns hardcoded data
        return [
            {"p": 101.325, "t": 300, "h": 3000, "s": 6.5},  # State 1 example
            {"p": 0.1, "t": 50, "h": 2500, "s": 7.5},  # State 2 example
            # Add other states
        ]
    def SelectQualityOrTHigh(self, Model=None):
        """
        Handles the logic for when the user selects either a specific quality or a high temperature
        for the Rankine cycle's input. This could enable/disable input fields or change labels depending
        on the selection.
        """
        # Assuming you have a RadioButton or similar for quality and temperature selection:
        if self.rdo_Quality.isChecked():
            # If quality is selected, perhaps disable temperature input, or vice versa
            self.le_TurbineInletCondition.setDisabled(True)
            # Adjust label text or other UI elements as needed
            self.lbl_TurbineInletCondition.setText("Quality:")
        else:
            # If high temperature is selected, enable temperature input
            self.le_TurbineInletCondition.setEnabled(True)
            self.lbl_TurbineInletCondition.setText("T High (°C):")

        # Update the model or other view components as needed based on the selection
        # This might involve recalculating or redisplaying data


class rankineController():
    def __init__(self, inputWidgets, displayWidgets):
        """
        Create rankineModel object.  The rankineController class updates the model based on user input
        and updates the rankineView as well.
        :param inputWidgets: a list of widgets that are for user input
        :param displayWidgets: a list of widgets that are for display
        """
        # Initialize the model and view

        self.Model = rankineModel()
        self.View = rankineView()

        # Store the input and display widgets
        self.IW = inputWidgets  # an array of widgets that are for user input
        self.DW = displayWidgets  # an array of widgets that are for display

        # Inform the view about the widgets it needs to manage
        self.View.setWidgets(self.IW, self.DW)

        # Further initialization or method calls can go here if necessary
        self.Model.steam = Steam_SI()  # Ensure Steam_SI is correctly initialized
        self.Model.buildVaporDomeData()  # Build vapor dome data
    def updateModel(self):
        """
        I'm expecting a tuple of input widgets from the GUI.  Read and apply them here.
        :param args: a tuple of input widgets, other arguments such as SI or ENG
        :return: nothing
        """
        #read from the input widgets
        self.Model.SI=self.View.rb_SI.isChecked()

        #update the model
        #$UNITS$ since inputs can be SI or English, I need to convert to SI here for pressures and temperature
        PCF=1 if self.Model.SI else UC.psi_to_bar #$UNITS$ input is bar for SI and psi for English
        self.Model.p_high = float(self.View.le_PHigh.text()) * PCF  # get the high pressure isobar in kPa
        self.Model.p_low = float(self.View.le_PLow.text()) * PCF  # get the low pressure isobar in kPa
        T=float(self.View.le_TurbineInletCondition.text()) #$UNITS$
        self.Model.t_high = None if self.View.rdo_Quality.isChecked() else (T if self.Model.SI else UC.F_to_C(T)) #$UNITS$
        self.Model.turbine_eff = float(self.View.le_TurbineEff.text())
        #do the calculation
        self.calc_efficiency()  # Existing call to calculate cycle efficiency
        self.buildDataForPlotting()  # Ensure this is called right after calculations
        self.updateView()

    def updateUnits(self):
        #Switching units should not change the model, but should update the view
        self.Model.SI=self.View.rb_SI.isChecked()
        self.View.updateUnits(Model=self.Model)
        pass

    def selectQualityOrTHigh(self):
        self.View.selectQualityOrTHigh(self.Model)

    def setNewPHigh(self):
        self.View.setNewPHigh(self.Model)

    def setNewPLow(self):
        self.View.setNewPLow(self.Model)

    def calc_efficiency(self):
        """
        I've modified this on 4/15/2022 to use a single SI_Steam object that is held in the model for calculating
        various states along the path of the Rankine cycle.  I use the getState function to retrieve a deep copy of
        a stateProps object.
        :return:
        """
        steam=self.Model.steam

        # calculate the 4 states
        # state 1: turbine inlet (p_high, t_high) superheated or saturated vapor
        if (self.Model.t_high == None):
            self.Model.state1 = steam.getState(P=self.Model.p_high, x=1.0, name='Turbine Inlet')
        else:
            self.Model.state1 = steam.getState(P=self.Model.p_high, T=self.Model.t_high, name='Turbine Inlet')
        # state 2: turbine exit (p_low, s=s_turbine inlet) two-phase
        self.Model.state2s = steam.getState(P=self.Model.p_low, s=self.Model.state1.s, name="Turbine Exit")
        if self.Model.turbine_eff < 1.0:  # eff=(h1-h2)/(h1-h2s) -> h2=h1-eff(h1-h2s)
            h2 = self.Model.state1.h - self.Model.turbine_eff * (self.Model.state1.h - self.Model.state2s.h)
            self.Model.state2 = steam.getState(P=self.Model.p_low, h=h2, name="Turbine Exit")
        else:
            self.Model.state2 = self.Model.state2s
        # state 3: pump inlet (p_low, x=0) saturated liquid
        self.Model.state3 = steam.getState(P=self.Model.p_low, x=0, name='Pump Inlet')
        # state 4: pump exit (p_high,s=s_pump_inlet) typically sub-cooled, but estimate as saturated liquid
        self.Model.state4 = steam.getState(P=self.Model.p_high, s=self.Model.state3.s, name='Pump Exit')

        self.Model.turbine_work = self.Model.state1.h - self.Model.state2.h  # calculate turbine work
        self.Model.pump_work = self.Model.state4.h - self.Model.state3.h  # calculate pump work
        self.Model.heat_added = self.Model.state1.h - self.Model.state4.h  # calculate heat added
        self.Model.efficiency = 100.0 * (self.Model.turbine_work - self.Model.pump_work) / self.Model.heat_added
        return self.Model.efficiency

    def updateView(self):
        """
        This is a pass-through function that calls and identically named function in the View, but passes along the
        Model as an argument.
        :param args: A tuple of Widgets that get unpacked and updated in the view
        :return:
        """
        self.buildDataForPlotting()
        self.View.outputToGUI(Model=self.Model)

    def setRankine(self,p_low=8, p_high=8000, t_high=None, eff_turbine=1.0, name='Rankine Cycle'):
        '''
        Set model values for rankine power cycle.  If t_high is not specified, the State 1
        is assigned x=1 (saturated steam @ p_high).  Otherwise, use t_high to find State 1.
        :param p_low: the low pressure isobar for the cycle in kPa
        :param p_high: the high pressure isobar for the cycle in kPa
        :param t_high: optional temperature for State1 (turbine inlet) in degrees C
        :param eff_turbine: isentropic efficiency of the turbine
        :param name: a convenient name
        '''
        self.Model.p_low=p_low
        self.Model.p_high=p_high
        self.Model.t_high=t_high
        self.Model.name=name
        self.Model.efficiency=None
        self.Model.turbine_eff=eff_turbine
        self.Model.turbine_work=0
        self.Model.pump_work=0
        self.Model.heat_added=0
        self.Model.state1=None  # entrance to turbine
        self.Model.state2s=None  # entrance to condenser (isentropic turbine)
        self.Model.state2=None  # entrance to condenser (non-isentropic turbine)
        self.Model.state3=None  # entrance to pump (saturated liquid at plow)
        self.Model.state4=None  # entrance to boiler (isentropic)

    def print_summary(self):
        """
        A pass-thrugh method for accessing View and passing Model.
        :return:
        """
        self.View.print_summary(Model=self.Model)

    def buildDataForPlotting(self):
        """
        I want to create data for plotting the Rankine cycle.  The key states are:
        State 1.  Entrance to Turbine (either saturated vapor or superheated steam at p_High)
        State 2.  Entrance to Condenser (probably two-phase at p_Low)
        State 3.  Entrance to the pump (saturated liquid at p_Low)
        State 4.  Entrance to the boiler (sub-cooled liquid at p_High, isentropic pump)
        
        I want to create h, s, v, p, T data between states 1-2, 2-3, 3-4, 4-1
        I'll piece together an upperCurve data set from 3-4 + 4-1 + 1-2
        The lowerCurve data set is 2-3
        :return:
        """
        print("Starting to build data for plotting...")
        # clear out any old data
        self.Model.upperCurve.clear()
        self.Model.lowerCurve.clear()
        
        #get saturated properties at PHigh and PLow
        satPLow=self.Model.steam.getsatProps_p(self.Model.p_low)
        satPHigh=self.Model.steam.getsatProps_p(self.Model.p_high)
        
        steam = self.Model.steam

        #region build upperCurve
        #region states from 3-4
        nPts = 15
        DeltaP = (satPHigh.psat - satPLow.psat)
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state = steam.getState(P=(satPLow.psat + z * DeltaP), s=satPLow.sf)
            self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        # endregion

        #region states from 4-1
        #first from T4 to T5 where T5 is the saturated liquid at p_High
        T4 = state.t
        T5 = satPHigh.tsat
        DeltaT = (T5 - T4)
        nPts = 20
        P = satPHigh.psat
        for n in range(nPts-1):
            z = n * 1.0 / (nPts - 2)
            T = T4 + z * DeltaT
            if T<T5:
                state = steam.getState(P=P, T=T)
                self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state = steam.getState(satPHigh.psat,x=z)
            self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        if self.Model.state1.t > (satPHigh.tsat+1):
            T6 = satPHigh.tsat
            DeltaT = self.Model.state1.t - T6
            for n in range(0, nPts):
                z = n * 1.0 / (nPts - 1)
                if z>0:
                    state = steam.getState(satPHigh.psat, T=T6+z*DeltaT)
                    self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        # endregion

        #region states between 1 and 2
        #I'm assuming a linear change in Pressure from P1 to P2, along with linear change in s,
        #but not sure of details inside the turbine, so this is just a guess.
        s1=self.Model.state1.s
        s2=self.Model.state2.s
        P1=self.Model.state1.p
        P2=self.Model.state2.p
        Deltas=s2-s1
        DeltaP=P2-P1
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state = steam.getState(P=P1+z*DeltaP, s=s1+z*Deltas)
            self.Model.upperCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        #endregion
        #endregion

        #region build lowerCurve between states 2 and 3
        x2=self.Model.state2.x
        state=self.Model.state2
        #account for possibility that T>TSatPHigh
        if state.t>satPLow.tsat:
            nPts=20
            DeltaT=(state.t-satPLow.tsat)/nPts
            self.Model.lowerCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
            for n in range(nPts):
                t=self.Model.state2.t-n*DeltaT
                if t>satPLow.tsat:
                    state=steam.getState(P=satPLow.psat,T=t)
                    self.Model.lowerCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))

        nPts= len(self.Model.upperCurve.t)
        for n in range(nPts):
            z = n * 1.0 / (nPts - 1)
            state=steam.getState(P=satPLow.psat, x=(1.0-z)*x2)
            self.Model.lowerCurve.addPt((state.t, state.p, state.u, state.h, state.s, state.v))
        #endregion
        print("Finished building data for plotting.")
        pass

    def updatePlot(self, x_variable, y_variable, logx, logy):
        # Set the scale for axes
        self.View.ax.clear()
        self.View.ax.set_xscale('log' if logx else 'linear')
        self.View.ax.set_yscale('log' if logy else 'linear')

        # Assuming you have a method in your model to get cycle data as dictionaries
        # For simplicity, let's say each state is a dict with keys as properties
        # And there's a method `getCycleData()` that returns a list of such dicts
        cycle_data = self.Model.getCycleData()

        # Convert property names from UI to data keys
        x_data_key = self.mapUiVariableToDataKey(x_variable)
        y_data_key = self.mapUiVariableToDataKey(y_variable)

        # Extract data for plotting
        x_data = [state[x_data_key] for state in cycle_data]
        y_data = [state[y_data_key] for state in cycle_data]

        # Plot data
        self.View.ax.plot(x_data, y_data, marker='o', linestyle='-')
        self.View.ax.set_xlabel(x_variable)
        self.View.ax.set_ylabel(y_variable)

        # Re-draw the canvas
        self.View.canvas.draw()
    def mapUiVariableToDataKey(self, ui_variable):
        mapping = {
            "Pressure": "p",
            "Temperature": "t",
            "Enthalpy": "h",
            "Entropy": "s",
            # Add mappings for other variables as needed
        }
        return mapping.get(ui_variable, "p")  # Default to "p" or any other safe default

#endregion

#region function definitions
def main():
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    ui.addCanvas()  # Add the canvas to your UI
    # Here you need to collect all your inputWidgets and displayWidgets
    inputWidgets = [
        ui.rb_SI, ui.le_PHigh, ui.le_PLow, ui.le_TurbineInletCondition,
        ui.rdo_Quality, ui.le_TurbineEff, ui.cmb_XAxis, ui.cmb_YAxis,
        ui.chk_logX, ui.chk_logY
    ]

    displayWidgets = [
        ui.lbl_PHigh, ui.lbl_PLow, ui.lbl_SatPropLow, ui.lbl_SatPropHigh,
        ui.lbl_TurbineInletCondition, ui.lbl_H1, ui.lbl_H1Units, ui.lbl_H2,
        ui.lbl_H2Units, ui.lbl_H3, ui.lbl_H3Units, ui.lbl_H4, ui.lbl_H4Units,
        ui.lbl_TurbineWork, ui.lbl_TurbineWorkUnits, ui.lbl_PumpWork,
        ui.lbl_PumpWorkUnits, ui.lbl_HeatAdded, ui.lbl_HeatAddedUnits,
        ui.lbl_ThermalEfficiency, ui.canvas, ui.figure, ui.ax  # You need to define these in your UI class
    ]

    # Instantiate the controller with the widgets
    controller = rankineController(inputWidgets, displayWidgets)

    # Show the form and execute the app
    Form.show()
    sys.exit(app.exec_())


#region function calls
if __name__=="__main__":
    main()
#endregion