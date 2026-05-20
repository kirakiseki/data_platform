#!/usr/bin/env python3
"""
JLD2 数据解析器

忠实呈现原始 JLD2 文件中的 Trip 数据结构：
- 10 个字段与 Trip.jl 完全对应
- 保留原始数据类型和嵌套结构

字段索引 (来自 Trip.jl):
  0: lon           - 经度 Vector{Float64}
  1: lat           - 纬度 Vector{Float64}
  2: tms           - Unix时间戳 Vector{Float64}
  3: devid         - 设备/出租车ID Any
  4: roads         - 匹配的道路ID Vector{Int}
  5: time          - 匹配后的时间戳 Vector
  6: frac          - 道路位置比例 Vector
  7: route         - 完整路径道路序列 Vector{Int}
  8: route_heading - 道路朝向 Vector
  9: route_geom    - WKT几何格式 Vector{String}
"""

import os
import h5py
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Any


# 字段定义 (与 Trip.jl 完全对应)
FIELD_DEFS = [
    ('lon', 'Vector{Float64}', '经度'),
    ('lat', 'Vector{Float64}', '纬度'),
    ('tms', 'Vector{Float64}', 'Unix时间戳'),
    ('devid', 'Any', '设备/出租车ID'),
    ('roads', 'Vector{Int}', '匹配的道路ID '),
    ('time', 'Vector', '匹配后时间戳 '),
    ('frac', 'Vector', '道路位置比例 '),
    ('route', 'Vector{Int}', '完整路径 '),
    ('route_heading', 'Vector', '路径朝向 '),
    ('route_geom', 'Vector{String}', 'WKT几何 '),
]


@dataclass
class Trip:
    """Trip 数据结构，与 Julia Trip.jl 完全对应"""
    lon: np.ndarray      # Vector{Float64}
    lat: np.ndarray      # Vector{Float64}
    tms: np.ndarray      # Vector{Float64}
    devid: Any           # Any
    roads: Optional[np.ndarray] = None  # Vector{Int}
    time: Optional[np.ndarray] = None   # Vector
    frac: Optional[np.ndarray] = None   # Vector
    route: Optional[np.ndarray] = None          # Vector{Int}
    route_heading: Optional[np.ndarray] = None  # Vector
    route_geom: Optional[np.ndarray] = None    # Vector{String}

    @property
    def n_points(self) -> int:
        """返回 GPS 点数量"""
        return len(self.lon)


def read_raw_field(f, field_ref, field_name: str):
    """
    读取字段，处理各种嵌套引用和类型

    Parameters:
        f: h5py.File 对象
        field_ref: HDF5 引用
        field_name: 字段名（用于特殊处理）

    Returns:
        原始数据（可能是 ndarray, 标量, 或 bytes）
    """
    try:
        field_obj = f[field_ref]
        data = field_obj[()]

        # 如果是标量，直接返回
        if not hasattr(data, '__len__') or data.shape == ():
            return data

        # 检查是否是空数组
        if data.size == 0:
            return data

        # 检查 dtype
        if data.dtype == object:
            # 处理 bytes 数组 (Julia String -> bytes)
            # 需要处理 2D 数组的情况（如 route_geom 可能是 shape=(1, N)）
            try:
                first = data.flat[0] if data.size > 0 else None
            except:
                first = None

            if first is not None and isinstance(first, (bytes, np.bytes_)):
                # 解码 bytes 数组为字符串列表（处理 2D 数组）
                decoded = []
                for item in data.flat:
                    if isinstance(item, bytes):
                        decoded.append(item.decode('utf-8', errors='replace'))
                    elif isinstance(item, np.ndarray):
                        # 处理嵌套数组（如 route_geom）
                        sub_decoded = []
                        for sub_item in item:
                            if isinstance(sub_item, bytes):
                                sub_decoded.append(sub_item.decode('utf-8', errors='replace'))
                            else:
                                sub_decoded.append(sub_item)
                        decoded.append(sub_decoded)
                    else:
                        decoded.append(item)
                # 如果是 2D 数组，保持形状
                if len(data.shape) > 1:
                    return np.array(decoded, dtype=object).reshape(data.shape)
                return np.array(decoded)

            # 检查是否有嵌套引用 (如 frac 字段)
            if first is not None and isinstance(first, h5py.h5r.Reference):
                resolved = []
                for item in data.flat:
                    if isinstance(item, h5py.h5r.Reference):
                        resolved.append(float(f[item][()]))
                    else:
                        resolved.append(item)
                return np.array(resolved)

        return data
    except Exception as e:
        print(f"    读取字段 {field_name} 失败: {e}")
        return None


def read_trip(f, trip_ref) -> Optional[Trip]:
    """
    从 JLD2 文件读取单个 Trip

    Parameters:
        f: h5py.File 对象
        trip_ref: trips 数组中的引用

    Returns:
        Trip 对象，或 None 如果读取失败
    """
    try:
        trip_obj = f[trip_ref]
        trip_data = trip_obj[()]

        # trip_data 是 numpy.void，使用字段名访问
        fields = {}
        for field_name, _, _ in FIELD_DEFS:
            try:
                field_ref = trip_data[field_name]
                if isinstance(field_ref, h5py.h5r.Reference):
                    data = read_raw_field(f, field_ref, field_name)
                else:
                    data = field_ref
                fields[field_name] = data
            except Exception as e:
                fields[field_name] = None

        # 构建 Trip 对象
        return Trip(
            lon=_safe_to_array(fields.get('lon')),
            lat=_safe_to_array(fields.get('lat')),
            tms=_safe_to_array(fields.get('tms')),
            devid=fields.get('devid'),
            roads=_safe_to_array(fields.get('roads')),
            time=_safe_to_array(fields.get('time')),
            frac=_safe_to_array(fields.get('frac')),
            route=_safe_to_array(fields.get('route')),
            route_heading=_safe_to_array(fields.get('route_heading')),
            route_geom=_safe_to_array(fields.get('route_geom')),
        )
    except Exception as e:
        return None


def _safe_to_array(data):
    """安全转换为 numpy 数组"""
    if data is None:
        return None
    if isinstance(data, np.ndarray):
        return data
    try:
        return np.array(data)
    except:
        return None


def load_jld2(file_path: str, max_trips: int = None) -> List[Trip]:
    """
    加载 JLD2 文件

    Parameters:
        file_path: JLD2 文件路径
        max_trips: 最大加载行程数

    Returns:
        Trip 对象列表
    """
    trips = []

    with h5py.File(file_path, 'r') as f:
        trips_dataset = f['trips']
        total = trips_dataset.shape[0]

        if max_trips:
            total = min(total, max_trips)

        print(f"加载 {total} 个行程...")

        for i in range(total):
            trip = read_trip(f, trips_dataset[i])
            if trip is not None:
                trips.append(trip)

            if (i + 1) % 10000 == 0:
                print(f"  已加载 {i+1}/{total}")

    print(f"完成，成功加载 {len(trips)} 个行程")
    return trips


def inspect_trip(trip: Trip, trip_id: int = 0):
    """打印 Trip 详细信息"""
    print(f"\n{'='*70}")
    print(f"Trip {trip_id}")
    print(f"{'='*70}")

    for field_name, julia_type, description in FIELD_DEFS:
        value = getattr(trip, field_name)
        print(f"\n{field_name:15s} ({julia_type}) - {description}")

        if value is None:
            print("  值: None")
        elif isinstance(value, np.ndarray):
            print(f"  类型: ndarray, shape={value.shape}, dtype={value.dtype}")
            if len(value) > 0:
                # 显示样本
                sample = value[:min(5, len(value))]
                if value.dtype == object and isinstance(sample[0], str):
                    print(f"  样本 (前5个字符串):")
                    for j, s in enumerate(sample):
                        print(f"    [{j}]: {s[:80]}..." if len(s) > 80 else f"    [{j}]: {s}")
                else:
                    print(f"  样本 (前5个): {sample}")
        else:
            print(f"  值: {value}")


def inspect_jld2(file_path: str, trip_indices: List[int] = None):
    """
    探索 JLD2 文件

    Parameters:
        file_path: JLD2 文件路径
        trip_indices: 要查看的行程索引列表
    """
    print(f"\n{'='*70}")
    print(f"📄 文件: {os.path.basename(file_path)}")
    print(f"💾 大小: {os.path.getsize(file_path) / (1024*1024*1024):.2f} GB")
    print(f"{'='*70}")

    with h5py.File(file_path, 'r') as f:
        trips_dataset = f['trips']
        n_trips = trips_dataset.shape[0]
        print(f"\n总行程数: {n_trips:,}")

        # 如果没有指定索引，显示默认的几个
        if trip_indices is None:
            trip_indices = [0, n_trips // 4, n_trips // 2, n_trips * 3 // 4, n_trips - 1]

        # 加载指定的 trips
        for idx in trip_indices:
            if idx >= n_trips:
                continue
            trip = read_trip(f, trips_dataset[idx])
            if trip:
                inspect_trip(trip, idx)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='JLD2 数据解析器')
    parser.add_argument('--input', '-i', default='datasets/processed_traj/trips_150103.jld2',
                        help='JLD2 文件路径')
    parser.add_argument('--trip', '-t', type=int, nargs='+',
                        help='要查看的 trip 索引')
    parser.add_argument('--max', '-n', type=int, default=None,
                        help='最大加载行程数')

    args = parser.parse_args()

    if args.trip:
        # 探索模式
        inspect_jld2(args.input, args.trip)
    else:
        # 加载全部
        trips = load_jld2(args.input, args.max)
        if trips:
            inspect_trip(trips[0], 0)


if __name__ == "__main__":
    main()