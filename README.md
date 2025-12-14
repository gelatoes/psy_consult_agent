# 基于多智能体交互的心理咨询辅助系统 - 项目说明文档

## 项目概述

本项目是一个基于多智能体交互的心理咨询辅助系统，通过构建多层级智能体框架来模拟真实心理咨询流程。系统主要包括侧写师智能体、指导员智能体和多流派心理咨询师智能体，通过协同工作为用户提供个性化心理咨询服务。

系统具有两种运行模式：
- **训练模式**：使用模拟学生智能体进行系统训练和优化
- **咨询模式**：为真实用户提供心理咨询服务

## 项目结构

```
src/
├── agents/                      # 智能体模块
│   ├── profiler_agent.py        # 侧写师智能体
│   ├── student_agent.py         # 学生智能体
│   ├── supervisor_agent.py      # 指导员智能体
│   ├── therapist_agent.py       # 咨询师智能体
│   └── therapist_factory.py     # 咨询师工厂类
├── controllers/                 # 控制器模块
│   ├── base_controller.py       # 控制器基类
│   ├── consultation_controller.py # 咨询模式控制器
│   └── training_controller.py   # 训练模式控制器
├── memory/                      # 记忆管理模块
│   ├── enhanced_memory_manager.py # 增强型记忆管理器
│   ├── memory_manager.py        # 记忆管理器
│   ├── initializer.py          # 记忆初始化器
│   ├── json_store.py           # JSON存储管理器
│   ├── long_term_store.py      # 长期记忆存储
│   └── system_initializer.py   # 系统记忆初始化器
├── schemas/                     # 数据模式定义
│   ├── memory_schemas.py        # 记忆模式定义
│   └── runtime_schemas.py       # 运行时模式定义
├── utils/                       # 工具模块
│   ├── config.py               # 配置管理
│   ├── constants.py            # 常量定义
│   ├── exceptions.py           # 异常定义
│   ├── json_utils.py           # JSON工具
│   ├── llm_service.py          # 大语言模型服务
│   ├── logger.py               # 日志管理
│   ├── prompt_loader.py        # 提示词加载器
│   ├── therapist_selector.py   # 咨询师选择器
│   └── vector_utils.py         # 向量化工具
├── config/                     # 配置文件目录
│   └── prompts/                # 提示词配置
│       ├── profiler_prompts.yaml
│       ├── student_prompts.yaml
│       ├── supervisor_prompts.yaml
│       └── therapist_prompts.yaml
├── json-memories/              # JSON记忆文件存储
├── long-term-memories/         # 向量数据库存储
├── system.py                   # 系统主类
├── main.py                     # 程序入口
├── students_config.json        # 学生配置文件
├── therapists_config.json      # 咨询师配置文件
└── scales.json                 # 心理量表定义
```

## 核心组件详解

### 1. 智能体模块 (agents/)

#### ProfilerAgent (profiler_agent.py)
侧写师智能体，负责与用户对话并生成心理画像。

**主要功能**：
- `speak()`: 与用户对话，基于指导员建议和技能记忆生成回应
- `update_working_memory()`: 更新工作记忆
- `update_psychological_portraits()`: 更新心理画像
- `strengthen_skill()`: 根据指导员反馈强化技能记忆

#### StudentAgent (student_agent.py)
学生智能体，在训练模式中模拟真实学生行为。

**主要功能**：
- `speak()`: 基于心理画像和生活经历回应咨询师
- `fill_scale()`: 填写心理量表（前测和后测）
- `get_info_prompt()`: 获取学生基本信息提示词

#### SupervisorAgent (supervisor_agent.py)
指导员智能体，监督和指导整个咨询流程。

**主要功能**：
- `offer_profile_advice()`: 为侧写师提供指导
- `check_profile_complete()`: 判断侧写是否完成
- `assess_portrait()`: 评估侧写质量
- `offer_consultation_advice()`: 为咨询师提供建议
- `check_consultation_complete()`: 判断咨询是否完成  
- `evaluate_therapist()`: 评估咨询师表现
- `create_student_medical_record()`: 创建电子病历

#### TherapistAgent (therapist_agent.py)
咨询师智能体，提供不同流派的心理咨询服务。

**主要功能**：
- `speak()`: 基于治疗流派进行咨询对话
- `update_working_memory()`: 更新工作记忆
- `strengthen_skill()`: 强化专业技能

#### TherapistFactory (therapist_factory.py)
咨询师工厂类，负责创建和管理不同流派的咨询师。

### 2. 控制器模块 (controllers/)

#### TrainingController (training_controller.py)
训练模式控制器，管理整个训练流程。

**工作流程**：
1. 初始化 → 量表测评 → 侧写对话 → 侧写评估
2. 保存状态快照 → 串行训练各咨询师 → 评估与记录
3. 切换到下一学生或结束训练

#### ConsultationController (consultation_controller.py)
咨询模式控制器，管理真实用户咨询流程。

**工作流程**：
1. 初始化 → 问候 → 量表测评 → 侧写对话
2. 咨询师选择 → 咨询对话 → 后测量表
3. 评估与病历生成

### 3. 记忆管理模块 (memory/)

#### MemoryManager (memory_manager.py)
高层记忆管理器，提供统一的记忆管理接口。

#### EnhancedMemoryManager (enhanced_memory_manager.py)
增强型记忆管理器，同时管理JSON文件和向量数据库。

**记忆类型**：
- **技能记忆**: 存储各智能体的专业技能和经验
- **工作记忆**: 当前咨询过程的临时信息
- **电子病历**: 完整的咨询案例记录
- **学生特征向量**: 用于相似度计算的向量表示

#### 存储层
- `JSONMemoryStore`: JSON文件存储管理
- `LongTermMemoryStore`: ChromaDB向量数据库存储
- `MemoryInitializer`: 记忆系统初始化

### 4. 工具模块 (utils/)

#### LLMService (llm_service.py)
大语言模型服务抽象层，支持OpenAI API。

#### TherapistSelector (therapist_selector.py)
智能咨询师选择算法：
1. 将用户心理画像向量化
2. 在病历库中查找相似案例
3. 根据治疗效果评分选择最佳流派

#### VectorUtils (vector_utils.py)
向量化工具，将心理画像转换为可计算的向量表示。

## 配置文件说明

### students_config.json
包含训练用的学生数据：
```json
{
  "basic_info": {
    "id": "stu000",
    "name": "学生姓名",
    "grade": "年级",
    "gender": "性别"
  },
  "psychologicalPortrait": {
    "events": {},
    "emotions": {},
    "behaviors": {}
  },
  "lifeEventsDetail": []
}
```

### therapists_config.json
定义不同流派的咨询师配置：
```json
{
  "therapists": [
    {
      "id": "cbt",
      "name": "认知行为疗法",
      "expertise": ["抑郁症", "焦虑障碍"],
      "core_techniques": ["认知重构", "行为激活"]
    }
  ]
}
```

### scales.json
心理量表定义，包括PHQ-9、GAD-7、GHQ-20等。

## 运行方式

### 环境配置

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置环境变量：
```bash
export OPENAI_API_KEY="your_api_key"
```

### 切换运行模式

在 `main.py` 中修改模式参数：

#### 训练模式
<!-- ```python
# 创建应用（训练模式）
app = await create_app(mode="training")
``` -->

#### 咨询模式
<!-- ```python
# 创建应用（咨询模式）
app = await create_app(mode="consultation")
``` -->

### 运行程序
<!-- ```bash
set PYTHONPATH=%PYTHONPATH%;. # Windows中设置默认路径
python src/main.py --ablation none # 全量
python src/main.py --ablation wo-profiler # 无侧写师
python src/main.py --ablation wo-memory # 无记忆机制 只去掉了工作记忆和技能记忆
``` -->

### 运行程序（最新）
#### 启动
需要同时启动前后端

#### 后端
``` bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端
``` bash
cd web
python run.py
```

## 系统工作流程

### 训练模式流程

1. **系统初始化**
   - 加载学生配置文件
   - 初始化记忆系统
   - 创建各类智能体

2. **侧写阶段**
   - 侧写师与模拟学生对话
   - 生成和更新心理画像
   - 指导员提供指导意见

3. **侧写评估**
   - 指导员评估画像质量
   - 侧写师更新技能记忆

4. **咨询训练**
   - 各流派咨询师串行训练
   - 完成咨询并填写后测量表
   - 指导员评估咨询效果

5. **记录生成**
   - 创建电子病历
   - 更新咨询师技能记忆
   - 循环处理下一学生

### 咨询模式流程

1. **用户接入**
   - 系统问候用户
   - 用户填写前测量表

2. **心理侧写**
   - 侧写师与用户多轮对话
   - 实时更新心理画像
   - 指导员监督进程

3. **咨询师选择**
   - 基于心理画像和历史病例
   - 使用向量相似度算法
   - 选择最适合的治疗流派

4. **心理咨询**
   - 选定咨询师与用户对话
   - 提供专业心理支持
   - 指导员监督质量

5. **效果评估**
   - 用户填写后测量表
   - 生成咨询报告
   - 更新病历库

## 核心技术特点

### 1. 多智能体协同
- 角色明确分工：侧写、指导、咨询
- 状态共享机制：工作记忆同步
- 质量监控体系：指导员全程监督

### 2. 记忆系统
- 双重存储：JSON + 向量数据库
- 多层记忆：技能、工作、病历、向量
- 持续学习：基于反馈优化

### 3. 智能匹配
- 心理画像向量化
- 相似度计算
- 加权效果评分
- 最优流派选择

### 4. 专业流程
- 符合心理咨询标准流程
- 支持多种治疗流派
- 量表前后测对比
- 效果量化评估

## 扩展与定制

### 添加新的治疗流派

1. 在 `therapists_config.json` 中添加新流派配置
2. 在 `config/prompts/` 中添加对应的提示词文件
3. 系统会自动创建对应的技能记忆集合

### 自定义心理量表

1. 在 `scales.json` 中添加量表定义
2. 修改学生智能体的 `fill_scale()` 方法
3. 更新相关提示词模板

### 调整对话轮次

在控制器中修改最大轮次限制：
```python
MAX_PROFILE_TURNS = 3  # 侧写对话轮次
MAX_CONSULTATION_TURNS = 5  # 咨询对话轮次
```

## 数据管理

### 记忆文件结构
```
json-memories/
├── profiler_skills.json          # 侧写师技能记忆
├── therapist_cbt_skills.json     # CBT咨询师技能记忆
├── medical_records.json          # 电子病历
├── student_vectors.json          # 学生特征向量
└── vector_index.json            # 向量索引

long-term-memories/               # ChromaDB向量数据库
```

### 数据备份与恢复
系统支持JSON和向量数据库的双重存储，确保数据安全性和一致性。

## 版本更新说明

### v2.0 重大优化 - CBT专业化与话题聚焦系统

本次更新对咨询环节进行了重点优化，实现了从泛心理咨询向专业化、聚焦化咨询的重大转变：

#### 1. CBT疗法专业化设计

**四阶段标准化流程**：
- **阶段1**：识别自动思维 - 情绪识别、引发事件识别、自动思维识别
- **阶段2**：确定思想陷阱 - 思维陷阱分类、认知偏差分析
- **阶段3**：挑战自动思维 - 证据收集、质疑思维、重新评估
- **阶段4**：回归现实思维 - 替代思维构建、行动计划制定

**智能阶段切换**：
- 督导师Agent实时评估各阶段完成要素
- 满足专业标准或达到最大轮次时自动切换
- 确保CBT疗法的科学性和完整性

#### 2. 话题聚焦与强化学习机制

**核心话题识别**：
- 基于侧写结果自动确定核心咨询话题
- 初始话题分数设定为5分基准值
- 建立动态话题记录表管理系统

**强化学习评分系统**：
- 督导师Agent对每轮对话进行话题相关性评估
- 高度相关(+2分)、中等相关(+1分)、无关(+0分)、其他主题(-1分)的动态打分
- 根据话题得分指导咨询师保持专业聚焦度

**多话题管理**：
- 自动识别新兴话题并开设独立分数追踪
- 优先引导高分话题深入探讨
- 防止咨询过程的主题偏移

#### 3. 人性化对话优化

**多轮子问题拆分**：
- 将复杂的CBT阶段问题分解为3-5个自然子问题
- 每轮只提出单一具体问题，避免用户困惑
- 基于配置文件的静态子问题与LLM动态生成结合

**四段式对话模板**：
- **回顾**：第二人称概括性复述（避免逐字引用）
- **共情**：情感确认与理解表达
- **问题**：单一具体的开放式提问
- **过渡**：自然的引导性结束语

**问题变体生成**：
- 督导师LLM生成多个问题变体供随机选择
- 避免机械化重复提问
- 增强咨询师回应的灵活性和自然度

#### 4. 专业化要素完成度追踪

**实时进度监控**：
- 每个CBT阶段的专业要素完成情况实时追踪
- 督导师Agent提供详细的证据分析和完成度评估
- 确保每个阶段达到临床标准要求

**智能补偿机制**：
- 未完成要素的自动识别和补充引导
- 基于督导师建议的个性化问题生成
- 保证咨询质量的专业性和完整性

#### 5. 状态管理优化

**CBT专用状态字段**：
```json
{
  "current_cbt_stage": "stage_1",
  "cbt_stage_dialogues": {"stage_1": 2, "stage_2": 0, ...},
  "cbt_stage_completions": {"stage_1": ["情绪识别", "引发事件识别"], ...},
  "topic_scores": {"学业焦虑": 7, "人际关系": 3},
  "core_topic": "学业焦虑",
  "cbt_sub_question_index": {"stage_1": 2, "stage_2": 0, ...}
}
```

**记忆系统增强**：
- 督导师工作记忆包含生活经历、核心信念、情绪触发点分析
- 咨询师技能记忆整合CBT专业技术和案例经验
- 实现更精准的个性化咨询服务

#### 6. 技术架构改进

**模块化设计**：
- CBT配置文件(`cbt_config.json`)独立管理阶段配置
- 提示词模板系统(`prompt/cbt.txt`, `prompt/enhance.txt`)专业化
- 控制器逻辑清晰分离静态配置与动态生成

**鲁棒性增强**：
- LLM调用失败的多层回退机制
- 静态配置与动态生成的无缝切换
- 异常情况下的安全默认行为

#### 7. 效果评估

**量化指标改进**：
- CBT各阶段完成度的精确测量
- 话题聚焦度的数值化评估
- 用户满意度的多维度分析

**专业化验证**：
- 符合CBT理论标准的流程设计
- 心理咨询专业伦理的严格遵循
- 临床实践指导原则的有效应用

本次更新显著提升了系统的专业化水平，实现了从通用心理咨询向专业CBT治疗的精准转变，同时保持了良好的用户体验和对话自然度。

## 注意事项

1. **API配置**: 确保正确配置OpenAI API密钥和接口地址
2. **存储空间**: 长期使用会积累大量病历数据，注意存储管理
3. **资源消耗**: 多智能体同时运行会消耗较多API调用量
4. **数据隐私**: 真实咨询数据需要妥善保护

## 故障排除

### 常见问题

1. **记忆初始化失败**
   - 检查文件权限
   - 确认ChromaDB安装正确

2. **智能体响应异常**
   - 检查提示词格式
   - 验证API连接状态

3. **向量计算错误**
   - 确认向量数据完整性
   - 检查相似度算法参数

4. **模式切换失败**
   - 确认配置文件存在
   - 检查系统初始化状态

---

本项目为心理健康服务领域的AI应用提供了完整的技术方案，通过多智能体协同和专业知识驱动，实现了高质量的智能心理咨询服务。