"""
JSON数组分割脚本
功能：读取包含数组的JSON文件，将数组元素平均分成三等份，分别保存到三个新的JSON文件中
作者：Claude
创建时间：2025年7月19日

使用说明：
1. 确保输入的JSON文件存在且格式正确
2. 脚本会自动处理数组长度不能被3整除的情况，确保所有元素都被分配
3. 输出的三个文件将包含尽可能平均分配的数组元素
"""

import json
import os
import math


def split_json_array():
    # 定义文件路径
    input_file = r"D:\myz-cs\myz-projects\llm_video\psy-consult\src\students_config_0718.json"
    output_files = [
        r"D:\myz-cs\myz-projects\llm_video\psy-consult\src\students_config_0718_1.json",
        r"D:\myz-cs\myz-projects\llm_video\psy-consult\src\students_config_0718_2.json",
        r"D:\myz-cs\myz-projects\llm_video\psy-consult\src\students_config_0718_3.json"
    ]

    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            print(f"错误：输入文件 {input_file} 不存在！")
            return

        # 读取原始JSON文件
        print("正在读取原始JSON文件...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查数据是否为数组
        if not isinstance(data, list):
            print("错误：JSON文件中的数据不是数组格式！")
            return

        # 获取数组长度
        total_length = len(data)
        print(f"原始数组包含 {total_length} 个元素")

        if total_length == 0:
            print("警告：数组为空，无需分割")
            return

        # 计算每个分组的大小
        base_size = total_length // 3
        remainder = total_length % 3

        # 确定每个分组的实际大小（前remainder个分组多分配1个元素）
        group_sizes = [base_size + (1 if i < remainder else 0) for i in range(3)]

        print(f"分组大小：{group_sizes[0]}, {group_sizes[1]}, {group_sizes[2]}")

        # 分割数组
        start_index = 0
        for i, size in enumerate(group_sizes):
            end_index = start_index + size
            group_data = data[start_index:end_index]

            # 保存到对应的文件
            output_file = output_files[i]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(group_data, f, ensure_ascii=False, indent=2)

            print(f"已保存第{i + 1}组（{len(group_data)}个元素）到：{output_file}")
            start_index = end_index

        print("分割完成！")

        # 验证分割结果
        total_saved = sum(group_sizes)
        print(f"验证：原始数组 {total_length} 个元素，已保存 {total_saved} 个元素")

    except json.JSONDecodeError as e:
        print(f"JSON解析错误：{e}")
    except FileNotFoundError as e:
        print(f"文件未找到：{e}")
    except Exception as e:
        print(f"发生未知错误：{e}")


if __name__ == "__main__":
    split_json_array()