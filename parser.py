"""文件名解析 & CSV 解析模块"""

import os
import re

# 文件名字段映射（按 - 分割后的位置）
# 当前 7 字段 + 预留 5 个涵道字段，共 12 个
FIELD_NAMES = [
    "日期",           # 0
    "桨叶转向",       # 1  (CW/CCW)
    "电机型号",       # 2
    "桨叶材质",       # 3
    "批次",           # 4
    "桨叶序号",       # 5
    "运行序号",       # 6
    "涵道型号",       # 7  (预留)
    "涵道唇口半径",   # 8  (预留)
    "涵道延伸段长度", # 9  (预留)
    "涵道延伸段角度", # 10 (预留)
    "涵道间隙",       # 11 (预留)
]


def parse_filename(filepath: str) -> dict:
    """从文件名解析测试变量，缺失字段返回 None"""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    parts = basename.split("-")

    result = {}
    for i, field_name in enumerate(FIELD_NAMES):
        if i < len(parts):
            result[field_name] = parts[i].strip()
        else:
            result[field_name] = None
    return result


def parse_csv(filepath: str) -> tuple:
    """解析 MET-V6 CSV 文件

    Returns:
        (metadata: dict, data: list[dict])
        metadata 包含: 测试台型号, 测试台编号, 拉力方向, 扭矩方向, 环境温度, 环境湿度, 大气压, 空气密度, 测试时间
        data 为数据行列表，每行为 dict
    """
    with open(filepath, "r", encoding="utf-8-sig") as f:
        raw = f.read()

    metadata = _parse_metadata(raw)
    data = _parse_data(raw)
    return metadata, data


def _parse_metadata(raw: str) -> dict:
    """从原始文本中提取元数据"""
    metadata = {}

    patterns = {
        "测试台型号": r"测试台型号:,*\s*([^,\n]*)",
        "测试台编号": r"测试台编号:,*\s*([^,\n]*)",
        "拉力方向": r"拉力方向:,*\s*([^,\n]*)",
        "扭矩方向": r"扭矩方向:,*\s*([^,\n]*)",
        "环境温度": r"环境温度:,*\s*([^,\n]*)",
        "环境湿度": r"环境湿度:,*\s*([^,\n]*)",
        "大气压": r"大气压:,*\s*([^,\n]*)",
        "空气密度": r"空气密度:,*\s*([^,\n]*)",
        "测试时间": r"测试时间:,*\s*([^,\n]*)",
        "桨直径": r"桨直径:,*\s*([^,\n]*)",
        "测试模式": r"测试模式:,*\s*([^,\n]*)",
    }

    _unit_strip = {
        "环境温度": "℃",
        "环境湿度": "%RH",
        "空气密度": "kg/m³",
        "大气压": "kPa",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw)
        if match:
            value = match.group(1).strip()
            if key in _unit_strip:
                value = value.replace(_unit_strip[key], "").strip()
            metadata[key] = value

    return metadata


def _parse_data(raw: str) -> list:
    """从原始文本中提取数据行，找到列头后读取所有后续数据"""
    lines = raw.strip().split("\n")

    # 找到数据列头行
    header_idx = None
    for i, line in enumerate(lines):
        if "帧数" in line and "油门" in line:
            header_idx = i
            break

    if header_idx is None:
        return []

    # 解析列头
    header_line = lines[header_idx].strip()
    columns = [col.strip() for col in header_line.split(",")]

    # 解析数据行
    data = []
    for line in lines[header_idx + 1 :]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < len(columns):
            continue
        row = {}
        for j, col_name in enumerate(columns):
            value = parts[j].strip() if j < len(parts) else ""
            try:
                if value == "" or value == "-":
                    row[col_name] = None
                else:
                    row[col_name] = float(value)
            except ValueError:
                row[col_name] = value
        data.append(row)

    return data
