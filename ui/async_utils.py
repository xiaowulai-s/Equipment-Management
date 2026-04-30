# -*- coding: utf-8 -*-
"""
异步工具集 (Async Utilities)

提供非阻塞的延迟和等待功能，替代 time.sleep() 避免阻塞GUI线程。

使用示例:
    from ui.async_utils import async_sleep, run_async

    # 异步延迟（不阻塞GUI）
    await async_sleep(1.0)  # 在协程中使用
    async_sleep(1.0, callback=my_function)  # 使用回调

    # 在非协程代码中
    run_async(my_heavy_task)  # 后台运行
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional, Any
from functools import wraps

from PySide6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QObject,
    QTimer,
    Qt,
    QRunnable,
    QThreadPool,
)

logger = logging.getLogger(__name__)


def async_sleep(seconds: float, callback: Optional[Callable] = None, *args, **kwargs) -> None:
    """
    非阻塞延迟执行

    在Qt事件循环中实现延迟，不会冻结GUI。

    Args:
        seconds: 延迟秒数（支持小数）
        callback: 延迟结束后要调用的函数（可选）
        *args, **kwargs: 传递给callback的参数

    使用示例:
        # 简单延迟
        async_sleep(2.0)

        # 带回调的延迟
        async_sleep(1.0, callback=self.refresh_data)

        # 带参数的回调
        async_sleep(0.5, callback=self.update_status, status="completed")
    """
    if callback is None:
        QTimer.singleShot(int(seconds * 1000), lambda: None)
    else:
        QTimer.singleShot(int(seconds * 1000), lambda: callback(*args, **kwargs))


def async_wait(ms: int = 0) -> None:
    """
    同步等待但保持事件循环响应

    用于需要短暂等待但不希望阻塞GUI的场景。
    注意：此函数仍会阻塞当前代码执行，但保持UI响应。

    Args:
        ms: 等待毫秒数

    使用示例:
        def on_click(self):
            do_something()
            async_wait(500)  # 等待500ms，期间UI仍可响应
            do_something_else()
    """
    if ms <= 0:
        return

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class AsyncWorker(QRunnable):
    """
    异步工作器 - 在后台线程运行任务

    使用示例:
        worker = AsyncWorker(heavy_computation, arg1, arg2)
        worker.signals.result.connect(self.on_result)
        worker.signals.error.connect(self.on_error)
        QThreadPool.globalInstance().start(worker)
    """

    class Signals(QObject):
        result = object()
        error = object()
        finished = object()
        progress = object()

    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = self.Signals()

    def run(self) -> None:
        """在后台线程中执行任务"""
        try:
            result = self.func(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            logger.error("AsyncWorker 任务执行失败: %s", str(e), exc_info=True)
            self.signals.error.emit(e)
        finally:
            self.signals.finished.emit()


def run_async(
    func: Callable,
    on_success: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
    on_finished: Optional[Callable] = None,
    *args,
    **kwargs,
) -> AsyncWorker:
    """
    在后台线程池中异步运行函数

    Args:
        func: 要执行的函数
        on_success: 成功回调 (result) -> None
        on_error: 错误回调 (exception) -> None
        on_finished: 完成回调 () -> None
        *args, **kwargs: 传递给func的参数

    Returns:
        AsyncWorker: 工作器实例（可用于取消等操作）

    使用示例:
        def heavy_calculation(x, y):
            time.sleep(2)  # 模拟耗时操作
            return x + y

        def on_result(result):
            print(f"计算结果: {result}")

        def on_error(error):
            print(f"出错: {error}")

        # 启动异步任务
        run_async(heavy_calculation, on_success=on_result, on_error=on_error, 10, 20)
    """
    worker = AsyncWorker(func, *args, **kwargs)

    if on_success:
        worker.signals.result.connect(on_success)
    if on_error:
        worker.signals.error.connect(on_error)
    if on_finished:
        worker.signals.finished.connect(on_finished)

    QThreadPool.globalInstance().start(worker)
    return worker


def debounce(delay_ms: int = 300) -> Callable:
    """
    防抖装饰器

    在指定时间内多次调用只执行最后一次。
    适用于搜索输入、窗口resize等场景。

    Args:
        delay_ms: 延迟时间（毫秒）

    使用示例:
        @debounce(500)
        def on_search_text_changed(self, text):
            self.perform_search(text)
    """

    def decorator(func: Callable) -> Callable:
        timer = None

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal timer

            if timer is not None:
                timer.stop()

            timer = QTimer()
            timer.setSingleShot(True)
            timeout_func = lambda: func(*args, **kwargs)
            timer.timeout.connect(timeout_func)
            timer.start(delay_ms)

        return wrapper

    return decorator


def throttle(min_interval_ms: int = 1000) -> Callable:
    """
    节流装饰器

    在指定时间内只执行一次，忽略后续调用。
    适用于按钮点击、滚动事件等场景。

    Args:
        min_interval_ms: 最小间隔（毫秒）

    使用示例:
        @throttle(2000)
        def on_save_button_clicked(self):
            self.save_data()
    """

    def decorator(func: Callable) -> Callable:
        last_call_time = [0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            from time import time

            current_time = int(time() * 1000)

            if current_time - last_call_time[0] >= min_interval_ms:
                last_call_time[0] = current_time
                func(*args, **kwargs)

        return wrapper

    return decorator


class RetryDecorator:
    """
    重试装饰器类 - 自动重试失败的函数

    使用示例:
        @RetryDecorator(max_retries=3, delay=1.0, backoff=2.0)
        def unstable_operation():
            ...
    """

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,),
        on_retry: Optional[Callable] = None,
    ):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.on_retry = on_retry

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            exception = None
            current_delay = self.delay

            for attempt in range(self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    exception = e

                    if attempt < self.max_retries:
                        logger.warning(
                            "第 %d/%d 次重试 %s(): %s",
                            attempt + 1,
                            self.max_retries,
                            func.__name__,
                            str(e),
                        )

                        if self.on_retry:
                            self.on_retry(attempt + 1, e)

                        async_wait(int(current_delay * 1000))
                        current_delay *= self.backoff
                    else:
                        logger.error(
                            "%s() 在 %d 次尝试后仍然失败: %s",
                            func.__name__,
                            self.max_retries,
                            str(e),
                        )

            raise exception

        return wrapper


if __name__ == "__main__":
    print("✅ Async Utilities 加载成功")
    print("\n📦 可用功能:")
    print("  - async_sleep(): 非阻塞延迟")
    print("  - async_wait(): 保持响应的同步等待")
    print("  - run_async(): 后台线程执行")
    print("  - debounce(): 防抖装饰器")
    print("  - throttle(): 节流装饰器")
    print("  - RetryDecorator: 自动重试装饰器")
