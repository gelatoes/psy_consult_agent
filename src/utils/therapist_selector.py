# src/utils/therapist_selector.py
from typing import Dict, Any, List, Optional, Tuple
import json

from src.utils.vector_utils import VectorUtils
from src.memory.memory_manager import MemoryManager
from src.utils.logger import logger


class TherapistSelector:
    """智能咨询师选择器"""

    @staticmethod
    async def select_best_therapist(
            memory_manager: MemoryManager,
            basic_info: Dict[str, Any],
            portrait: Dict[str, Any],
            available_therapists: List[str]
    ) -> Tuple[str, float]:
        """
        根据学生特征和历史病历，选择最佳的治疗师流派

        算法流程:
        1. 创建当前学生的特征向量
        2. 查找相似的历史案例(获取相似度最高的10个向量)
        3. 获取这些向量对应的病历，提取治疗类型和改善分数
        4. 计算综合得分: 相似度 × 改善分数
        5. 选择综合得分最高的治疗师流派

        Args:
            memory_manager: 记忆管理器
            basic_info: 学生基本信息
            portrait: 学生心理画像
            available_therapists: 可用的治疗师流派列表

        Returns:
            Tuple[str, float]: (最佳治疗师流派, 综合得分)
        """
        try:
            # 1. 创建当前学生的特征向量
            current_vector = VectorUtils.create_student_feature_vector(basic_info, portrait)
            current_feature_text = current_vector["feature_text"]

            # 2. 查找相似的历史案例(Top 10)
            similar_vectors = await memory_manager.find_similar_vectors(current_feature_text, limit=3)
            # logger.info("-------1---------------")
            # logger.info(similar_vectors)

            if not similar_vectors:
                logger.warning("未找到相似的历史案例，将使用默认治疗师")
                return available_therapists[0], 0.0

            # 3. 获取向量索引数据
            vector_index = await memory_manager.get_vector_index()
            # logger.info("-------2---------------")
            # logger.info(vector_index)

            # 4. 计算每个案例的综合得分
            case_scores = []

            for vector in similar_vectors:
                vector_id = vector.get("id")
                # logger.info("-------3----------")
                # logger.info(vector_id)
                if not vector_id or vector_id not in vector_index:
                    continue

                # 获取关联的病历ID
                record_id = vector_index[vector_id].get("record_id")
                # logger.info("-------4----------")
                # logger.info(record_id)
                if not record_id:
                    continue

                # 获取完整病历
                medical_record = await memory_manager.get_medical_record(record_id)
                # logger.info("-------5----------")
                # logger.info(medical_record)
                if not medical_record:
                    continue

                # 获取治疗师流派和改善分数
                therapy_type = medical_record.get("therapyType")
                # logger.info("------6----------")
                # logger.info(therapy_type)

                # 必须确保治疗师流派在可用列表中
                if therapy_type not in available_therapists:
                    continue

                # 获取治疗效果分数
                improvement_score = medical_record.get("totalImprovementScore", 0)
                # logger.info("-------7----------")
                # logger.info(improvement_score)

                # 如果改善分数不是正数，跳过(量表分数变高说明效果不好)
                # if improvement_score <= 0:
                #     continue

                # 计算相似度
                similarity = TherapistSelector._calculate_similarity(
                    current_feature_text,
                    vector.get("feature_text", "")
                )
                # logger.info("-------8----------")
                # logger.info(similarity)

                # 计算综合得分
                combined_score = similarity * improvement_score
                # logger.info("-------9--------")
                # logger.info(combined_score)

                # 记录该案例信息
                case_scores.append({
                    "therapy_type": therapy_type,
                    "record_id": record_id,
                    "similarity": similarity,
                    "improvement_score": improvement_score,
                    "combined_score": combined_score
                })

            # 5. 按综合得分排序
            if not case_scores:
                logger.warning("没有找到有效的治疗师得分，将使用默认治疗师")
                return available_therapists[0], 0.0

            # 按综合得分从高到低排序
            sorted_cases = sorted(case_scores, key=lambda x: x["combined_score"], reverse=True)

            # 选择综合得分最高的治疗师流派
            best_therapy = sorted_cases[0]["therapy_type"]
            best_score = sorted_cases[0]["combined_score"]

            # 记录选择结果的详细信息
            selection_detail = {
                "best_therapy": best_therapy,
                "best_score": best_score,
                "top_cases": sorted_cases[:3]  # 记录前3个案例的详细信息
            }
            logger.info(f"智能选择结果: {json.dumps(selection_detail, ensure_ascii=False)}")

            return best_therapy, best_score

        except Exception as e:
            logger.error(f"选择最佳治疗师时出错: {str(e)}")
            # 出错时返回默认治疗师
            return available_therapists[0], 0.0

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """
        计算两个特征文本的相似度

        使用词袋模型和余弦相似度计算两个文本的相似度

        Args:
            text1: 第一个特征文本
            text2: 第二个特征文本

        Returns:
            float: 相似度分数 (0-1之间)
        """
        if not text1 or not text2:
            return 0.0

        # 分词
        words1 = text1.split()
        words2 = text2.split()

        # 构建词汇表
        vocabulary = sorted(set(words1).union(set(words2)))

        # 构建词袋向量
        vector1 = [words1.count(word) for word in vocabulary]
        vector2 = [words2.count(word) for word in vocabulary]

        # 计算向量的点积
        dot_product = sum(a * b for a, b in zip(vector1, vector2))

        # 计算向量的范数
        magnitude1 = sum(a * a for a in vector1) ** 0.5
        magnitude2 = sum(b * b for b in vector2) ** 0.5

        # 避免除以零
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # 计算余弦相似度
        similarity = dot_product / (magnitude1 * magnitude2)

        return similarity