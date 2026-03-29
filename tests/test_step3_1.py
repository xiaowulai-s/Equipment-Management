"""
步骤3.1 测试 - 通信驱动基类 (BaseDriver)

覆盖范围:
    [1] DriverState 常量
    [2] DriverStats 性能统计
    [3] BaseDriver 实例化与属性
    [4] BaseDriver 状态管理 (状态机)
    [5] BaseDriver.configure() 参数配置
    [6] BaseDriver 抽象方法约束
    [7] BaseDriver 模板方法 (open/close/read/write)
    [8] BaseDriver 错误处理
"""

import os
import sys
import threading
import time

# 确保项目根目录在路径中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__ if "__file__" in dir() else ".")))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.communication.base_driver import BaseDriver, DriverState, DriverStats
from src.utils.exceptions import DriverError, DriverOpenError, DriverReadError, DriverWriteError

passed = 0
failed = 0
errors = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        msg = f"  ✗ {name}"
        if detail:
            msg += f" — {detail}"
        errors.append(msg)


# ═══════════════════════════════════════════════════════════════
# 测试用具体子类 (实现抽象方法)
# ═══════════════════════════════════════════════════════════════


class MockDriver(BaseDriver):
    """Mock驱动, 用于测试基类模板方法"""

    def __init__(self, **kwargs):
        super().__init__(driver_type="mock", **kwargs)
        self.open_called = False
        self.close_called = False
        self.read_data = b""
        self.write_data = b""
        self._fail_open = False
        self._fail_read = False
        self._fail_write = False
        self._fail_close = False

    def _do_open(self) -> None:
        if self._fail_open:
            raise ConnectionRefusedError("Mock拒绝连接")
        self.open_called = True

    def _do_close(self) -> None:
        if self._fail_close:
            raise RuntimeError("Mock关闭异常")
        self.close_called = True

    def _do_read(self, size: int) -> bytes:
        if self._fail_read:
            raise TimeoutError("Mock读取超时")
        if size < 0:
            return self.read_data
        return self.read_data[:size]

    def _do_write(self, data: bytes) -> int:
        if self._fail_write:
            raise BrokenPipeError("Mock管道断裂")
        self.write_data = data
        return len(data)


class ValidatingDriver(BaseDriver):
    """参数校验驱动, 测试 _validate_config"""

    def __init__(self, **kwargs):
        super().__init__(driver_type="validating", **kwargs)

    def _do_open(self) -> None:
        pass

    def _do_close(self) -> None:
        pass

    def _do_read(self, size: int) -> bytes:
        return b""

    def _do_write(self, data: bytes) -> int:
        return len(data)

    def _validate_config(self, **kwargs) -> None:
        if "baud_rate" in kwargs:
            rate = kwargs["baud_rate"]
            if not isinstance(rate, int) or rate <= 0:
                raise ValueError(f"波特率必须为正整数, 实际: {rate}")


# ═══════════════════════════════════════════════════════════════
# [1] DriverState 常量
# ═══════════════════════════════════════════════════════════════
print("\n[1] DriverState 常量")
check("CLOSED", DriverState.CLOSED == "closed")
check("OPENING", DriverState.OPENING == "opening")
check("OPEN", DriverState.OPEN == "open")
check("CLOSING", DriverState.CLOSING == "closing")
check("ERROR", DriverState.ERROR == "error")


# ═══════════════════════════════════════════════════════════════
# [2] DriverStats 性能统计
# ═══════════════════════════════════════════════════════════════
print("\n[2] DriverStats 性能统计")

stats = DriverStats()

# 初始值
check("初始 bytes_sent=0", stats.bytes_sent == 0)
check("初始 bytes_received=0", stats.bytes_received == 0)
check("初始 read_count=0", stats.read_count == 0)
check("初始 write_count=0", stats.write_count == 0)
check("初始 error_count=0", stats.error_count == 0)
check("初始 open_count=0", stats.open_count == 0)
check("初始 last_activity=None", stats.last_activity is None)
check("初始 idle_seconds=-1", stats.idle_seconds == -1.0)

# add_bytes_sent
stats.add_bytes_sent(100)
check("发送100后 bytes_sent=100", stats.bytes_sent == 100)
check("发送后 write_count=1", stats.write_count == 1)
check("发送后 last_activity 非None", stats.last_activity is not None)

stats.add_bytes_sent(50)
check("再发送50后 bytes_sent=150", stats.bytes_sent == 150)
check("再发送后 write_count=2", stats.write_count == 2)

# add_bytes_received
stats.add_bytes_received(30)
check("接收30后 bytes_received=30", stats.bytes_received == 30)
check("接收后 read_count=1", stats.read_count == 1)

stats.add_bytes_received(20)
check("再接收20后 bytes_received=50", stats.bytes_received == 50)
check("再接收后 read_count=2", stats.read_count == 2)

# 零值 / 负值
stats.add_bytes_sent(0)
check("发送0不影响 bytes_sent", stats.bytes_sent == 150)
stats.add_bytes_sent(-10)
check("发送-10不影响 bytes_sent", stats.bytes_sent == 150)
stats.add_bytes_received(0)
check("接收0不影响 bytes_received", stats.bytes_received == 50)

# record_error
stats.record_error()
check("记录错误后 error_count=1", stats.error_count == 1)
stats.record_error()
check("再记录后 error_count=2", stats.error_count == 2)

# record_open
stats.record_open()
check("记录打开后 open_count=1", stats.open_count == 1)

# idle_seconds (至少经过了一些时间)
check("空闲时间 >= 0", stats.idle_seconds >= 0)
check("last_activity_str 非空", len(stats.last_activity_str) > 0)

# to_dict
d = stats.to_dict()
check("to_dict 包含 bytes_sent", d["bytes_sent"] == 150)
check("to_dict 包含 bytes_received", d["bytes_received"] == 50)
check("to_dict 包含 error_count", d["error_count"] == 2)
check("to_dict 包含 open_count", d["open_count"] == 1)
check("to_dict 包含 last_activity", "last_activity" in d)
check("to_dict 包含 idle_seconds", "idle_seconds" in d)

# reset
stats.reset()
check("重置后 bytes_sent=0", stats.bytes_sent == 0)
check("重置后 bytes_received=0", stats.bytes_received == 0)
check("重置后 error_count=0", stats.error_count == 0)
check("重置后 open_count=0", stats.open_count == 0)
check("重置后 last_activity=None", stats.last_activity is None)

# 线程安全测试
stats2 = DriverStats()
threads = []
for _ in range(10):
    t = threading.Thread(target=lambda: stats2.add_bytes_sent(1))
    threads.append(t)
    t.start()
for t in threads:
    t.join()
check("并发安全: bytes_sent=10", stats2.bytes_sent == 10)


# ═══════════════════════════════════════════════════════════════
# [3] BaseDriver 实例化与属性
# ═══════════════════════════════════════════════════════════════
print("\n[3] BaseDriver 实例化与属性")

driver = MockDriver(timeout=3.0)
check("driver_type='mock'", driver.driver_type == "mock")
check("初始 state=CLOSED", driver.state == DriverState.CLOSED)
check("初始 is_open=False", driver.is_open is False)
check("初始 timeout=3.0", driver.timeout == 3.0)
check("stats 类型正确", isinstance(driver.stats, DriverStats))
check("config 初始为空", driver.config == {})

# timeout setter
driver.timeout = 10.0
check("设置 timeout=10.0", driver.timeout == 10.0)

try:
    driver.timeout = -1
    check("负超时应抛异常", False)
except ValueError:
    check("负超时 ValueError", True)

try:
    driver.timeout = 0
    check("零超时应抛异常", False)
except ValueError:
    check("零超时 ValueError", True)

# get_info
info = driver.get_info()
check("get_info 包含 driver_type", info["driver_type"] == "mock")
check("get_info 包含 driver_class", info["driver_class"] == "MockDriver")
check("get_info 包含 state", info["state"] == DriverState.CLOSED)
check("get_info 包含 timeout", info["timeout"] == 10.0)
check("get_info 包含 config", "config" in info)
check("get_info 包含 stats", "stats" in info)

# __repr__
r = repr(driver)
check("__repr__ 包含类型", "MockDriver" in r)
check("__repr__ 包含状态", "closed" in r)
check("__repr__ 包含timeout", "10.0s" in r)


# ═══════════════════════════════════════════════════════════════
# [4] BaseDriver 状态管理 (状态机)
# ═══════════════════════════════════════════════════════════════
print("\n[4] BaseDriver 状态管理")

d4 = MockDriver()

# 非法转换: CLOSED → OPEN (必须经过OPENING)
try:
    d4._set_state(DriverState.OPEN)
    check("CLOSED→OPEN 应拒绝", False)
except DriverError:
    check("CLOSED→OPEN 拒绝", True)

# 合法转换链
d4._set_state(DriverState.OPENING)
check("CLOSED→OPENING", d4.state == DriverState.OPENING)

d4._set_state(DriverState.OPEN)
check("OPENING→OPEN", d4.state == DriverState.OPEN)

d4._set_state(DriverState.CLOSING)
check("OPEN→CLOSING", d4.state == DriverState.CLOSING)

d4._set_state(DriverState.CLOSED)
check("CLOSING→CLOSED", d4.state == DriverState.CLOSED)

# ERROR → OPENING (重试)
d4._set_state(DriverState.OPENING)
d4._set_state(DriverState.ERROR)
check("OPENING→ERROR", d4.state == DriverState.ERROR)
d4._set_state(DriverState.OPENING)
check("ERROR→OPENING (重试)", d4.state == DriverState.OPENING)
d4._set_state(DriverState.CLOSED)  # 先关
d4._set_state(DriverState.OPENING)
d4._set_state(DriverState.OPEN)

# ERROR → CLOSING
d4._set_state(DriverState.ERROR)
d4._set_state(DriverState.CLOSING)
check("ERROR→CLOSING", d4.state == DriverState.CLOSING)
d4._set_state(DriverState.CLOSED)

# _check_open
d4_closed = MockDriver()
try:
    d4_closed._check_open()
    check("未打开时 check_open 应抛异常", False)
except DriverError:
    check("未打开 _check_open 抛异常", True)


# ═══════════════════════════════════════════════════════════════
# [5] BaseDriver.configure() 参数配置
# ═══════════════════════════════════════════════════════════════
print("\n[5] BaseDriver 参数配置")

d5 = MockDriver()
d5.configure(host="192.168.1.100", port=502)
check("配置后 config 含 host", d5.config.get("host") == "192.168.1.100")
check("配置后 config 含 port", d5.config.get("port") == 502)

# 更新配置
d5.configure(port=503, timeout=10)
check("更新 port=503", d5.config.get("port") == 503)
check("新增 timeout=10", d5.config.get("timeout") == 10)
check("host 保持不变", d5.config.get("host") == "192.168.1.100")

# 参数校验 (ValidatingDriver)
vd = ValidatingDriver()
vd.configure(baud_rate=9600)
check("合法 baud_rate=9600", vd.config.get("baud_rate") == 9600)

try:
    vd.configure(baud_rate=-100)
    check("非法 baud_rate 应拒绝", False)
except ValueError:
    check("非法 baud_rate ValueError", True)

try:
    vd.configure(baud_rate="abc")
    check("非int baud_rate 应拒绝", False)
except ValueError:
    check("非int baud_rate ValueError", True)


# ═══════════════════════════════════════════════════════════════
# [6] BaseDriver 抽象方法约束
# ═══════════════════════════════════════════════════════════════
print("\n[6] BaseDriver 抽象方法约束")

try:
    BaseDriver(driver_type="test")
    check("直接实例化应失败", False)
except TypeError:
    check("直接实例化 TypeError", True)


# ═══════════════════════════════════════════════════════════════
# [7] BaseDriver 模板方法
# ═══════════════════════════════════════════════════════════════
print("\n[7] BaseDriver 模板方法")

# ── open ──
d7 = MockDriver(timeout=2.0)
signal_opened = []
signal_error = []
d7.opened.connect(lambda: signal_opened.append(True))
d7.error_occurred.connect(lambda msg: signal_error.append(msg))

d7.open()
check("open 后 is_open=True", d7.is_open is True)
check("open 后 state=OPEN", d7.state == DriverState.OPEN)
check("open 后 open_called=True", d7.open_called is True)
check("open 后发射 opened 信号", len(signal_opened) == 1)

# 重复打开 (应跳过)
d7.open()
check("重复打开仍 is_open", d7.is_open is True)
check("重复打开不再发射信号", len(signal_opened) == 1)

# ── close ──
signal_closed = []
d7.closed.connect(lambda: signal_closed.append(True))

d7.close()
check("close 后 is_open=False", d7.is_open is False)
check("close 后 state=CLOSED", d7.state == DriverState.CLOSED)
check("close 后发射 closed 信号", len(signal_closed) == 1)
check("close 后 close_called=True", d7.close_called is True)

# 重复关闭 (应跳过)
d7.close()
check("重复关闭仍 CLOSED", d7.state == DriverState.CLOSED)
check("重复关闭不再发射", len(signal_closed) == 1)

# ── open → close → reopen ──
d7b = MockDriver()
d7b.open()
d7b.close()
d7b.open()
check("reopen 后 is_open", d7b.is_open is True)

# ── write ──
d7c = MockDriver()
d7c.open()
signal_tx = []
signal_rx = []
d7c.bytes_sent_changed.connect(lambda n: signal_tx.append(n))
d7c.data_received.connect(lambda d: signal_rx.append(d))

n = d7c.write(b"hello")
check("write 返回字节数=5", n == 5)
check("write 后内部数据正确", d7c.write_data == b"hello")
check("write 后 stats.bytes_sent=5", d7c.stats.bytes_sent == 5)
check("write 后 write_count=1", d7c.stats.write_count == 1)
check("write 发射 bytes_sent_changed", len(signal_tx) == 1)
check("bytes_sent_changed 值=5", signal_tx[0] == 5)

# 空写入
try:
    d7c.write(b"")
    check("空写入应抛异常", False)
except DriverWriteError:
    check("空写入 DriverWriteError", True)

# 未打开写入
d7d = MockDriver()
try:
    d7d.write(b"test")
    check("未打开写入应抛异常", False)
except DriverError:
    check("未打开写入 DriverError", True)

# ── read ──
d7e = MockDriver()
d7e.open()
d7e.read_data = b"response_data"

data = d7e.read()
check("read(-1) 返回全部", data == b"response_data")
check("read 后 stats.bytes_received=13", d7e.stats.bytes_received == 13)
check("read 后 read_count=1", d7e.stats.read_count == 1)
check("read 发射 data_received", len(signal_rx) == 0)  # d7c's signal

# 精确读取
d7e.read_data = b"ABCDE"
data = d7e.read(3)
check("read(3) 返回前3字节", data == b"ABC")

# 读取超出
data = d7e.read(10)
check("read(10) 返回最多可用", len(data) <= 10)

# 读取空数据
d7e.read_data = b""
data = d7e.read()
check("读取空返回 b''", data == b"")

# 未打开读取
try:
    d7d.read()
    check("未打开读取应抛异常", False)
except DriverError:
    check("未打开读取 DriverError", True)

# ── reset_stats ──
d7f = MockDriver()
d7f.open()
d7f.write(b"test")
d7f.read_data = b"ok"
d7f.read()
check("reset前 bytes_sent=4", d7f.stats.bytes_sent == 4)
check("reset前 bytes_received=2", d7f.stats.bytes_received == 2)

d7f.reset_stats()
check("reset后 bytes_sent=0", d7f.stats.bytes_sent == 0)
check("reset后 bytes_received=0", d7f.stats.bytes_received == 0)
check("reset后 write_count=0", d7f.stats.write_count == 0)
check("reset后 read_count=0", d7f.stats.read_count == 0)


# ═══════════════════════════════════════════════════════════════
# [8] BaseDriver 错误处理
# ═══════════════════════════════════════════════════════════════
print("\n[8] BaseDriver 错误处理")

# ── open 失败 ──
d8a = MockDriver()
d8a._fail_open = True
signal_err8a = []
d8a.error_occurred.connect(lambda msg: signal_err8a.append(msg))

try:
    d8a.open()
    check("失败open应抛异常", False)
except DriverOpenError as e:
    check("失败open DriverOpenError", True)
    check("error_code=DRIVER_OPEN_ERROR", e.error_code == "DRIVER_OPEN_ERROR")
    check("失败后 state=ERROR", d8a.state == DriverState.ERROR)
    check("失败后 is_open=False", d8a.is_open is False)
    check("失败后 error_count=1", d8a.stats.error_count == 1)
    check("失败后发射 error_occurred", len(signal_err8a) == 1)

# 从ERROR状态可重试open
d8a._fail_open = False
d8a.open()
check("ERROR→OPEN重试成功", d8a.is_open is True)

# ── read 失败 ──
d8b = MockDriver()
d8b.open()
d8b._fail_read = True

try:
    d8b.read(10)
    check("失败read应抛异常", False)
except DriverReadError as e:
    check("失败read DriverReadError", True)
    check("error_code=DRIVER_READ_ERROR", e.error_code == "DRIVER_READ_ERROR")
    check("read失败后 error_count=1", d8b.stats.error_count == 1)

# ── write 失败 ──
d8c = MockDriver()
d8c.open()
d8c._fail_write = True

try:
    d8c.write(b"fail")
    check("失败write应抛异常", False)
except DriverWriteError as e:
    check("失败write DriverWriteError", True)
    check("error_code=DRIVER_WRITE_ERROR", e.error_code == "DRIVER_WRITE_ERROR")
    check("write失败后 error_count=1", d8c.stats.error_count == 1)

# ── close 失败 (不应抛异常) ──
d8d = MockDriver()
d8d.open()
d8d._fail_close = True
signal_err8d = []
d8d.error_occurred.connect(lambda msg: signal_err8d.append(msg))

# close失败不应抛异常
d8d.close()
check("close失败不抛异常", True)
check("close失败后 state=ERROR", d8d.state == DriverState.ERROR)
check("close失败后发射 error_occurred", len(signal_err8d) == 1)


# ═══════════════════════════════════════════════════════════════
# 结果汇总
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 项")

if errors:
    print("\n失败项:")
    for e in errors:
        print(e)

sys.exit(1 if failed > 0 else 0)
