# -*- coding: utf-8 -*-
"""
设备轮询逻辑单元测试
Unit Tests for Device Polling Logic
"""

import pytest
import time

from core.device.polling import (
    DevicePollInfo,
    FaultInfo,
    PollPriority,
    PollStatistics,
    RecoveryConfig,
)


class TestPollStatistics:
    """轮询统计信息测试"""

    def test_initial_state(self):
        """测试初始状态"""
        stats = PollStatistics()

        assert stats.total_polls == 0
        assert stats.successful_polls == 0
        assert stats.failed_polls == 0
        assert len(stats.response_times) == 0

    def test_record_success(self):
        """测试记录成功轮询"""
        stats = PollStatistics()
        stats.record_success(50.5)

        assert stats.total_polls == 1
        assert stats.successful_polls == 1
        assert stats.failed_polls == 0
        assert len(stats.response_times) == 1
        assert stats.response_times[0] == 50.5

    def test_record_failure(self):
        """测试记录失败轮询"""
        stats = PollStatistics()
        stats.record_failure()

        assert stats.total_polls == 1
        assert stats.failed_polls == 1
        assert stats.successful_polls == 0

    def test_success_rate(self):
        """测试成功率计算"""
        stats = PollStatistics()

        # 初始状态
        assert stats.success_rate == 0.0

        # 添加一些成功和失败记录
        for _ in range(7):
            stats.record_success()
        for _ in range(3):
            stats.record_failure()

        expected_rate = 7 / 10
        assert abs(stats.success_rate - expected_rate) < 0.001

    def test_avg_response_time(self):
        """测试平均响应时间计算"""
        stats = PollStatistics()

        # 初始状态
        assert stats.avg_response_time == 0.0

        # 添加响应时间
        times = [10, 20, 30, 40, 50]
        for t in times:
            stats.record_success(t)

        expected_avg = sum(times) / len(times)
        assert abs(stats.avg_response_time - expected_avg) < 0.001

    def test_response_times_maxlen(self):
        """测试响应时间队列最大长度"""
        stats = PollStatistics()

        for i in range(15):
            stats.record_success(float(i))

        assert len(stats.response_times) == 10
        assert stats.response_times[-1] == 14.0


class TestFaultInfo:
    """故障诊断信息测试"""

    def test_initial_state(self):
        """测试初始状态"""
        fault = FaultInfo()

        assert fault.fault_type is None
        assert fault.fault_start_time is None
        assert fault.fault_duration == 0
        assert len(fault.error_history) == 0
        assert fault.fault_detection_enabled is True

    def test_detect_fault_first_occurrence(self):
        """测试首次故障检测"""
        fault = FaultInfo()
        fault.detect_fault("communication_timeout", "连接超时", "DEV001")

        assert fault.fault_type == "communication_timeout"
        assert fault.fault_start_time is not None
        assert len(fault.error_history) == 1

    def test_detect_fault_disabled(self):
        """测试禁用故障检测"""
        fault = FaultInfo(fault_detection_enabled=False)
        fault.detect_fault("timeout", "超时", "DEV001")

        assert fault.fault_type is None
        assert len(fault.error_history) == 0

    def test_clear_fault_with_active_fault(self):
        """测试清除活跃故障"""
        fault = FaultInfo()
        fault.detect_fault("connection_refused", "拒绝连接", "DEV002")

        summary = fault.clear_fault("DEV002")

        assert "fault_type" in summary
        assert summary["fault_type"] == "connection_refused"
        assert fault.fault_type is None
        assert fault.fault_start_time is None

    def test_clear_fault_no_active_fault(self):
        """测试清除无活跃故障"""
        fault = FaultInfo()
        summary = fault.clear_fault("DEV003")

        assert summary == {}

    def test_error_history_maxlen(self):
        """测试错误历史最大长度"""
        fault = FaultInfo()

        for i in range(25):
            fault.detect_fault(f"error_{i}", f"msg_{i}", "DEV004")

        assert len(fault.error_history) == 20


class TestRecoveryConfig:
    """恢复配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = RecoveryConfig()

        assert config.recovery_mode == "auto"
        assert config.max_recovery_attempts == 5
        assert config.auto_reconnect_enabled is False
        assert config.recovery_enabled is True
        assert config.recovery_status == "none"
        assert config.recovery_attempts == 0
        assert len(config.recovery_history) == 0

    def test_custom_config(self):
        """测试自定义配置"""
        config = RecoveryConfig(
            recovery_mode="manual",
            max_recovery_attempts=10,
            auto_reconnect_enabled=True,
        )

        assert config.recovery_mode == "manual"
        assert config.max_recovery_attempts == 10
        assert config.auto_reconnect_enabled is True


class TestDevicePollInfo:
    """设备轮询信息核心逻辑测试"""

    @pytest.fixture
    def poll_info(self, mock_device):
        return DevicePollInfo(mock_device, priority=PollPriority.NORMAL)

    def test_initial_state(self, poll_info):
        """测试初始状态"""
        assert poll_info.last_poll_time == 0
        assert poll_info.poll_interval == 1000
        assert poll_info.next_poll_time == 0
        assert poll_info.consecutive_errors == 0
        assert poll_info.max_errors == 3
        assert poll_info.backoff_time == 0

    def test_should_poll_ready(self, poll_info):
        """测试应该轮询(就绪状态)"""
        current_time = int(time.time() * 1000) + 2000
        result = poll_info.should_poll(current_time)
        assert result is True

    def test_should_poll_backoff(self, poll_info):
        """测试不应该轮询(退避状态)"""
        future_time = int(time.time() * 1000) + 60000
        poll_info.backoff_time = future_time

        current_time = int(time.time() * 1000)
        result = poll_info.should_poll(current_time)
        assert result is False

    def test_update_poll_time_basic(self, poll_info):
        """测试基本更新轮询时间"""
        current_time = 5000
        poll_info.update_poll_time(current_time)

        assert poll_info.last_poll_time == current_time
        assert poll_info.next_poll_time > current_time
        # 无响应时间时不记录成功统计
        assert poll_info.statistics.total_polls == 0

    def test_update_poll_time_with_response(self, poll_info):
        """测试带响应时间的更新"""
        current_time = 5000
        response_time = 45.5

        poll_info.update_poll_time(current_time, response_time)

        assert poll_info.statistics.successful_polls == 1
        assert len(poll_info.statistics.response_times) == 1
        assert abs(poll_info.statistics.response_times[0] - response_time) < 0.01

    def test_on_success_clears_errors(self, poll_info):
        """测试成功处理清除错误计数"""
        poll_info.consecutive_errors = 3
        poll_info.backoff_time = int(time.time() * 1000) + 5000

        poll_info.on_success()

        assert poll_info.consecutive_errors == 0
        assert poll_info.backoff_time == 0

    def test_on_error_increment_and_backoff(self, poll_info):
        """测试错误处理增加计数和退避"""
        initial_errors = poll_info.consecutive_errors

        for _ in range(poll_info.max_errors + 1):
            poll_info.on_error("timeout", "超时")

        assert poll_info.consecutive_errors > initial_errors
        if poll_info.consecutive_errors >= poll_info.max_errors:
            assert poll_info.backoff_time > 0

    def test_dynamic_interval_adjustment_fast(self, poll_info):
        """测试动态间隔调整(快速响应)"""
        # 记录多个快速响应
        for _ in range(5):
            poll_info.update_poll_time(int(time.time() * 1000), 20.0)

        # 快速响应应该减小间隔
        assert poll_info.poll_interval < 1000

    def test_dynamic_interval_adjustment_slow(self, poll_info):
        """测试动态间隔调整(慢速响应)"""
        # 设置目标响应时间
        poll_info.target_response_time = 50.0

        # 记录多个慢速响应
        for _ in range(5):
            poll_info.update_poll_time(int(time.time() * 1000), 150.0)

        # 慢速响应应该增大间隔
        assert poll_info.poll_interval > 1000

    def test_priority_based_default_interval(self, poll_info):
        """测试基于优先级的默认间隔"""
        high_priority = DevicePollInfo(poll_info.device, priority=PollPriority.HIGH)
        low_priority = DevicePollInfo(poll_info.device, priority=PollPriority.LOW)

        high_priority.update_poll_time(1000)
        low_priority.update_poll_time(1000)

        assert high_priority.poll_interval < low_priority.poll_interval


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
