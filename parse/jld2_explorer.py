#!/usr/bin/env python3
"""
JLD2 数据结构探索工具
功能：
  1. 查看文件基本信息（大小、行程数）
  2. 展示 HDF5 内部结构（_types, trips 等）
  3. 详细展示每个 trip 的字段
  4. 对比 H5 和 JLD2 数据结构

字段索引 (来自 Trip.jl):
  0: lon     - 经度 Vector{Float64}
  1: lat     - 纬度 Vector{Float64}
  2: tms     - Unix时间戳 Vector{Float64}
  3: devid   - 设备/出租车ID Any
  4: roads   - 匹配的道路ID Vector{Int}
  5: time    - 匹配后的时间戳 Vector
  6: frac    - 道路位置比例 (0-1) Vector
  7: route   - 完整路径道路序列 Vector{Int}
  8: route_heading - 道路朝向 Vector
  9: route_geom    - WKT几何格式 Vector{String}
"""

import os
import sys
import h5py
import numpy as np
from pathlib import Path


# 正确的字段顺序（来自 Trip.jl）
FIELD_NAMES = ['lon', 'lat', 'tms', 'devid', 'roads', 'time', 'frac',
               'route', 'route_heading', 'route_geom']

# 默认数据目录
DEFAULT_JLD2_DIR = "datasets/processed_traj"
DEFAULT_H5_DIR = "datasets/deepgtt-h5"


def print_jld2_info(file_path: str):
    """打印 JLD2 文件基本信息"""
    print(f"\n{'='*70}")
    print(f"📄 文件: {os.path.basename(file_path)}")
    print(f"💾 大小: {os.path.getsize(file_path) / (1024*1024*1024):.2f} GB")
    print(f"{'='*70}")

    with h5py.File(file_path, 'r') as f:
        # 根级别结构
        print("\n📁 根目录结构:")
        for key in f.keys():
            obj = f[key]
            if isinstance(obj, h5py.Group):
                print(f"  📁 {key}/ - {len(obj.keys())} 个子项")
            else:
                print(f"  📄 {key}: shape={obj.shape}, dtype={obj.dtype}")

        # trips 数据集
        if 'trips' in f:
            trips = f['trips']
            print(f"\n📁 trips/ (行程数据)")
            print(f"  类型: {type(trips).__name__}")
            print(f"  shape: {trips.shape}")
            print(f"  dtype: {trips.dtype}")
            print(f"  总行程数: {trips.shape[0]}")

            # trips 属性
            if trips.attrs:
                print(f"\n  📋 trips 属性:")
                for attr in trips.attrs:
                    print(f"    @{attr}: {trips.attrs[attr]}")

        # _types 类型信息
        if '_types' in f:
            print("\n📁 _types/ (Julia 类型定义)")
            types_group = f['_types']
            for key in list(types_group.keys())[:5]:
                t = types_group[key]
                if isinstance(t, h5py.Group):
                    print(f"  📁 {key}/ - {list(t.keys())[:3]}")

        # 根属性
        if f.attrs:
            print(f"\n📋 根属性:")
            for attr in f.attrs:
                print(f"  @{attr}: {f.attrs[attr]}")


def print_trip_structure(file_path: str, trip_indices: list = None):
    """详细展示指定 trip 的字段结构"""
    with h5py.File(file_path, 'r') as f:
        trips = f['trips']
        n_trips = trips.shape[0]

        if trip_indices is None:
            # 默认：首尾和中间各取一个
            trip_indices = [0, n_trips // 4, n_trips // 2, n_trips * 3 // 4, n_trips - 1]

        print(f"\n{'='*70}")
        print(f"🔍 Trip 字段结构 (索引: {trip_indices})")
        print(f"{'='*70}")

        for idx in trip_indices:
            if idx >= n_trips:
                continue

            print(f"\n--- Trip {idx} ---")
            ref = trips[idx]
            trip_obj = f[ref]
            trip_data = trip_obj[()]

            print(f"  字段数: {len(trip_data)}")

            for i in range(min(len(trip_data), len(FIELD_NAMES))):
                try:
                    field_ref = trip_data[i]
                    field_obj = f[field_ref]
                    data = field_obj[()]

                    field_name = FIELD_NAMES[i] if i < len(FIELD_NAMES) else f"field_{i}"

                    if hasattr(data, '__len__') and not isinstance(data, (str, bytes)):
                        print(f"  {i:2d}. {field_name:15s}: len={len(data):5d}, dtype={data.dtype}")
                        if len(data) > 0:
                            sample = data[:min(3, len(data))]
                            print(f"        sample: {sample}")
                    else:
                        print(f"  {i:2d}. {field_name:15s}: {data}")
                except Exception as e:
                    print(f"  {i:2d}. field_{i}: (读取失败: {e})")


def compare_h5_jld2(h5_path: str, jld2_path: str):
    """对比 HDF5 和 JLD2 的数据结构"""
    print(f"\n{'='*70}")
    print(f"🔍 对比 HDF5 和 JLD2 数据结构")
    print(f"{'='*70}")

    # HDF5 结构
    print("\n📄 HDF5 (trip/1):")
    with h5py.File(h5_path, 'r') as f:
        if 'trip/1' in f:
            t = f['trip/1']
            print(f"  字段: {list(t.keys())}")
            for key in t.keys():
                obj = t[key]
                print(f"    {key}: shape={obj.shape}, dtype={obj.dtype}")
        else:
            print("  (trip/1 不存在)")

    # JLD2 结构
    print("\n📄 JLD2 (trips[0]):")
    with h5py.File(jld2_path, 'r') as f:
        if 'trips' in f:
            trips = f['trips']
            if trips.shape[0] > 0:
                ref = trips[0]
                trip_obj = f[ref]
                trip_data = trip_obj[()]
                print(f"  字段数: {len(trip_data)}")
                print(f"  字段名: {FIELD_NAMES}")


def list_all_files(base_dir: str, pattern: str = "*.jld2"):
    """列出目录下的所有匹配文件"""
    path = Path(base_dir)
    if not path.exists():
        return []
    return sorted([f for f in path.iterdir() if f.suffix == '.jld2' and not f.name.startswith('._')])


def print_directory_stats(dir_path: str):
    """打印目录下所有文件的统计信息"""
    print(f"\n{'='*70}")
    print(f"📊 目录统计: {dir_path}")
    print(f"{'='*70}")

    files = list_all_files(dir_path)
    if not files:
        print(f"  目录不存在或没有 JLD2 文件")
        return

    total_trips = 0
    total_size = 0

    for f in files:
        try:
            with h5py.File(str(f), 'r') as h5f:
                n_trips = h5f['trips'].shape[0] if 'trips' in h5f else 0
                size_mb = f.stat().st_size / (1024 * 1024)
                total_trips += n_trips
                total_size += size_mb
                print(f"  {f.name:25s}: {n_trips:>6} trips, {size_mb:>8.1f} MB")
        except Exception as e:
            print(f"  {f.name:25s}: 读取失败 - {e}")

    print(f"\n  {'总计':25s}: {total_trips:>6} trips, {total_size:>8.1f} MB")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='JLD2 数据结构探索工具')
    parser.add_argument('--jld2', '-j', default=DEFAULT_JLD2_DIR,
                        help='JLD2 文件或目录路径')
    parser.add_argument('--h5', '-H', default=DEFAULT_H5_DIR,
                        help='HDF5 文件或目录路径')
    parser.add_argument('--trip', '-t', type=int, nargs='+',
                        help='指定要查看的 trip 索引')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='显示目录统计信息')
    parser.add_argument('--compare', '-c', action='store_true',
                        help='对比 HDF5 和 JLD2')

    args = parser.parse_args()

    # 统计模式
    if args.stats:
        if Path(args.jld2).is_dir():
            print_directory_stats(args.jld2)
        else:
            print_directory_stats(str(Path(args.jld2).parent))
        return

    # 对比模式
    if args.compare:
        h5_files = list_all_files(args.h5, "*.h5")
        jld2_files = list_all_files(args.jld2)

        if h5_files and jld2_files:
            compare_h5_jld2(str(h5_files[0]), str(jld2_files[0]))
        return

    # 探索模式
    if Path(args.jld2).is_file():
        print_jld2_info(args.jld2)
        print_trip_structure(args.jld2, args.trip)
    elif Path(args.jld2).is_dir():
        files = list_all_files(args.jld2)
        if files:
            print_jld2_info(str(files[0]))
            print_trip_structure(str(files[0]), args.trip)
    else:
        print(f"错误: 路径不存在 {args.jld2}")


if __name__ == "__main__":
    main()