# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 15:53:14 2015

@author: uwe
"""

import pickle
import logging
import os

from oemof.core.network import Entity
from oemof.core.network.entities.components import transports as transport
from oemof.solph.optimization_model import OptimizationModel as OM


class EnergySystem:
    r"""Defining an energy supply system to use oemof's solver libraries.

    Note
    ----
    The list of regions is not necessary to use the energy system with solph.

    Parameters
    ----------
    entities : list of :class:`Entity <oemof.core.network.Entity>`, optional
        A list containing the already existing :class:`Entities
        <oemof.core.network.Entity>` that should be part of the energy system.
        Stored in the :attr:`entities` attribute.
        Defaults to `[]` if not supplied.
    simulation : core.energy_system.Simulation object
        Simulation object that contains all necessary attributes to start the
        solver library. Defined in the :py:class:`Simulation
        <oemof.core.energy_system.Simulation>` class.
    regions : list of core.energy_system.Region objects
        List of regions defined in the :py:class:`Region
        <oemof.core.energy_system.Simulation>` class.
    time_idx : pandas.index, optional
        Define the time range and increment for the energy system. This is an
        optional parameter but might be import for other functions/methods that
        use the EnergySystem class as an input parameter.

    Attributes
    ----------
    entities : list of :class:`Entity <oemof.core.network.Entity>`
        A list containing the :class:`Entities <oemof.core.network.Entity>`
        that comprise the energy system. If this :class:`EnergySystem` is
        set as the :attr:`registry <oemof.core.network.Entity.registry>`
        attribute, which is done automatically on :class:`EnergySystem`
        construction, newly created :class:`Entities
        <oemof.core.network.Entity>` are automatically added to this list on
        construction.
    simulation : core.energy_system.Simulation object
        Simulation object that contains all necessary attributes to start the
        solver library. Defined in the :py:class:`Simulation
        <oemof.core.energy_system.Simulation>` class.
    regions : list of core.energy_system.Region objects
        List of regions defined in the :py:class:`Region
        <oemof.core.energy_system.Simulation>` class.
    results : dictionary
        A dictionary holding the results produced by the energy system.
        Is `None` while no results are produced.
        Currently only set after a call to :meth:`optimize` after which it
        holds the return value of :meth:`om.results()
        <oemof.solph.optimization_model.OptimizationModel.results>`.
        See the documentation of that method for a detailed description of the
        structure of the results dictionary.
    time_idx : pandas.index, optional
        Define the time range and increment for the energy system. This is an
        optional atribute but might be import for other functions/methods that
        use the EnergySystem class as an input parameter.
    """
    def __init__(self, **kwargs):
        for attribute in ['regions', 'entities', 'simulation']:
            setattr(self, attribute, kwargs.get(attribute, []))

        Entity.registry = self
        self.results = kwargs.get('results')
        self.time_idx = kwargs.get('time_idx')

    # TODO: Condense signature (use Buse)
    def connect(self, bus1, bus2, in_max, out_max, eta, transport_class):
        """Create two transport objects to connect two buses of the same type
        in both directions.

        Parameters
        ----------
        bus1, bus2 : core.network.Bus object
            Two buses to be connected.
        eta : float
            Constant efficiency of the transport.
        in_max : float
            Maximum input the transport can handle, in $MW$.
        out_max : float
            Maximum output which can possibly be obtained when using the
            transport, in $MW$.
        transport_class class
            Transport class to use for the connection
        """
        if not transport_class == transport.Simple:
            logging.error('')
            raise(TypeError(
                "Sorry, `EnergySystem.connect` currently only works with" +
                "a `transport_class` argument of" + str(transport.Simple)))
        for bus_a, bus_b in [(bus1, bus2), (bus2, bus1)]:
            uid = ('transport',) + bus_a.uid + bus_b.uid
            transport_class(uid=uid, outputs=[bus_a], inputs=[bus_b],
                            out_max=[out_max], in_max=[in_max], eta=[eta])

    # TODO: Add concept to make it possible to use another solver library.
    def optimize(self, om=None):
        """Start optimizing the energy system using solph.

        Parameters
        ----------
        om : :class:`OptimizationModel <oemof.solph.optimization_model.OptimizationModel>`, optional
            The optimization model used to optimize the :class:`EnergySystem`.
            If not given, an :class:`OptimizationModel
            <oemof.solph.optimization_model.OptimizationModel>` instance local
            to this method is created using the current :class:`EnergySystem`
            instance as an argument.
            You only need to supply this if you want to observe any side
            effects that solving has on the `om`.

        Returns
        -------
        self : :class:`EnergySystem`
        """
        if om is None:
            om = OM(energysystem=self)

        om.solve(solver=self.simulation.solver, debug=self.simulation.debug,
                 verbose=self.simulation.verbose,
                 duals=self.simulation.duals,
                 solve_kwargs=self.simulation.solve_kwargs)

        self.results = om.results()
        return self

    def dump(self, dpath=None, filename=None, keep_weather=True):
        r""" Dump an EnergySystem instance.
        """
        if dpath is None:
            bpath = os.path.join(os.path.expanduser("~"), '.oemof')
            if not os.path.isdir(bpath):
                os.mkdir(bpath)
            dpath = os.path.join(bpath, 'dumps')
            if not os.path.isdir(dpath):
                os.mkdir(dpath)

        if filename is None:
            filename = 'es_dump.oemof'

        pickle.dump(self.__dict__, open(os.path.join(dpath, filename), 'wb'))

        msg = ('Attributes dumped to: {0}'.format(os.path.join(
            dpath, filename)))
        logging.debug(msg)
        return msg

    def restore(self, dpath=None, filename=None):
        r""" Restore an EnergySystem instance.
        """
        logging.info(
            "Restoring attributes will overwrite existing attributes.")
        if dpath is None:
            dpath = os.path.join(os.path.expanduser("~"), '.oemof', 'dumps')

        if filename is None:
            filename = 'es_dump.oemof'

        self.__dict__ = pickle.load(open(os.path.join(dpath, filename), "rb"))
        msg = ('Attributes restored from: {0}'.format(os.path.join(
            dpath, filename)))
        logging.debug(msg)
        return msg


class Region:
    r"""Defining a region within an energy supply system.

    Note
    ----
    The list of regions is not necessary to use the energy system with solph.

    Parameters
    ----------
    entities : list of core.network objects
        List of all objects of the energy system. All class descriptions can
        be found in the :py:mod:`oemof.core.network` package.
    name : string
        A unique name to identify the region. If possible use typical names for
        regions and english names for countries.
    code : string
        A short unique name to identify the region.
    geom : shapely.geometry object
        The geometry representing the region must be a polygon or a multi
        polygon.

    Attributes
    ----------
    entities : list of core.network objects
        List of all objects of the energy system. All class descriptions can
        be found in the :py:mod:`oemof.core.network` package.
    name : string
        A unique name to identify the region. If possible use typical names for
        regions and english names for countries.
    geom : shapely.geometry object
        The geometry representing the region must be a polygon or a multi
        polygon.
    """
    def __init__(self, **kwargs):
        self.entities = []  # list of entities
        self.add_entities(kwargs.get('entities', []))

        self.name = kwargs.get('name')
        self.geom = kwargs.get('geom')
        self._code = kwargs.get('code')

    # TODO: oder sollte das ein setter sein? Yupp.
    def add_entities(self, entities):
        """Add a list of entities to the existing list of entities.

        For every entity added to a region the region attribute of the entity
        is set

        Parameters
        ----------
        entities : list of core.network objects
            List of all objects of the energy system that belongs to area
            covered by the polygon of the region. All class descriptions can
            be found in the :py:mod:`oemof.core.network` package.
        """

        # TODO: prevent duplicate entries
        self.entities.extend(entities)
        for entity in entities:
            if self not in entity.regions:
                entity.regions.append(self)

    @property
    def code(self):
        """Creating a short code based on the region name if no code is set."""
        if self._code is None:
            name_parts = self.name.replace('_', ' ').split(' ', 1)
            self._code = ''
            for part in name_parts:
                self._code += part[:1].upper() + part[1:3]
        return self._code


class Simulation:
    r"""Defining the simulation related parameters according to the solver lib.

    Parameters
    ----------
    solver : string
        Name of the solver supported by the used solver library.
        (e.g. 'glpk', 'gurobi')
    debug : boolean
        Set the chosen solver to debug (verbose) mode to get more information.
    verbose : boolean
        If True, solver output etc. is streamed in python console
    duals : boolean
        If True, results of dual variables and reduced costs will be saved
    objective_options : dictionary
        'function': function to use from
                    :py:mod:`oemof.solph.predefined_objectives`
        'cost_objects': list of str(`class`) elements. Objects of type  `class`
                        are include in cost terms of objective function.
        'revenue_objects': list of str(`class`) elements. . Objects of type
                           `class` are include in revenue terms of
                           objective function.
    timesteps : list or sequence object
         Timesteps to be simulated or optimized in the used library
    relaxed : boolean
        If True, integer variables will be relaxed
        (only relevant for milp-problems)
    fast_build : boolean
        If True, the standard way of pyomo constraint building is skipped and
        a different function is used.
        (Warning: No guarantee that all expected 'standard' pyomo model
        functionalities work for the constructed model!)
    """
    def __init__(self, **kwargs):
        ''
        self.solver = kwargs.get('solver', 'glpk')
        self.debug = kwargs.get('debug', False)
        self.verbose = kwargs.get('verbose', False)
        self.objective_options = kwargs.get('objective_options', {})
        self.duals = kwargs.get('duals', False)
        self.timesteps = kwargs.get('timesteps')
        self.relaxed = kwargs.get('relaxed', False)
        self.fast_build = kwargs.get('fast_build', False)
        self.solve_kwargs = kwargs.get('solve_kwargs', {})

        if self.timesteps is None:
            raise ValueError('No timesteps defined!')
