"""
模型能力管理API路由
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

from app.services.model_capability_service import get_model_capability_service
from app.services.config_service import config_service
from app.constants.model_capabilities import (
    DEFAULT_MODEL_CAPABILITIES,
    ANALYSIS_DEPTH_REQUIREMENTS,
    CAPABILITY_DESCRIPTIONS,
    ModelRole,
    ModelFeature,
    get_model_capability_badge,
    get_role_badge,
    get_feature_badge
)
from app.core.unified_config import unified_config
from app.core.response import ok, fail
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/model-capabilities", tags=["模型能力管理"])


# ==================== 请求/响应模型 ====================

class ModelCapabilityInfo(BaseModel):
    """模型能力信息"""
    model_name: str
    capability_level: int
    suitable_roles: List[str]
    features: List[str]
    recommended_depths: List[str]
    performance_metrics: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class ModelRecommendationRequest(BaseModel):
    """模型推荐请求"""
    research_depth: str = Field(..., description="研究深度：快速/基础/标准/深度/全面")


class ModelRecommendationResponse(BaseModel):
    """模型推荐响应"""
    quick_model: str
    deep_model: str
    quick_model_info: ModelCapabilityInfo
    deep_model_info: ModelCapabilityInfo
    reason: str


class ModelValidationRequest(BaseModel):
    """模型验证请求"""
    quick_model: str
    deep_model: str
    research_depth: str


class ModelValidationResponse(BaseModel):
    """模型验证响应"""
    valid: bool
    warnings: List[str]
    recommendations: List[str]


class BatchInitRequest(BaseModel):
    """批量初始化请求"""
    overwrite: bool = Field(default=False, description="是否覆盖已有配置")


# ==================== 能力参数辅助方法 ====================

# LLMConfig 中能力参数的默认值：只要这些值都还是默认值，就认为该模型尚未初始化能力参数
DEFAULT_CAPABILITY_FIELDS: Dict[str, Any] = {
    "capability_level": 2,
    "suitable_roles": ["both"],
    "features": [],
    "recommended_depths": ["快速", "基础", "标准"],
    "performance_metrics": None
}


def _plain_values(values: Optional[List[Any]]) -> List[Any]:
    """把枚举成员转换成原始值列表

    Python 3.11+ 中 str(ModelRole.QUICK_ANALYSIS) 得到的是 'ModelRole.QUICK_ANALYSIS'，
    无法再被 ModelRole() 解析回来，这里统一使用 .value 转换。
    """
    return [value.value if isinstance(value, Enum) else value for value in (values or [])]


def _has_capability_config(llm_config) -> bool:
    """判断模型是否已经配置过能力参数"""
    return (
        llm_config.capability_level != DEFAULT_CAPABILITY_FIELDS["capability_level"]
        or _plain_values(llm_config.suitable_roles) != DEFAULT_CAPABILITY_FIELDS["suitable_roles"]
        or _plain_values(llm_config.features) != DEFAULT_CAPABILITY_FIELDS["features"]
        or _plain_values(llm_config.recommended_depths) != DEFAULT_CAPABILITY_FIELDS["recommended_depths"]
        or llm_config.performance_metrics is not None
    )


def _capability_matches(llm_config, target: Dict[str, Any]) -> bool:
    """判断模型当前的能力参数是否已经与目标值一致"""
    return (
        llm_config.capability_level == target["capability_level"]
        and _plain_values(llm_config.suitable_roles) == target["suitable_roles"]
        and _plain_values(llm_config.features) == target["features"]
        and _plain_values(llm_config.recommended_depths) == target["recommended_depths"]
        and llm_config.performance_metrics == target["performance_metrics"]
    )


# ==================== API路由 ====================

@router.get("/default-configs")
async def get_default_model_configs():
    """
    获取所有默认模型能力配置

    返回预定义的常见模型能力配置，用于参考和初始化。
    """
    try:
        # 转换为可序列化的格式
        configs = {}
        for model_name, config in DEFAULT_MODEL_CAPABILITIES.items():
            configs[model_name] = {
                "model_name": model_name,
                "capability_level": config["capability_level"],
                "suitable_roles": _plain_values(config["suitable_roles"]),
                "features": _plain_values(config["features"]),
                "recommended_depths": config["recommended_depths"],
                "performance_metrics": config.get("performance_metrics"),
                "description": config.get("description")
            }

        return {
            "success": True,
            "data": configs,
            "message": "获取默认模型配置成功"
        }
    except Exception as e:
        logger.error(f"获取默认模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/depth-requirements", response_model=dict)
async def get_depth_requirements():
    """
    获取分析深度要求

    返回各个分析深度对模型的最低要求。
    """
    try:
        # 转换为可序列化的格式
        requirements = {}
        for depth, req in ANALYSIS_DEPTH_REQUIREMENTS.items():
            requirements[depth] = {
                "min_capability": req["min_capability"],
                "quick_model_min": req["quick_model_min"],
                "deep_model_min": req["deep_model_min"],
                "required_features": _plain_values(req["required_features"]),
                "description": req["description"]
            }

        return ok(requirements, "获取分析深度要求成功")
    except Exception as e:
        logger.error(f"获取分析深度要求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capability-descriptions", response_model=dict)
async def get_capability_descriptions():
    """获取能力等级描述"""
    try:
        return ok(CAPABILITY_DESCRIPTIONS, "获取能力等级描述成功")
    except Exception as e:
        logger.error(f"获取能力等级描述失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/badges", response_model=dict)
async def get_all_badges():
    """
    获取所有徽章样式

    返回能力等级、角色、特性的徽章样式配置。
    """
    try:
        badges = {
            "capability_levels": {
                str(level): get_model_capability_badge(level)
                for level in range(1, 6)
            },
            "roles": {
                role.value: get_role_badge(role)
                for role in ModelRole
            },
            "features": {
                feature.value: get_feature_badge(feature)
                for feature in ModelFeature
            }
        }

        return ok(badges, "获取徽章样式成功")
    except Exception as e:
        logger.error(f"获取徽章样式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend", response_model=dict)
async def recommend_models(request: ModelRecommendationRequest):
    """
    推荐模型

    根据分析深度推荐最合适的模型对。
    """
    try:
        capability_service = get_model_capability_service()

        # 获取推荐模型
        quick_model, deep_model = capability_service.recommend_models_for_depth(
            request.research_depth
        )

        logger.info(f"🔍 推荐模型: quick={quick_model}, deep={deep_model}")

        # 获取模型详细信息
        quick_info = capability_service.get_model_config(quick_model)
        deep_info = capability_service.get_model_config(deep_model)

        logger.info(f"🔍 模型详细信息: quick_info={quick_info}, deep_info={deep_info}")

        # 生成推荐理由
        depth_req = ANALYSIS_DEPTH_REQUIREMENTS.get(
            request.research_depth,
            ANALYSIS_DEPTH_REQUIREMENTS["标准"]
        )

        # 获取能力等级描述
        capability_desc = {
            1: "基础级",
            2: "标准级",
            3: "高级",
            4: "专业级",
            5: "旗舰级"
        }

        quick_level_desc = capability_desc.get(quick_info['capability_level'], "标准级")
        deep_level_desc = capability_desc.get(deep_info['capability_level'], "标准级")

        reason = (
            f"• 快速模型：{quick_level_desc}，注重速度和成本，适合数据收集\n"
            f"• 深度模型：{deep_level_desc}，注重质量和推理，适合分析决策"
        )

        response_data = {
            "quick_model": quick_model,
            "deep_model": deep_model,
            "quick_model_info": quick_info,
            "deep_model_info": deep_info,
            "reason": reason
        }

        logger.info(f"🔍 返回的响应数据: {response_data}")

        return ok(response_data, "模型推荐成功")
    except Exception as e:
        logger.error(f"模型推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=dict)
async def validate_models(request: ModelValidationRequest):
    """
    验证模型对

    验证选择的模型对是否适合指定的分析深度。
    """
    try:
        capability_service = get_model_capability_service()

        # 验证模型对
        validation = capability_service.validate_model_pair(
            request.quick_model,
            request.deep_model,
            request.research_depth
        )

        return ok(validation, "模型验证完成")
    except Exception as e:
        logger.error(f"模型验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-init", response_model=dict)
async def batch_init_capabilities(request: BatchInitRequest):
    """
    批量初始化模型能力

    为数据库中的模型配置自动填充能力参数，并将结果持久化到数据库。
    """
    try:
        # 能力参数保存在系统配置（system_configs.llm_configs）里
        config = await config_service.get_system_config()
        if not config:
            raise HTTPException(status_code=500, detail="未找到系统配置，无法初始化模型能力")

        updated_count = 0
        skipped_count = 0
        updated_configs = []

        for llm_config in config.llm_configs:
            model_name = llm_config.model_name

            default_config = DEFAULT_MODEL_CAPABILITIES.get(model_name)
            if not default_config:
                logger.warning(f"模型 {model_name} 没有默认配置，跳过")
                skipped_count += 1
                continue

            # 已经配置过能力参数且未要求覆盖时跳过
            if not request.overwrite and _has_capability_config(llm_config):
                logger.info(f"模型 {model_name} 已配置能力参数，跳过")
                skipped_count += 1
                continue

            target = {
                "capability_level": int(default_config["capability_level"]),
                "suitable_roles": _plain_values(default_config["suitable_roles"]),
                "features": _plain_values(default_config["features"]),
                "recommended_depths": _plain_values(default_config["recommended_depths"]),
                "performance_metrics": default_config.get("performance_metrics")
            }

            # 已经是目标值，无需写入
            if _capability_matches(llm_config, target):
                logger.info(f"模型 {model_name} 的能力参数已是最新，无需更新")
                skipped_count += 1
                continue

            # 更新配置
            llm_config.capability_level = target["capability_level"]
            llm_config.suitable_roles = target["suitable_roles"]
            llm_config.features = target["features"]
            llm_config.recommended_depths = target["recommended_depths"]
            llm_config.performance_metrics = target["performance_metrics"]

            updated_count += 1
            updated_configs.append(llm_config)
            logger.info(f"已初始化模型 {model_name} 的能力参数")

        if updated_count > 0:
            # 保存到数据库（同时更新配置版本号）
            if not await config_service.save_system_config(config):
                raise HTTPException(status_code=500, detail="模型能力参数保存失败")

            # 同步到传统配置文件，保证运行时读取 models.json 时也能拿到能力参数
            for llm_config in updated_configs:
                if not unified_config.sync_llm_capability_to_legacy(llm_config):
                    logger.warning(
                        f"模型 {llm_config.model_name} 的能力参数未同步到配置文件"
                        f"（传统配置中不存在该模型或写入失败）"
                    )

        return ok(
            {
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "total_count": len(config.llm_configs),
                "updated_models": [c.model_name for c in updated_configs]
            },
            f"批量初始化完成：更新{updated_count}个，跳过{skipped_count}个"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量初始化失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/{model_name}", response_model=dict)
async def get_model_capability(model_name: str):
    """
    获取指定模型的能力信息

    Args:
        model_name: 模型名称
    """
    try:
        capability_service = get_model_capability_service()
        config = capability_service.get_model_config(model_name)

        return ok(config, f"获取模型 {model_name} 能力信息成功")
    except Exception as e:
        logger.error(f"获取模型能力信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

