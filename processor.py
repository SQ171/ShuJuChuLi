"""数据处理模块：PWM分组、统计剔除异常值、汇总计算"""

import numpy as np


def process_file(filepath: str, metadata: dict, data: list, sigma: float = 2.5,
                 min_samples: int = 10):
    """处理单个文件的数据，返回最稳定油门段的汇总结果

    从所有稳态段中选出样本数最多的段（排除怠速 PWM=1000），
    对该段做 σ 剔除后求均值，作为该文件唯一输出。

    Args:
        filepath: CSV 文件路径
        metadata: parse_csv 返回的元数据
        data: parse_csv 返回的数据行列表
        sigma: 异常值剔除的 σ 系数
        min_samples: 稳定段最少保留的数据量

    Returns:
        dict or None: 最佳油门段的汇总结果
    """
    segments = _group_by_stable_segments(data)

    # 选出非怠速段中样本数最多的
    best_segment = None
    best_count = 0
    for segment_rows in segments:
        pwms = [r.get("PWM-μs") for r in segment_rows if r.get("PWM-μs") is not None]
        if not pwms:
            continue
        mean_pwm = np.mean(pwms)
        if mean_pwm <= 1010:  # 排除怠速段
            continue
        if len(segment_rows) > best_count:
            best_count = len(segment_rows)
            best_segment = segment_rows

    if best_segment is None or len(best_segment) < min_samples:
        return None

    segment_rows = best_segment

    thrusts = np.array([r["拉力-g"] for r in segment_rows if r.get("拉力-g") is not None])
    torques = np.array([r["扭矩-N•m"] for r in segment_rows if r.get("扭矩-N•m") is not None])
    powers = np.array([r["电功率-W"] for r in segment_rows if r.get("电功率-W") is not None])
    throttles = np.array([r["油门-%"] for r in segment_rows if r.get("油门-%") is not None])

    # 统计剔除异常值
    mask = _outlier_mask_multi([thrusts, torques, powers], sigma=sigma)
    mask &= (powers > 0)

    valid_thrusts = thrusts[mask]
    valid_torques = torques[mask]
    valid_powers = powers[mask]
    valid_throttles = throttles[mask]

    if len(valid_thrusts) < min_samples:
        return None

    efficiencies = valid_thrusts / valid_powers
    mean_pwm = int(round(np.mean([r["PWM-μs"] for r in segment_rows])))

    return {
        "PWM-μs": mean_pwm,
        "油门-%": round(float(np.mean(valid_throttles)), 2),
        "拉力-g": round(float(np.mean(valid_thrusts)), 1),
        "扭矩-N·m": round(float(np.mean(valid_torques)), 4),
        "电功率-W": round(float(np.mean(valid_powers)), 2),
        "拉力力效-g/W": round(float(np.mean(efficiencies)), 2),
        "样本数": len(valid_thrusts),
        "剔除数": len(thrusts) - len(valid_thrusts),
    }


def _group_by_stable_segments(data: list, pwm_tolerance: int = 2) -> list:
    """检测 PWM 稳态段，将连续且 PWM 变化不超过 tolerance 的行归为一段

    Returns:
        list[list]: 每个元素为一段稳态数据的行列表
    """
    # 按帧号排序（保证时间顺序）
    sorted_data = sorted(data, key=lambda r: r.get("帧数", 0))

    segments = []
    current_segment = []

    for row in sorted_data:
        pwm = row.get("PWM-μs")
        if pwm is None:
            continue

        if not current_segment:
            current_segment.append(row)
            continue

        last_pwm = current_segment[-1].get("PWM-μs")
        if last_pwm is not None and abs(pwm - last_pwm) <= pwm_tolerance:
            current_segment.append(row)
        else:
            segments.append(current_segment)
            current_segment = [row]

    if current_segment:
        segments.append(current_segment)

    return segments


def _outlier_mask_multi(arrays: list, sigma: float = 2.5) -> np.ndarray:
    """对多个指标数组联合做 σ 剔除，任一指偏离即标记为异常

    返回布尔 mask，True = 保留
    """
    n = len(arrays[0])
    mask = np.ones(n, dtype=bool)

    for arr in arrays:
        if len(arr) == 0:
            continue
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            continue
        lower = mean - sigma * std
        upper = mean + sigma * std
        mask &= (arr >= lower) & (arr <= upper)

    return mask
