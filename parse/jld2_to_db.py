#!/usr/bin/env python3
"""
JLD2 数据导入工具

将 JLD2 文件中的轨迹数据导入到 PostgreSQL 数据库。

使用 SQLModel 和 Pydantic 进行数据库操作和数据验证。
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import defaultdict

import h5py
import numpy as np
from tqdm import tqdm
from loguru import logger
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as SQLField, Session, create_engine, select
from sqlalchemy.dialects.postgresql import insert, ARRAY
from sqlalchemy import Integer, String, Text

# 配置 loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

# 批量插入大小（优化后增大）
BATCH_SIZE = 5000

# 数据库配置
DB_HOST = 'server_address'  # 替换为实际数据库地址
DB_PORT = '5432'
DB_USER = 'postgres'
DB_PASSWORD = 'password'  # 替换为实际密码
DB_NAME = 'harbin'


# ===================== 并行处理函数 =====================

def process_file_for_multiprocessing(file_path: str, batch_size: int = BATCH_SIZE) -> int:
    """
    用于多线程处理单个文件的函数（必须在模块级别定义以支持 pickle）
    """
    # 使用 get_engine 获取连接（线程安全）
    local_engine = get_engine()
    local_session = Session(local_engine)
    try:
        return process_jld2_file(file_path, local_session, batch_size)
    finally:
        local_session.close()
        # 不 dispose 引擎，因为引擎会被复用


# ===================== SQLModel 数据库模型 =====================

class TripBase(SQLModel):
    """行程基础模型"""
    devid: str = Field(max_length=50)
    trip_date: datetime
    trip_seq: int | None = None
    start_lon: float
    start_lat: float
    end_lon: float
    end_lat: float
    start_time: float
    end_time: float


class Trip(TripBase, table=True):
    """行程主表"""
    __tablename__ = 'ods_trips'

    trip_id: int | None = SQLField(default=None, primary_key=True)
    n_points: int = Field(default=0)
    n_roads: int = Field(default=0)


class TripGPSBase(SQLModel):
    """GPS 点基础模型"""
    trip_id: int
    point_seq: int
    lon: float
    lat: float
    tms: float


class TripGPS(TripGPSBase, table=True):
    """GPS 轨迹点表"""
    __tablename__ = 'ods_trip_gps'

    id: int | None = SQLField(default=None, primary_key=True)


class TripRoadsBase(SQLModel):
    """道路匹配基础模型"""
    trip_id: int
    match_seq: int
    road_id: int
    match_time: float
    frac: float | None = None


class TripRoads(TripRoadsBase, table=True):
    """道路匹配表"""
    __tablename__ = 'ods_trip_roads'

    id: int | None = SQLField(default=None, primary_key=True)


class TripRoutesBase(SQLModel):
    """路径信息基础模型"""
    trip_id: int
    route: List[int] = SQLField(default=[], sa_type=ARRAY(Integer))
    route_heading: List[str] | None = SQLField(default=None, sa_type=ARRAY(String))
    route_geom: List[str] | None = SQLField(default=None, sa_type=ARRAY(Text))


class TripRoutes(TripRoutesBase, table=True):
    """路径信息表"""
    __tablename__ = 'ods_trip_routes'

    trip_id: int = SQLField(primary_key=True)


# ===================== Pydantic 请求/响应模型 =====================

class TripInsert(SQLModel):
    """行程插入模型"""
    devid: str
    trip_date: datetime
    trip_seq: int | None
    start_lon: float
    start_lat: float
    end_lon: float
    end_lat: float
    start_time: float
    end_time: float


class GPSPointInsert(SQLModel):
    """GPS 点插入模型"""
    trip_id: int
    point_seq: int
    lon: float
    lat: float
    tms: float


class RoadMatchInsert(SQLModel):
    """道路匹配插入模型"""
    trip_id: int
    match_seq: int
    road_id: int
    match_time: float
    frac: float | None


class RouteInsert(SQLModel):
    """路径信息插入模型"""
    trip_id: int
    route: List[int]
    route_heading: List[str] | None
    route_geom: List[str] | None


# ===================== 数据库操作 =====================

def get_db_url() -> str:
    """获取数据库连接 URL"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    """创建数据库引擎（优化连接池配置）"""
    return create_engine(
        get_db_url(),
        pool_size=12,      # 基础连接池大小
        max_overflow=15,   # 峰值时额外连接数
        pool_pre_ping=True  # 检测连接有效性
    )


def insert_trips_batch(session: Session, trips: List[TripInsert]) -> List[int]:
    """批量插入行程记录"""
    if not trips:
        return []

    trip_ids = []
    for trip_data in trips:
        trip = Trip(
            devid=trip_data.devid,
            trip_date=trip_data.trip_date,
            trip_seq=trip_data.trip_seq,
            start_lon=trip_data.start_lon,
            start_lat=trip_data.start_lat,
            end_lon=trip_data.end_lon,
            end_lat=trip_data.end_lat,
            start_time=trip_data.start_time,
            end_time=trip_data.end_time,
        )
        session.add(trip)
        session.flush()  # 获取 trip_id
        trip_ids.append(trip.trip_id)

    return trip_ids


def insert_gps_batch(session: Session, gps_points: List[GPSPointInsert]):
    """批量插入 GPS 点"""
    for gps in gps_points:
        point = TripGPS(
            trip_id=gps.trip_id,
            point_seq=gps.point_seq,
            lon=gps.lon,
            lat=gps.lat,
            tms=gps.tms,
        )
        session.add(point)


def insert_roads_batch(session: Session, roads: List[RoadMatchInsert]):
    """批量插入道路匹配"""
    for road in roads:
        road_record = TripRoads(
            trip_id=road.trip_id,
            match_seq=road.match_seq,
            road_id=road.road_id,
            match_time=road.match_time,
            frac=road.frac,
        )
        session.add(road_record)


def insert_routes_batch(session: Session, routes: List[RouteInsert]):
    """批量插入路径信息"""
    for route in routes:
        route_record = TripRoutes(
            trip_id=route.trip_id,
            route=route.route,
            route_heading=route.route_heading,
            route_geom=route.route_geom,
        )
        session.add(route_record)


# ===================== JLD2 解析 =====================

def get_trip_date_from_timestamp(tms: np.ndarray) -> datetime:
    """从 Unix 时间戳获取上海本地日期，避免受运行环境时区影响。"""
    if tms is None or len(tms) == 0:
        return datetime.now()

    # 第一个时间戳
    first_ts = float(tms[0])
    return datetime.utcfromtimestamp(first_ts) + timedelta(hours=8)


def is_map_matching_success(trip) -> bool:
    """
    检测地图匹配是否成功

    判断条件:
    - route 不为空（有完整路径）
    - route_geom 不为空（有几何信息）
    """
    route = trip.route
    route_geom = trip.route_geom

    # route 必须存在且非空
    if route is None or len(route) == 0:
        return False

    # route_geom 必须存在且非空
    if route_geom is None or len(route_geom) == 0:
        return False

    return True


def process_trip_data(trip, devid: str, trip_seq: int) -> Optional[Dict[str, Any]]:
    """处理单条行程数据，准备插入数据库"""
    try:
        # 检查地图匹配是否成功
        if not is_map_matching_success(trip):
            return None

        lon = trip.lon
        lat = trip.lat
        tms = trip.tms
        roads = trip.roads
        time = trip.time
        frac = trip.frac
        route = trip.route
        route_heading = trip.route_heading
        route_geom = trip.route_geom

        if lon is None or len(lon) == 0:
            return None

        # 从时间戳获取日期
        trip_date = get_trip_date_from_timestamp(tms)

        # 行程基本信息
        trip_record = TripInsert(
            devid=devid,
            trip_date=trip_date,
            trip_seq=trip_seq,
            start_lon=float(lon[0]),
            start_lat=float(lat[0]),
            end_lon=float(lon[-1]),
            end_lat=float(lat[-1]),
            start_time=float(tms[0]),
            end_time=float(tms[-1]),
        )

        # GPS 点数据
        gps_records = []
        for i in range(len(lon)):
            gps_records.append(GPSPointInsert(
                trip_id=0,  # 临时占位，后面会替换
                point_seq=i,
                lon=float(lon[i]),
                lat=float(lat[i]),
                tms=float(tms[i]),
            ))

        # 道路匹配数据
        road_records = []
        if roads is not None and len(roads) > 0:
            for i in range(len(roads)):
                match_time = float(time[i]) if time is not None and i < len(time) else float(tms[i])
                road_frac = float(frac[i]) if frac is not None and i < len(frac) else None
                road_records.append(RoadMatchInsert(
                    trip_id=0,
                    match_seq=i,
                    road_id=int(roads[i]),
                    match_time=match_time,
                    frac=road_frac,
                ))

        # 路径数据
        route_record = None
        if route is not None and len(route) > 0:
            route_list = route.tolist() if hasattr(route, 'tolist') else list(route)
            heading_list = None
            if route_heading is not None:
                heading_list = [str(h) for h in (route_heading.tolist() if hasattr(route_heading, 'tolist') else route_heading)]
            geom_list = None
            if route_geom is not None:
                geom_list = [str(g) for g in (route_geom.tolist() if hasattr(route_geom, 'tolist') else route_geom)]

            route_record = RouteInsert(
                trip_id=0,
                route=route_list,
                route_heading=heading_list,
                route_geom=geom_list,
            )

        return {
            'trip': trip_record,
            'gps': gps_records,
            'roads': road_records,
            'route': route_record,
        }

    except Exception as e:
        print(f"    处理行程失败: {e}")
        return None


def process_jld2_file(file_path: str, session: Session, batch_size: int = BATCH_SIZE) -> int:
    """处理单个 JLD2 文件，边读边插入数据库"""
    from jld2_parser import read_trip

    filename = os.path.basename(file_path)
    logger.info(f"开始处理文件: {filename}")

    # 按 devid 分组统计行程序号
    devid_trip_count = defaultdict(int)
    trips_processed = 0
    trips_filtered = 0
    inserted = 0

    # 批量缓冲区
    batch: List[Dict[str, Any]] = []

    with h5py.File(file_path, 'r') as f:
        trips_dataset = f['trips']
        total = trips_dataset.shape[0]
        logger.info(f"总行程数: {total:,}")

        # 边读边插入，使用 tqdm 显示进度
        for i in tqdm(range(total), desc=f"处理 {filename}", unit="trip"):
            trip = read_trip(f, trips_dataset[i])
            if trip is None:
                trips_filtered += 1
                continue

            # 计算当日行程序号
            devid = trip.devid
            if devid is None:
                trips_filtered += 1
                continue
            devid_str = str(devid) if not isinstance(devid, str) else devid
            devid_trip_count[devid_str] += 1
            trip_seq = devid_trip_count[devid_str]

            trip_info = process_trip_data(trip, devid_str, trip_seq)
            if trip_info:
                batch.append(trip_info)
                trips_processed += 1

                # 批量插入
                if len(batch) >= batch_size:
                    try:
                        inserted += _insert_batch(session, batch)
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        logger.warning(f"批量插入失败: {e}, 尝试单条插入")
                        inserted += _insert_batch_fallback(session, batch)
                    batch = []
            else:
                trips_filtered += 1

    # 处理剩余的 batch
    if batch:
        try:
            inserted += _insert_batch(session, batch)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.warning(f"最后批量插入失败: {e}, 尝试单条插入")
            inserted += _insert_batch_fallback(session, batch)

    logger.info(f"完成，有效: {trips_processed:,}, 过滤: {trips_filtered:,}, 插入: {inserted:,}")
    return inserted


def _insert_batch(session: Session, batch: List[Dict[str, Any]]) -> int:
    """批量插入一组行程数据"""
    if not batch:
        return 0

    # 插入行程
    trip_records = [t['trip'] for t in batch]
    trip_ids = insert_trips_batch(session, trip_records)

    # 插入 GPS 点
    gps_records = []
    for trip_id, t in zip(trip_ids, batch):
        for gps in t['gps']:
            gps.trip_id = trip_id
        gps_records.extend(t['gps'])
    if gps_records:
        insert_gps_batch(session, gps_records)

    # 插入道路匹配
    road_records = []
    for trip_id, t in zip(trip_ids, batch):
        for road in t['roads']:
            road.trip_id = trip_id
        road_records.extend(t['roads'])
    if road_records:
        insert_roads_batch(session, road_records)

    # 插入路径信息
    route_records = []
    for trip_id, t in zip(trip_ids, batch):
        if t['route']:
            t['route'].trip_id = trip_id
            route_records.append(t['route'])
    if route_records:
        insert_routes_batch(session, route_records)

    return len(batch)


def _insert_batch_fallback(session: Session, batch: List[Dict[str, Any]]) -> int:
    """逐条插入（批量失败时的降级方案）"""
    inserted = 0
    for trip_info in batch:
        try:
            trip_id = insert_trips_batch(session, [trip_info['trip']])[0]

            # GPS
            for gps in trip_info['gps']:
                gps.trip_id = trip_id
            insert_gps_batch(session, trip_info['gps'])

            # Roads
            for road in trip_info['roads']:
                road.trip_id = trip_id
            insert_roads_batch(session, trip_info['roads'])

            # Routes
            if trip_info['route']:
                trip_info['route'].trip_id = trip_id
                insert_routes_batch(session, [trip_info['route']])

            session.commit()
            inserted += 1
        except Exception as e2:
            session.rollback()
            logger.error(f"单条插入失败: {e2}")

    return inserted


def import_jld2_files(file_paths: List[str], batch_size: int = BATCH_SIZE, workers: int = 4):
    """导入多个 JLD2 文件（并行处理）"""
    engine = get_engine()

    # 测试连接
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT version()")
            logger.success(f"数据库连接成功: {result.fetchone()[0][:50]}...")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return

    # 过滤存在的文件
    valid_files = [f for f in file_paths if os.path.exists(f)]
    invalid_files = [f for f in file_paths if not os.path.exists(f)]
    for f in invalid_files:
        logger.warning(f"文件不存在: {f}")

    if not valid_files:
        logger.error("没有有效的文件可以处理")
        return

    logger.info(f"将并行处理 {len(valid_files)} 个文件 (workers={min(workers, len(valid_files))})")

    # 并行处理文件（使用线程池）
    from concurrent.futures import ThreadPoolExecutor, as_completed

    total_inserted = 0
    max_workers = min(workers, len(valid_files))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_file = {
            executor.submit(process_file_for_multiprocessing, f, batch_size): f
            for f in valid_files
        }

        # 收集结果
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                count = future.result()
                total_inserted += count
            except Exception as e:
                logger.error(f"处理文件失败: {file_path}, {e}")

    logger.success(f"\n{'='*50}")
    logger.success(f"导入完成，总共插入 {total_inserted:,} 条行程")
    logger.success(f"{'='*50}")


def list_jld2_files(data_dir: str = 'datasets/processed_traj') -> List[str]:
    """列出所有 JLD2 文件"""
    files = []
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith('.jld2'):
                files.append(os.path.join(data_dir, f))
    return sorted(files)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='JLD2 数据导入工具')
    parser.add_argument('--input', '-i', nargs='+',
                        help='JLD2 文件路径')
    parser.add_argument('--dir', '-d', default='datasets/processed_traj',
                        help='JLD2 文件目录')
    parser.add_argument('--batch-size', '-b', type=int, default=BATCH_SIZE,
                        help=f'批量插入大小 (默认 {BATCH_SIZE})')
    parser.add_argument('--workers', '-w', type=int, default=4,
                        help='并行处理的文件数 (默认 4)')

    args = parser.parse_args()

    file_paths = []
    if args.input:
        file_paths = args.input
    else:
        file_paths = list_jld2_files(args.dir)

    if not file_paths:
        logger.warning("没有找到 JLD2 文件")
        return

    logger.info(f"将处理以下文件:")
    for f in file_paths:
        logger.info(f"  - {f}")

    import_jld2_files(file_paths, args.batch_size, args.workers)


if __name__ == "__main__":
    main()
