#!/usr/bin/env python3
"""下位机模拟器的定向协议与物理模型测试。"""

import importlib.util
import pathlib
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "pty_modbus_sim", pathlib.Path(__file__).with_name("pty_modbus_sim.py"))
simulator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(simulator)


class MemoryTransport:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)


class SimulatorStub:
    def __init__(self, emulate_write_sync=True):
        self.lock = threading.RLock()
        self.emulate_write_sync = emulate_write_sync
        self.heater_pairs = (1, 2, 3)
        self.logs = []

    def log(self, message):
        self.logs.append(message)


def read_request(slave, start, count):
    return simulator.rtu(bytes([slave, 0x03]) + struct.pack(">HH", start, count))


def write_request(slave, start, values, byte_count=None):
    data = struct.pack(f">{len(values)}H", *values)
    if byte_count is None:
        byte_count = len(data)
    body = (bytes([slave, 0x10]) + struct.pack(">HHB", start, len(values), byte_count)
            + data[:byte_count])
    return simulator.rtu(body)


class ProtocolTest(unittest.TestCase):
    def make_bus(self, emulate_write_sync=False):
        transport = MemoryTransport()
        bus = simulator.Bus(0, "test", [1, 2], transport,
                            SimulatorStub(emulate_write_sync))
        return bus, transport

    def test_read_returns_real_register_values_and_crc(self):
        bus, transport = self.make_bus()
        bus.devices[1].regs["voltage"] = 246

        bus.handle_rx(read_request(1, 0x0003, 1))

        response = transport.writes[-1]
        self.assertEqual(response[:5], bytes.fromhex("01 03 02 00 f6"))
        self.assertEqual(simulator.crc16(response[:-2]), int.from_bytes(response[-2:], "little"))

    def test_write_multiple_changes_outputs_and_can_be_read_back(self):
        bus, transport = self.make_bus()

        bus.handle_rx(write_request(1, 0x0013, [1, 0, 1]))
        bus.handle_rx(read_request(1, 0x0013, 3))

        self.assertEqual(bus.devices[1].ot[2:5], [1, 0, 1])
        self.assertEqual(transport.writes[-1][3:9], bytes.fromhex("00 01 00 00 00 01"))

    def test_illegal_write_is_atomic_and_returns_exception(self):
        bus, transport = self.make_bus()

        bus.handle_rx(write_request(1, 0x0013, [1, 2, 1]))

        self.assertEqual(bus.devices[1].ot[2:5], [0, 0, 0])
        self.assertEqual(transport.writes[-1][:3], bytes([1, 0x90, 0x03]))

    def test_write_single_changes_output_in_compatibility_mode(self):
        bus, transport = self.make_bus()
        request = simulator.rtu(bytes([1, 0x06]) + struct.pack(">HH", 0x0014, 1))

        bus.handle_rx(request)

        self.assertEqual(bus.devices[1].ot[3], 1)
        self.assertEqual(transport.writes[-1], request)

    def test_malformed_multiple_write_returns_illegal_value(self):
        bus, transport = self.make_bus()
        body = bytes([1, 0x10]) + struct.pack(">HHB", 0x0013, 2, 2) + b"\x00\x01"

        bus.handle_rx(simulator.rtu(body))

        self.assertEqual(bus.devices[1].ot[2:4], [0, 0])
        self.assertEqual(transport.writes[-1][:3], bytes([1, 0x90, 0x03]))

    def test_address_switch_write_quirk_matches_field_device(self):
        bus, transport = self.make_bus(emulate_write_sync=True)
        bus.handle_rx(read_request(2, 0x0001, 1))
        transport.writes.clear()

        request = write_request(1, 0x0013, [1])
        bus.handle_rx(request)
        self.assertEqual(transport.writes, [])
        self.assertEqual(bus.devices[1].ot[2], 0)

        bus.handle_rx(request)
        self.assertEqual(len(transport.writes), 1)
        self.assertEqual(bus.devices[1].ot[2], 1)

    def test_stream_recovers_after_leading_garbage(self):
        bus, transport = self.make_bus()

        bus.handle_rx(b"\xff" + read_request(1, 0x0001, 1))

        self.assertEqual(len(transport.writes), 1)
        self.assertEqual(bus.rx, b"")

    def test_current_host_poll_and_expansion_mask_read_write(self):
        bus, transport = self.make_bus()
        device = bus.devices[1]
        device.exp_in = [1, 0, 1, 0, 1]
        for start, count in ((0, 1), (1, 11), (0x000C, 1), (0x000E, 1),
                             (0x0031, 1), (0x0033, 1)):
            bus.handle_rx(read_request(1, start, count))
            self.assertEqual(transport.writes[-1][1:3], bytes([3, count * 2]))
        self.assertEqual(device.read_regs(0x000C, 1), [0x15])
        self.assertEqual(device.read_regs(0x000E, 1), [0])
        bus.handle_rx(write_request(1, 0x0031, [0x201]))
        request = simulator.rtu(bytes([1, 6]) + struct.pack(">HH", 0x0033, 0x55))
        bus.handle_rx(request)
        self.assertEqual(transport.writes[-1], request)
        self.assertEqual(device.read_regs(0x0031, 1), [0x201])
        self.assertEqual(device.read_regs(0x0033, 1), [0x55])
        self.assertEqual(device.heater_gears(), [1, 0, 0])


class DeviceModelTest(unittest.TestCase):
    def test_heating_tracks_configured_pairs_and_ignores_unused_outputs(self):
        device = simulator.Device(1, 22.0, (1, 4, 5))
        device.internal = 22.0
        device.ot[2] = 1
        device.tick(10)
        self.assertAlmostEqual(device.internal, 22.0)
        device.ot = [1, 0, 0, 0, 0, 0, 0, 1, 1, 1]
        self.assertEqual(device.heater_gears(), [1, 2, 3])
        device.tick(10)
        self.assertGreater(device.internal, 23.7)

    def test_physics_uses_elapsed_time_not_tick_count(self):
        one_tick = simulator.Device(1, 22.0)
        many_ticks = simulator.Device(1, 22.0)
        for device in (one_tick, many_ticks):
            device.internal = device.ambient
            device.ot[2] = 1

        one_tick.tick(10.0)
        for _ in range(20):
            many_ticks.tick(0.5)

        self.assertAlmostEqual(one_tick.internal, many_ticks.internal, delta=0.01)

    def test_negative_temperature_is_signed_in_model_and_uint16_on_wire(self):
        device = simulator.Device(1, 22.0)
        device.regs["th1_temp"] = simulator.Device._temp10(-12.3)

        self.assertEqual(device.regs["th1_temp"], -123)
        self.assertEqual(device.read_regs(0x0004, 1), [0xFF85])


class OperatingScenarioTest(unittest.TestCase):
    def make_simulator(self):
        sim = object.__new__(simulator.Simulator)
        sim.lock = threading.RLock()
        sim.log_enabled = False
        sim.emulate_write_sync = True
        sim.heater_pairs = (1, 2, 3)
        sim.input_modes = ["unused", "heater_a", "heater_b", "heater_c", "unused"]
        sim.buses = [
            simulator.Bus(0, "P0", [1, 2, 3], MemoryTransport(), sim),
            simulator.Bus(1, "P1", [4, 5], MemoryTransport(), sim),
        ]
        return sim

    def test_config_survives_restart_and_updates_live_wiring(self):
        sim = self.make_simulator()
        with tempfile.TemporaryDirectory() as run_dir, patch.object(simulator, "RUN_DIR", run_dir):
            sim.config_path = simulator.write_run_config("/dev/pts/10", "/dev/pts/11")
            sim.config_stamp = None
            config = pathlib.Path(sim.config_path)
            original = config.read_text()
            config.write_text(original.replace("heaterAPair=1", "heaterAPair=5")
                              .replace("expIn2Mode=heater_a", "expIn2Mode=unused")
                              .replace("expIn5Mode=unused", "expIn5Mode=heater_a"))
            simulator.write_run_config("/dev/pts/20", "/dev/pts/21")
            sim.reload_config()
            self.assertEqual(sim.heater_pairs, (5, 2, 3))
            self.assertEqual(sim.buses[0].devices[1].heater_pairs, (5, 2, 3))
            self.assertIn("device=/dev/pts/20", config.read_text())
            with patch.object(simulator.time, "monotonic", return_value=10):
                sim.cmd_press(["0:1", "A"])
            device = sim.buses[0].devices[1]
            self.assertEqual(device.exp_in, [0, 0, 0, 0, 1])
            self.assertEqual(device.input_releases, {4: 10.6})
            with self.assertRaisesRegex(ValueError, "已闭合"):
                sim.cmd_press(["0:1", "A"])
            sim.execute("set 0:1 in5 0")
            self.assertEqual(device.input_releases, {})
            simulator.write_run_config("/dev/pts/30", "/dev/pts/31", reset=True)
            self.assertIn("heaterAPair=1", config.read_text())

    def test_high_voltage_switch_drives_both_detection_inputs(self):
        sim = self.make_simulator()
        device = sim.buses[0].devices[1]
        self.assertEqual((device.regs["hv_input"], device.regs["voltage"]), (1, 0))

        sim.execute("highvoltage 0:1 on")
        self.assertEqual((device.regs["hv_input"], device.regs["voltage"]), (0, 120))

        sim.execute("highvoltage 0:1 off")
        self.assertEqual((device.regs["hv_input"], device.regs["voltage"]), (1, 0))

    def test_add_remove_and_crowded_scenarios_change_real_bus_population(self):
        sim = self.make_simulator()
        sim.execute("remove 0:2")
        sim.execute("add 1:8 19")
        self.assertNotIn(2, sim.buses[0].devices)
        self.assertEqual(sim.buses[1].devices[8].ambient, 19)

        sim.execute("scenario crowded")
        self.assertEqual(set(sim.buses[0].devices), set(range(1, 17)))
        self.assertEqual(set(sim.buses[1].devices), set(range(1, 17)))

        sim.execute("scenario normal")
        self.assertEqual(set(sim.buses[0].devices), {1, 2, 3})
        self.assertEqual(set(sim.buses[1].devices), {4, 5})

    def test_temperature_and_pt100_can_be_adjusted_independently(self):
        sim = self.make_simulator()
        device = sim.buses[0].devices[1]
        original_pt100 = [device.regs[f"pt{i}_temp"] for i in range(1, 3)]

        sim.execute("temperature 0:1 30")
        self.assertEqual(
            [device.regs[f"th{i}_temp"] for i in range(1, 4)], [300, 300, 300])
        self.assertEqual(
            [device.regs[f"pt{i}_temp"] for i in range(1, 3)], original_pt100)

        sim.execute("pt100 0:1 26")
        self.assertEqual(
            [device.regs[f"pt{i}_temp"] for i in range(1, 3)], [260, 260])
        self.assertEqual(
            [device.regs[f"th{i}_temp"] for i in range(1, 4)], [300, 300, 300])

        device.tick(60.0)

        self.assertEqual(
            [device.regs[f"th{i}_temp"] for i in range(1, 4)], [300, 300, 300])
        self.assertEqual(
            [device.regs[f"pt{i}_temp"] for i in range(1, 3)], [260, 260])


if __name__ == "__main__":
    unittest.main()
