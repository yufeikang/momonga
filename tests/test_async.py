import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from momonga.aio import AsyncMomonga

class TestAsyncMomonga(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # momonga.Momonga クラスをモック化
        self.patcher = patch('momonga.aio.Momonga')
        self.MockMomongaClass = self.patcher.start()
        self.mock_sync_client = self.MockMomongaClass.return_value
        
        # AsyncMomonga インスタンス作成
        self.amo = AsyncMomonga(rbid='id', pwd='pwd', dev='dev')

    async def asyncTearDown(self):
        self.patcher.stop()

    async def test_context_manager(self):
        """非同期コンテキストマネージャが正しく open/close を呼ぶか"""
        async with self.amo as client:
            self.assertIs(client, self.amo)
            # open が呼ばれたか (同期メソッドが)
            self.mock_sync_client.open.assert_called_once()
        
        # close が呼ばれたか
        self.mock_sync_client.close.assert_called_once()

    async def test_get_instantaneous_power(self):
        """get_instantaneous_power が正しくラップされているか"""
        # 同期メソッドの戻り値を設定
        self.mock_sync_client.get_instantaneous_power.return_value = 500.0
        
        # 非同期メソッド呼び出し
        ret = await self.amo.get_instantaneous_power()
        
        # 検証
        self.assertEqual(ret, 500.0)
        self.mock_sync_client.get_instantaneous_power.assert_called_once()

    async def test_get_measured_cumulative_energy_with_args(self):
        """引数付きメソッド (get_measured_cumulative_energy) のテスト"""
        self.mock_sync_client.get_measured_cumulative_energy.return_value = 1234.56
        
        # 引数ありで呼び出し
        ret = await self.amo.get_measured_cumulative_energy(reverse=True)
        
        self.assertEqual(ret, 1234.56)
        # 引数が正しく渡されたか
        self.mock_sync_client.get_measured_cumulative_energy.assert_called_once_with(True)

    async def test_request_to_set_kwargs(self):
        """キーワード引数付きメソッド (request_to_set) のテスト"""
        await self.amo.request_to_set(day_for_historical_data_1={'day': 1})
        
        self.mock_sync_client.request_to_set.assert_called_once_with(day_for_historical_data_1={'day': 1})

if __name__ == '__main__':
    unittest.main()
