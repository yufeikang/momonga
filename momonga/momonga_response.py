from typing import Optional

from .momonga_exception import MomongaKeyError
from .momonga_device_enum import DeviceType


class MomongaSkResponseBase:
    def __init__(self, res, device_type: Optional[DeviceType] = None):
        self.raw_response = res
        self.device_type = device_type
        self.decode()

    def decode(self):
        pass

    def extract(self, key):
        for elm in reversed(self.raw_response):
            if key in elm:
                return elm
        raise MomongaKeyError(key)


class SkVerResponse(MomongaSkResponseBase):
    def decode(self):
        res_list = self.extract('EVER').split()
        self.stack_ver = res_list[1]


class SkAppVerResponse(MomongaSkResponseBase):
    def decode(self):
        res_list = self.extract('EAPPVER').split()
        self.app_ver = res_list[1]


class SkInfoResponse(MomongaSkResponseBase):
    def decode(self):
        res_list = self.extract('EINFO').split()
        self.ip6_addr = res_list[1]
        self.mac_addr = bytes.fromhex(res_list[2])
        self.channel = int(res_list[3], 16)
        self.pan_id = bytes.fromhex(res_list[4])
        self.side = int(res_list[5], 16)


class SkScanResponse(MomongaSkResponseBase):
    def decode(self):
        self.channel = int(self.extract('Channel:').split(':')[-1], 16)
        self.channel_page = int(self.extract('Channel Page:').split(':')[-1], 16)
        self.pan_id = bytes.fromhex(self.extract('Pan ID:').split(':')[-1])
        self.mac_addr = bytes.fromhex(self.extract('Addr:').split(':')[-1])
        self.lqi = int(self.extract('LQI:').split(':')[-1], 16)
        self.rssi = 0.275 * self.lqi - 104.27
        match self.device_type:
            case DeviceType.BP35A1:
                self.side = None
            case DeviceType.BP35C2:
                self.side = int(self.extract('Side:').split(':')[-1], 16)
            case _:
                self.side = int(self.extract('Side:').split(':')[-1], 16)
        self.pair_id = bytes.fromhex(self.extract('PairID:').split(':')[-1])


class SkLl64Response(MomongaSkResponseBase):
    def decode(self):
        self.ip6_addr = self.extract('FE80:')


class SkSendToResponse(MomongaSkResponseBase):
    def decode(self):
        self.res_list = self.extract('EVENT 21').split()
        self.event_num = int(self.res_list[1], 16)
        self.src_addr = self.res_list[2]
        match self.device_type:
            case DeviceType.BP35A1:
                self.side = None
                self.param = int(self.res_list[3], 16)
            case DeviceType.BP35C2:
                self.side = int(self.res_list[3], 16)
                self.param = int(self.res_list[4], 16)
            case _:
                self.side = int(self.res_list[3], 16)
                self.param = int(self.res_list[4], 16)


class SkEventRxUdp(MomongaSkResponseBase):
    def decode(self):
        self.res_list = self.extract('ERXUDP').split()
        self.src_addr = self.res_list[1]
        self.des_addr = self.res_list[2]
        self.src_port = int(self.res_list[3], 16)
        self.dst_port = int(self.res_list[4], 16)
        self.src_mac = bytes.fromhex(self.res_list[5])
        match self.device_type:
            case DeviceType.BP35A1:
                self.lqi = None
                self.rssi = None
                self.sec = int(self.res_list[6], 16)
                self.side = None
                self.data_len = int(self.res_list[7], 16)
                self.data = bytes.fromhex(self.res_list[8])
            case DeviceType.BP35C2:
                self.lqi = int(self.res_list[6], 16)
                self.rssi = 0.275 * self.lqi - 104.27
                self.sec = int(self.res_list[7], 16)
                self.side = int(self.res_list[8], 16)
                self.data_len = int(self.res_list[9], 16)
                self.data = bytes.fromhex(self.res_list[10])
            case _:
                self.lqi = int(self.res_list[6], 16)
                self.rssi = 0.275 * self.lqi - 104.27
                self.sec = int(self.res_list[7], 16)
                self.side = int(self.res_list[8], 16)
                self.data_len = int(self.res_list[9], 16)
                self.data = bytes.fromhex(self.res_list[10])
