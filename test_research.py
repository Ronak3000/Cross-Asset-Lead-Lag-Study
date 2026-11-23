import unittest

import numpy as np

from hawkes import exposure, history
from simulation import MS, Settings, Tape, entry, simulate
from unittest.mock import patch


def row(t, action="A", side="B", bid=100, ask=101, size=1, price=100):
    unit = 10**9
    return t*MS, dict(flags=128, action=action, side=side, bid_px_00=bid*unit,
                      ask_px_00=ask*unit, bid_sz_00=5, ask_sz_00=6, price=price*unit, size=size)


class ResearchTests(unittest.TestCase):
    def test_tied_trades_have_no_same_time_excitation(self):
        x = history([(0.,0),(0.,1),(1.,2)], 2.)
        np.testing.assert_equal(x[:2], np.zeros((2,4)))
        np.testing.assert_allclose(x[2], [2*np.exp(-2),2*np.exp(-2),0,0])

    def test_holdout_integral_includes_training_history(self):
        value = exposure(np.array([0.,2.,3.]), np.array([1,0,2]), 1., 1., 3.)
        np.testing.assert_allclose(value,[1-np.exp(-1),np.exp(-1)-np.exp(-3),0,0])

    def test_passive_queue_requires_volume_beyond_initial_depth(self):
        tape = Tape([row(0),row(1,"T","A",size=5),row(2,"T","A"),row(10)],0,11*MS)
        self.assertEqual(entry(tape,0,1,"passive")[0],(2*MS,100.))
        self.assertIsNone(entry(tape,MS,1,"passive")[0])

    def test_passive_cancel_on_price_loss(self):
        tape = Tape([row(0),row(1,bid=99),row(2,"T","A",size=20),row(10)],0,11*MS)
        self.assertIsNone(entry(tape,0,1,"passive")[0])
        no_trades = Tape([row(0),row(1,bid=99),row(10)],0,11*MS)
        self.assertEqual(entry(no_trades,0,1,"passive"),(None,MS))

    def test_market_uses_arrival_quote_costs_and_one_position(self):
        tape = Tape([row(0),row(3, bid=101,ask=102),row(7,bid=103,ask=104),row(15)],0,16*MS)
        config = Settings(order_ms=2, hold_ms=2, fee=.01)
        with patch("simulation.signals",return_value=[(MS,1,1.,1.),(4*MS,1,1.,1.)]):
            result = simulate(tape,tape,{},config,0,16*MS)
        self.assertEqual((result["signals"],result["attempts"],result["trades"]),(2,1,1))
        self.assertEqual((result["ledger"][0]["entry"],result["ledger"][0]["exit"]),(102.,103.))
        self.assertAlmostEqual(result["net"],.98)

    def test_invalid_scenario_rejected(self):
        with self.assertRaises(ValueError):
            Settings(order_ms=-1)
