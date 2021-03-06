from nose.tools import ok_, assert_raises

import pandas as pd
import numpy as np
import logging
import filecmp
import os.path as ospath

from oemof.core.network.entities.components import transformers as transformer
from oemof.solph import predefined_objectives as predefined_objectives
from oemof.core import energy_system as es
from oemof.core.network.entities import Bus
from oemof.core.network.entities.buses import HeatBus
from oemof.solph import optimization_model as om
from oemof.core.network.entities.components import sources as source
from oemof.tools import helpers


class Entity_Tests:

    def test_HeatBus(self):
        "Creating a HeatBus without the temperature attribute raises an error."
        assert_raises(TypeError, HeatBus, uid="Test")


class Constraint_Tests:

    @classmethod
    def setUpClass(self):

        self.time_index = pd.date_range('1/1/2012', periods=3, freq='H')

        self.sim = es.Simulation(
            timesteps=range(len(self.time_index)), solver='glpk',
            objective_options={
                'function': predefined_objectives.minimize_cost})

        self.energysystem = es.EnergySystem(time_idx=self.time_index,
                                            simulation=self.sim)

        self.tmppath = helpers.extend_basic_path('tmp')
        logging.info(self.tmppath)

    def compare_lp_files(self, energysystem, filename):
        self.opt_model = om.OptimizationModel(energysystem=energysystem)
        tmp_filename = filename.replace('.lp', '') + '_tmp.lp'
        self.opt_model.write_lp_file(
            path=self.tmppath, filename=tmp_filename)
        logging.info("Comparing with file: {0}".format(filename))
        ok_(filecmp.cmp(ospath.join(self.tmppath, tmp_filename),
                        ospath.join("tests", "lp_files", filename)))

    def test_Transformer_Simple(self):
        "Test transformer.Simple with and without investment."
        self.energysystem.entities = []

        bgas = Bus(uid="bgas",
                   type="gas",
                   price=70,
                   balanced=True,
                   excess=False)

        bel = Bus(uid="bel",
                  type="el",
                  excess=True)

        transformer.Simple(
            uid='pp_gas',
            inputs=[bgas],
            outputs=[bel],
            opex_var=50,
            out_max=[10e10],
            eta=[0.58])

        self.compare_lp_files(self.energysystem, "transformer_simp.lp")

        transformer.Simple.optimization_options.update({'investment': True})
        self.compare_lp_files(self.energysystem, "transformer_simp_invest.lp")

    def test_source_fixed(self):
        "Test source.FixedSource with and without investment."
        self.energysystem.entities = []

        bel = Bus(uid="bel",
                  type="el")

        source.FixedSource(uid="wind",
                           outputs=[bel],
                           val=[50, 80, 30],
                           out_max=[1000000],
                           add_out_limit=0,
                           capex=1000,
                           opex_fix=20,
                           lifetime=25,
                           crf=0.08)

        self.compare_lp_files(self.energysystem, "source_fixed.lp")
        source.FixedSource.optimization_options.update({'investment': True})
        self.compare_lp_files(self.energysystem, "source_fixed_invest.lp")

    def test_storage(self):
        pass

    def test_postheating_invest(self):
        self.energysystem.entities = []

        btest = HeatBus(
            uid="bus_test",
            excess=False,
            temperature=1,
            re_temperature=1)

        district_heat_bus = HeatBus(
            uid="bus_distr_heat",
            excess=False,
            temperature=np.array([380, 360, 370]),
            re_temperature=np.array([340, 340, 340]))

        storage_heat_bus = HeatBus(
            excess=False,
            uid="bus_stor_heat",
            temperature=370)

        postheat = transformer.PostHeating(
            uid='postheat_elec',
            inputs=[btest, storage_heat_bus], outputs=[district_heat_bus],
            opex_var=0, capex=99999,
            out_max=[999993],
            in_max=[777, 888],
            eta=[0.95, 1])

        assert_raises(ValueError, om.OptimizationModel,
                      energysystem=self.energysystem)

        postheat.in_max = [None, float('inf')]
        self.compare_lp_files(self.energysystem, "postheating_invest.lp")

        transformer.PostHeating.optimization_options.update(
            {'investment': False})

        postheat.in_max = [777, 888]
        self.compare_lp_files(self.energysystem, "postheating.lp")
