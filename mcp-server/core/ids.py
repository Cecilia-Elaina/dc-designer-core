"""ID 生成工具"""
import uuid
import time

_counter = 0


def gen_id(prefix: str = "dc") -> str:
    """生成唯一 ID，格式: prefix_timestamp_random"""
    global _counter
    _counter += 1
    ts = int(time.time() * 1000) % 1000000
    return f"{prefix}_{ts}_{_counter:04d}"


def gen_goal_id() -> str:
    return gen_id("goal")


def gen_skill_id() -> str:
    return gen_id("skill")


def gen_objective_id() -> str:
    return gen_id("obj")


def gen_assessment_id() -> str:
    return gen_id("assess")


def gen_source_id() -> str:
    return gen_id("src")


def gen_project_id() -> str:
    return gen_id("proj")
