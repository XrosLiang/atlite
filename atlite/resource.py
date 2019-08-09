# -*- coding: utf-8 -*-

## Copyright 2016-2017 Gorm Andresen (Aarhus University), Jonas Hoersch (FIAS), Tom Brown (FIAS)

## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Renewable Energy Atlas Lite (Atlite)

Light-weight version of Aarhus RE Atlas for converting weather data to power systems data
"""

import os
import yaml
from operator import itemgetter
import numpy as np
from scipy.signal import fftconvolve
from pkg_resources import resource_stream

from . import config
from .wind import download_turbineconf

import logging
logger = logging.getLogger(name=__name__)

from . import config
from .utils import construct_filepath, arrowdict

def get_windturbineconfig(turbine):
    """Load the wind 'turbine' configuration.

    The configuration can either be one from local storage, then 'turbine' is
    considered part of the file base name '<turbine>.yaml' in config.windturbine_dir.
    Alternatively the configuration can be downloaded from the Open Energy Database (OEDB),
    in which case 'turbine' is a dictionary used for selecting a turbine from the database.

    Parameter
    ---------
    turbine : str|dict
        Name of the local turbine file.
        Alternatively a dict for selecting a turbine from the Open Energy Database,
        in thins case the key 'source' should be contained. For all other key arguments
        to retrieve the matching turbine, see atlite.wind.download_turbineconf() for details.
    """

    turbineconf = None

    if isinstance(turbine, str):
        if turbine.startswith('oedb:'):
            turbineconf = download_turbineconf(turbine, store_locally=False)
        else:
            turbine = {'filename':turbine, 'source':'local'}
    if isinstance(turbine, dict):
        if turbine.get('source') is None:
            logger.warning("No key 'source':'oedb' provided with the turbine dictionary."
                           "I am assuming and adding it for now, but still nag you about it.")
            turbine['source'] = 'oedb'

        if turbine['source'] == 'oedb':
            turbineconf = download_turbineconf(turbine, store_locally=False)
        elif turbine['source'] == "local":
            res_name = os.path.join(config.windturbine_dir, turbine['filename']+".yaml")
            res_name = construct_filepath(res_name)

            with open(res_name, "r") as turbine_file:
                turbineconf = yaml.safe_load(turbine_file)
        else:
            raise ValueError("Not a valid 'source'.")

    if turbineconf is None:
        raise ValueError("No matching turbine configuration found.")

    V, POW, hub_height = itemgetter('V', 'POW', 'HUB_HEIGHT')(turbineconf)
    return dict(V=np.array(V), POW=np.array(POW), hub_height=hub_height, P=np.max(POW))

def get_solarpanelconfig(panel):
    """Load the 'panel'.yaml file from local disk and provide a solar panel dict."""

    res_name = os.path.join(config.solarpanel_dir, panel+".yaml")

    res_name = construct_filepath(res_name)

    with open(res_name, "r") as panel_file:
        panelconf = yaml.safe_load(panel_file)

    return panelconf

def solarpanel_rated_capacity_per_unit(panel):
    # unit is m^2 here

    if isinstance(panel, str):
        panel = get_solarpanelconfig(panel)

    model = panel.get('model', 'huld')
    if model == 'huld':
        return panel['efficiency']
    elif model == 'bofinger':
        # one unit in the capacity layout is interpreted as one panel of a
        # capacity (A + 1000 * B + log(1000) * C) * 1000W/m^2 * (k / 1000)
        A, B, C = itemgetter('A', 'B', 'C')(panel)
        return (A + B * 1000. + C * np.log(1000.))*1e3

def windturbine_rated_capacity_per_unit(turbine):
    if isinstance(turbine, str):
        turbine = get_windturbineconfig(turbine)

    return turbine['P']

def windturbine_smooth(turbine, params={}):
    '''
    Smooth the powercurve in `turbine` with a gaussian kernel

    Parameters
    ----------
    turbine : dict
        Turbine config with at least V and POW
    params : dict
        Allows adjusting fleet availability eta, mean Delta_v and
        stdev sigma. Defaults to values from Andresen's paper: 0.95,
        1.27 and 2.29, respectively.

    Returns
    -------
    turbine : dict
        Turbine config with a smoothed power curve

    References
    ----------
    G. B. Andresen, A. A. Søndergaard, M. Greiner, Validation of
    Danish wind time series from a new global renewable energy atlas
    for energy system analysis, Energy 93, Part 1 (2015) 1074–1088.
    '''

    if not isinstance(params, dict):
        params = {}

    eta = params.setdefault('eta', 0.95)
    Delta_v = params.setdefault('Delta_v', 1.27)
    sigma = params.setdefault('sigma', 2.29)

    def kernel(v_0):
        # all velocities in m/s
        return (1./np.sqrt(2*np.pi*sigma*sigma) *
                np.exp(-(v_0 - Delta_v)*(v_0 - Delta_v)/(2*sigma*sigma) ))

    def smooth(velocities, power):
        # interpolate kernel and power curve to the same, regular velocity grid
        velocities_reg = np.linspace(-50., 50., 1001)
        power_reg = np.interp(velocities_reg, velocities, power)
        kernel_reg = kernel(velocities_reg)

        # convolve power and kernel
        # the downscaling is necessary because scipy expects the velocity
        # increments to be 1., but here, they are 0.1
        convolution = 0.1*fftconvolve(power_reg, kernel_reg, mode='same')

        # sample down so power curve doesn't get too long
        velocities_new = np.linspace(0., 35., 72)
        power_new = eta * np.interp(velocities_new, velocities_reg, convolution)

        return velocities_new, power_new

    turbine = turbine.copy()
    turbine['V'], turbine['POW'] = smooth(turbine['V'], turbine['POW'])
    turbine['P'] = np.max(turbine['POW'])

    if any(turbine['POW'][np.where(turbine['V'] == 0.0)] > 1e-2):
        logger.warn("Oversmoothing detected with parameters {p}. " +
                    "Turbine generates energy at 0 m/s wind speeds".format(p=params))

    return turbine


turbines = arrowdict({t[:-5]: t[:-5] for t in
                     os.listdir(os.path.join(os.path.dirname(__file__),
                               'resources', 'windturbine'))})

panels = arrowdict({t[:-5]: t[:-5] for t in
                     os.listdir(os.path.join(os.path.dirname(__file__),
                               'resources', 'solarpanel'))})

