-- ============================================================
-- 01_extensions_types.sql
-- 数据库扩展与自定义类型
-- 执行顺序：第一步，所有其他脚本依赖此文件
-- ============================================================

-- PostGIS 空间扩展（所有几何列依赖）
CREATE EXTENSION IF NOT EXISTS postgis;

-- Hstore（OSM 标签存储）
CREATE EXTENSION IF NOT EXISTS hstore;

-- POI 类型枚举
-- 用于 ods_poi.poi_type 和 dw_dim_poi.poi_type
CREATE TYPE poi_category AS ENUM (
    '火车站',
    '机场',
    '长途客运站',
    '商圈',
    '医院',
    '学校',
    '小区',
    '景区',
    '其他',
    '站台'
);
