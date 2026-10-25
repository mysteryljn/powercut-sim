# powercut-sim

模拟 OTA/配置事务在任意断电点发生时的提交和恢复。它用内存中的 journal、临时版本和提交标记验证：断电后不会把半个更新暴露成活动版本，并输出可审查的恢复结果。

## 痛点

R156 要求软件更新安全、可验证并能处理失败或中断回滚；真实断电测试昂贵而且难以覆盖所有切点。本项目用确定性故障注入先验证状态机和恢复不变量。

## 使用

    python powercut.py --chunks 4 --cut-after 2
    python powercut.py --chunks 4

## 许可证

MIT
