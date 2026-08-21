from colloquy.base import Base
from .browser import BodyStateNode, FaultsNode, ServosNode, TimingNode
from .dxl_ids import BODY_DXL_IDS
from .virtual_audio_serial_port import VirtualAudioSerialPort
from .virtual_serial_port import VirtualSerialPort
from .virtual_port_handler import VirtualPortHandler
from .virtual_packet_handler import VirtualPacketHandler


class VirtualDrivers(Base):
    """Root of the stand-ins the drivers talk to when `is_simulated`, plus
    a read-only view of what they currently hold.

    Named for the half it stands in for. It is not itself a driver - it is
    a fake serial port and nine fake servos - but it sits where the real
    ones would and the page names it beside `drivers`, which is the pair
    a reader is trying to tell apart.

    A plain Base, not a BaseThread. Nothing here runs a loop - it used to
    extend BaseThread without implementing setup/loop/setdown, so anything
    that started it (including a "start" link, once this node became
    visible in the web UI) would have raised NotImplementedError on its
    first tick.
    """

    def __init__(self, owner):
        super().__init__(owner)
        self._arduino_serial_port = None
        self._audio_serial_port = None
        self._u2d2_packet_handler = None
        self._body_nodes = {
            body: BodyStateNode(owner=self, body_name=body)
            for body in BODY_DXL_IDS
            if body != "bar"
        }
        self._servos_node = ServosNode(owner=self)
        self._faults_node = FaultsNode(owner=self)
        self._timing_node = TimingNode(owner=self)

    @property
    def params(self):
        return self.owner.params

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def name(self):
        return "virtual drivers"

    @property
    def dxls(self):
        return self.u2d2_packet_handler.dxls

    @property
    def states(self):
        """What the simulated arduino currently holds - see
        VirtualSerialPort._states."""
        return self.arduino_serial_port._states

    @property
    def arduino_serial_port(self):
        if self._arduino_serial_port is None:
            self._arduino_serial_port = VirtualSerialPort(owner=self)
        return self._arduino_serial_port

    @property
    def audio_serial_port(self):
        """Thomas's audio subsystem tester, when there is no board.

        Built on first use like the one above, so a machine that never
        opens the bench test never builds it.
        """
        if self._audio_serial_port is None:
            self._audio_serial_port = VirtualAudioSerialPort(owner=self)
        return self._audio_serial_port

    @property
    def u2d2_packet_handler(self):
        if self._u2d2_packet_handler is None:
            self._u2d2_packet_handler = VirtualPacketHandler(owner=self)
        return self._u2d2_packet_handler

    def u2d2_port_handler(self, port_name):
        # Deliberately a fresh handler per call, unlike the two memoized
        # stand-ins above: U2D2.open() asserts the previous one is closed
        # and then replaces it, mirroring the real PortHandler, which is
        # also constructed anew each time the port is opened.
        return VirtualPortHandler(port_name)

    @property
    def snapshot_children(self):
        children = dict(self._body_nodes)
        children[self._servos_node.name] = self._servos_node
        children[self._faults_node.name] = self._faults_node
        children[self._timing_node.name] = self._timing_node
        return children
