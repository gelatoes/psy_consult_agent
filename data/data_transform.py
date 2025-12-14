import pandas as pd
import json

# 1. Define variable names and their English counterparts.
var_name_mapping = {
    # Basic Info
    'Q1': 'grade',
    'Q2': 'gender',
    'Q3': 'university_type',
    'Q4': 'major_type',
    
    # Mental Health
    'GHQ': 'ghq',
    
    # Influencing Factors
    'Q10': 'exercise_duration',
    'Q13': 'sleep_quality',
    'QZ': 'social_support',
    'Q46': 'help_seeking_willingness',
    'Q5661': 'perceived_academic_involution',
    'Q6267': 'upward_social_comparison',
    'QR': 'psychological_resilience',
    'Q139': 'stressor_count',

    # Irrelevant Info
    'Q5': 'only_child',
    'Q6': 'academic_performance',
    'Q7': 'parents_residence',
    'Q8': 'mother_education',
    'Q9': 'monthly_allowance',
    'Q11_1': 'bedtime',
    'Q16': 'self_rated_health',
    'Q1823': 'social_media_addiction',
    'Q3641': 'academic_involution_level',
    'Q116124': 'Campbell',
    'Q125138': 'CPSS',
}

# 2. Define the new variable categories based on '变量划分.docx'.
var_categories = {
    'basic_info': ['Q1', 'Q2', 'Q3', 'Q4'],
    'realQuestionnaireResults': ['GHQ', 'Q116124', 'Q125138'],
    'influencing_factors': ['Q10', 'Q13', 'QZ', 'Q46', 'Q5661', 'Q6267', 'QR', 'Q139'],
    'additional_info': [
        'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q11_1', 'Q16', 'Q1823', 
        'Q3641'
    ]
}

def convert_value(var_name: str, value):
    """
    Converts a raw value to a more descriptive string based on the variable name
    and the rules from '变量赋值.xlsx' and '变量划分.docx'.
    
    Args:
        var_name: The variable name (e.g., 'Q1', 'GHQ').
        value: The raw value from the data.
        
    Returns:
        The transformed, human-readable value.
    """
    if pd.isna(value):
        return None
    
    val = float(value) # Convert to float for numerical comparisons

    # --- Categorical Variables ---
    if var_name == 'Q1':  # 年级 (Grade)
        return {1: '大一', 2: '大二', 3: '大三', 4: '大四', 5: '大五', 6: '硕士', 7: '博士'}.get(val, value)
    elif var_name == 'Q2':  # 性别 (Gender)
        return {1: '男', 2: '女'}.get(val, value)
    elif var_name == 'Q3':  # 院校类型 (University Type)
        return {1: '985高校', 2: '211高校', 3: '民办高校', 4: '其他'}.get(val, value)
    elif var_name == 'Q4':  # 专业类型 (Major Type)
        return {1: '理工', 2: '社科文科', 3: '医学', 4: '艺术', 5: '农学'}.get(val, value)
    elif var_name == 'Q5':  # 是否是独生子女 (Only Child)
        return {1: '是', 2: '否'}.get(val, value)
    elif var_name == 'Q6':  # 学习成绩 (Academic Performance)
        mapping = {1: '综合成绩排名前10%', 2: '综合成绩排名前11%-25%', 3: '综合成绩排名26%-50%', 
                     4: '综合成绩排名51%-75%', 5: '综合成绩排名76%-90%', 6: '综合成绩排名后10%', 7: '新生（不适用）'}
        return mapping.get(val, value)
    elif var_name == 'Q7':  # 父母当前居住地 (Parents' Residence)
        return {1: '地市及以上城市', 2: '县城', 3: '乡镇、农村'}.get(val, value)
    elif var_name == 'Q8':  # 母亲的文化程度 (Mother's Education)
        mapping = {1: '不识字', 2: '小学', 3: '初中', 4: '高中/中专', 5: '大专', 6: '本科', 7: '研究生'}
        return mapping.get(val, value)
    elif var_name == 'Q16': # 自评身体健康状况 (Self-rated Health)
        return {1: '很不好', 2: '不太好', 3: '一般', 4: '比较好', 5: '很好'}.get(val, value)
    elif var_name == 'Q46': # 求助意愿 (Help-seeking Willingness)
        return {1: '无', 2: '有'}.get(val, value)

    # --- Numerical Scales with Thresholds ---
    elif var_name == 'GHQ': # 一般健康 (General Health)
        return f"{int(val)}"
    elif var_name == 'QZ': # 社会支持 (Social Support)
        return f"{int(val)}"
    elif var_name == 'Q5661': # 学业内卷氛围感知 (Perceived Academic Involution)
        return f"{int(val)}"
    elif var_name == 'Q6267': # 上行社会比较 (Upward Social Comparison)
        return f"{int(val)}"
    elif var_name == 'QR': # 心理韧性 (Psychological Resilience)
        return f"{int(val)}"
    elif var_name == 'Q139': # 压力源 (Stressor Count)
        return f"{int(val)}"

    # --- Simple Numerical Values with Units ---
    elif var_name == 'Q9': # 生活费 (Monthly Allowance)
        return f"{int(val)}元"
    elif var_name == 'Q10': # 锻炼时长 (Exercise Duration)
        return f"{val}小时"
    elif var_name == 'Q13': # 睡眠质量 (Sleep Quality)
        return f"{int(val)}/10"
        
    # --- Default: Return original value (or formatted int if possible) ---
    try:
        return int(val)
    except (ValueError, TypeError):
        return value

# 3. Read the new data file.
try:
    data_df = pd.read_excel('data/原始数据.xls')
except FileNotFoundError:
    print("Error: 'data/原始数据.xls' not found. Please ensure the file is in the correct directory.")
    raise FileNotFoundError

# 4. Process the data and create the JSON structure.
cnt = 0
json_data = []
for index, row in data_df.iterrows():
    student_record = {'basic_info': {'id': f"stu{index:03d}"},
                      'realQuestionnaireResults': {},
                      'psychologicalPortrait': {},
                      'additional_info': {}
                      }
    
    
    cnt += 1
    for category, var_list in var_categories.items():
        if category == 'basic_info' or category == 'realQuestionnaireResults' or category == 'additional_info':
            for var_code in var_list:
                if var_code in data_df.columns:
                    english_name = var_name_mapping.get(var_code, var_code)
                    raw_value = row[var_code]
                    transformed_value = convert_value(var_code, raw_value)
                    student_record[category][english_name] = transformed_value
        else:
            student_record['psychologicalPortrait'][category] = {}
            for var_code in var_list:
                if var_code in data_df.columns:
                    english_name = var_name_mapping.get(var_code, var_code)
                    raw_value = row[var_code]
                    transformed_value = convert_value(var_code, raw_value)
                    student_record['psychologicalPortrait'][category][english_name] = transformed_value
    
    json_data.append(student_record)
print(cnt)
# 5. Save the transformed data to a new JSON file.
output_filename = 'src/students_config_0718.json'
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print(f"Successfully transformed {len(json_data)} student records.")
print(f"Data saved to '{output_filename}'")