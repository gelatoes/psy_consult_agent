# 基于配置文件动态创建心理咨询师Agent系统设计与实现文档

## 1. 系统概述

该系统是一个基于LangGraph的心理咨询应用，支持两种模式：咨询模式和训练模式。本次改进聚焦于实现心理咨询师Agent的动态创建机制，使系统能根据配置文件自动创建不同流派的心理咨询师，并为每个咨询师适配相应的记忆系统。

## 2. 主要改进内容

### 2.1 配置文件设计 - `therapists_config.json`

创建了心理咨询师配置文件，用于定义不同流派的咨询师信息。配置示例:

```json
{
  "version": "1.0",
  "last_updated": "2025-03-21",
  "therapists": [
    {
      "id": "cbt",
      "name": "认知行为疗法",
      "english_name": "Cognitive Behavioral Therapy",
      "description": "认知行为疗法是一种以实证为基础的心理治疗方法...",
      "expertise": ["抑郁症", "焦虑障碍", "强迫症", "创伤后应激障碍"],
      "core_techniques": ["认知重构", "行为激活", "暴露疗法"],
      "theoretical_basis": "CBT认为我们的想法、感受和行为是相互关联的...",
      "session_structure": {
        "short_term": true,
        "goal_oriented": true,
        "typical_sessions": "12-20次会谈"
      },
      "tone_config": "作为认知行为疗法咨询师，你的语言风格应当清晰、直接且有教育性..."
    }
  ]
}
```

### 2.2 TherapistAgent类改进

扩展了TherapistAgent类，使其能够根据配置文件参数初始化:

- 增加了从配置文件加载信息的功能
- 支持语气配置和专业领域等属性
- 提供默认配置机制，确保即使配置不完整也能正常工作

### 2.3 TherapistFactory类实现

新增TherapistFactory类，专门负责咨询师Agent的创建:

- 负责加载配置文件
- 动态创建单个或所有咨询师实例
- 确保每个咨询师都有对应的记忆集合

### 2.4 记忆系统适配

改进了记忆系统，使其支持动态加载咨询师配置:

- 修改MemoryInitializer类检测并初始化所有咨询师的记忆集合
- 实现记忆系统与配置文件的同步
- 为新增的咨询师流派自动创建初始技能记忆

### 2.5 System类和TrainingController适配

- 修改System类，使用TherapistFactory创建咨询师团队
- 更新TrainingController以支持动态数量的咨询师

## 3. 核心组件详解

### 3.1 TherapistAgent 类

```python
class TherapistAgent:
    def __init__(
            self,
            therapy_type: str,
            config: Optional[Dict[str, Any]] = None,
            llm: Optional[BaseChatModel] = None
    ):
        self.therapy_type = therapy_type
        # 使用提供的配置或从配置文件加载
        if config:
            self.config = config
        else:
            self.config = self._load_config(therapy_type)
        # LLM初始化...
```

主要属性和方法:
- `therapy_type`: 咨询师流派类型
- `name`: 流派名称
- `description`: 流派描述
- `expertise`: 擅长领域
- `core_techniques`: 核心技术
- `tone_config`: 语气配置

### 3.2 TherapistFactory 类

```python
class TherapistFactory:
    def __init__(self, memory_manager: Optional[MemoryManager] = None, 
                 llm: Optional[BaseChatModel] = None):
        self.memory_manager = memory_manager
        self.llm = llm
        self.therapists_config = {}

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        # 从配置文件加载心理咨询师配置...

    def create_therapist(self, therapy_type: str) -> Optional[TherapistAgent]:
        # 创建特定流派的心理咨询师...

    def create_all_therapists(self) -> List[TherapistAgent]:
        # 根据配置创建所有流派的心理咨询师...

    async def ensure_therapist_memories(self) -> None:
        # 确保所有配置的咨询师在记忆系统中有对应的记忆集合...
```

### 3.3 记忆系统改进

1. 修改了`MemoryManager`类和`EnhancedMemoryManager`类，增加动态获取咨询师流派的能力
2. 更新了`MemorySystemInitializer`类，实现配置与记忆系统的同步功能
3. 支持动态创建记忆集合

```python
def _get_therapist_types(self) -> List[str]:
    """从配置文件获取所有的治疗师流派类型"""
    therapy_types = ["cbt", "psychodynamic"]  # 默认流派
    try:
        # 尝试加载治疗师配置文件
        config_path = os.path.join(...)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            # 提取所有流派ID
            therapy_types = [
                therapist.get("id")
                for therapist in config_data.get("therapists", [])
                if therapist.get("id")
            ]
    except Exception as e:
        logger.warning(f"加载治疗师配置失败: {str(e)}，将使用默认流派")
    return therapy_types
```

### 3.4 System类适配

```python
def initialize(self):
    # 加载咨询师配置
    self.therapist_factory.load_config()
    
    # 确保所有咨询师的记忆集合存在
    await self.therapist_factory.ensure_therapist_memories()
    
    # 创建心理咨询师团队（从配置动态创建）
    self.therapist_agents = self.therapist_factory.create_all_therapists()
```

## 4. 使用方法

### 4.1 配置文件设置

1. 在`src`目录下创建或修改`therapists_config.json`文件
2. 按照以下格式添加各种流派的咨询师信息:

```json
{
  "version": "1.0",
  "last_updated": "2025-03-21",
  "therapists": [
    {
      "id": "流派标识符",
      "name": "流派中文名称",
      "english_name": "流派英文名称",
      "description": "流派描述",
      "expertise": ["擅长领域1", "擅长领域2"],
      "core_techniques": ["核心技术1", "核心技术2"],
      "theoretical_basis": "理论基础描述",
      "session_structure": {
        "short_term": true,
        "goal_oriented": true
      },
      "tone_config": "语气配置描述"
    }
  ]
}
```

### 4.2 系统启动流程

1. 系统初始化时会自动读取配置文件
2. 检查并初始化每个流派的记忆集合
3. 动态创建咨询师Agent团队
4. 开始训练或咨询流程

### 4.3 添加新咨询师流派

1. 编辑`therapists_config.json`文件，添加新的咨询师配置
2. 重启系统，系统将自动:
   - 为新咨询师创建记忆集合
   - 初始化基础技能记忆
   - 将新咨询师纳入训练和咨询流程

### 4.4 修改咨询师配置

1. 编辑`therapists_config.json`文件，修改相应咨询师的配置信息
2. 重启系统，更新将自动生效
3. 已存储的技能记忆和病历不会受影响

## 5. 技术亮点

1. **配置驱动设计**: 通过配置文件而非代码管理咨询师信息，方便非技术人员调整
2. **动态组件创建**: 基于工厂模式实现咨询师的动态创建
3. **双重记忆机制**: 支持JSON文件和向量数据库的双重记忆存储
4. **自动初始化**: 自动检测并创建新增咨询师的记忆集合
5. **优雅降级**: 提供默认配置机制，确保即使配置不完整系统也能正常工作

## 6. 注意事项

1. 配置文件必须包含有效的JSON结构
2. 每个咨询师必须有唯一的`id`字段
3. 修改已有咨询师的`id`会导致其记忆集合无法匹配
4. 首次添加新咨询师时，系统会自动为其创建基础技能记忆
5. 需确保配置文件中的路径正确，文件编码为UTF-8

## 7. 未来扩展方向

1. 支持热加载配置，无需重启系统
2. 添加基于咨询效果的自动流派选择机制
3. 实现咨询师技能记忆的交叉学习功能
4. 提供可视化界面配置咨询师信息
5. 引入更多流派的默认配置模板

通过这些改进，系统现在能够更灵活地管理和创建不同流派的心理咨询师Agent，同时确保记忆系统的一致性和完整性，大大提高了系统的可扩展性和易用性。