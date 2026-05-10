#!/usr/bin/env python3
"""
Feishu Sheets Manager - 飞书表格管理工具
为 Hermes Agent 提供飞书表格的增删改查操作

依赖: lark-cli (npm install -g @larksuite/cli)
"""

import subprocess
import json
import os
from typing import List, Dict, Any, Optional

class FeishuSheetsManager:
    """飞书表格管理器"""
    
    def __init__(self, as_user: bool = True):
        """
        初始化
        
        Args:
            as_user: 是否以用户身份操作（可访问个人数据），False 则以应用身份
        """
        self.as_flag = "--as user" if as_user else "--as bot"
        self._check_cli()
    
    def _check_cli(self):
        """检查 lark-cli 是否已安装"""
        result = subprocess.run(
            ["lark-cli", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError("lark-cli 未安装，请先运行: npm install -g @larksuite/cli")
    
    def _run(self, cmd: List[str]) -> Dict[str, Any]:
        """执行 lark-cli 命令并返回 JSON 结果"""
        full_cmd = ["lark-cli"] + cmd + ["--format", "json"]
        if self.as_flag:
            full_cmd.extend(self.as_flag.split())
        
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            raise RuntimeError(f"命令执行失败: {' '.join(full_cmd)}\n错误: {error_msg}")
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"raw_output": result.stdout}
    
    # ==================== 创建操作 ====================
    
    def create_spreadsheet(
        self,
        title: str,
        headers: Optional[List[str]] = None,
        data: Optional[List[List[Any]]] = None,
        folder_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新的电子表格
        
        Args:
            title: 表格标题
            headers: 表头行（可选）
            data: 初始数据（二维数组，可选）
            folder_token: 目标文件夹 token（可选）
        
        Returns:
            创建的表格信息，包含 spreadsheet_token
        
        Example:
            manager = FeishuSheetsManager()
            result = manager.create_spreadsheet(
                title="坐骑列表",
                headers=["Spell ID", "名称", "类型", "状态"],
                data=[["80146", "狡狐魔使", "陆地", "已修复"]]
            )
        """
        cmd = ["sheets", "+create", "--title", title]
        
        if headers:
            cmd.extend(["--headers", json.dumps(headers, ensure_ascii=False)])
        
        if data:
            cmd.extend(["--data", json.dumps(data, ensure_ascii=False)])
        
        if folder_token:
            cmd.extend(["--folder-token", folder_token])
        
        return self._run(cmd)
    
    # ==================== 读取操作 ====================
    
    def read_sheet(
        self,
        spreadsheet_token: str,
        range_str: str,
        sheet_id: Optional[str] = None,
        value_render_option: str = "ToString"
    ) -> Dict[str, Any]:
        """
        读取表格单元格值
        
        Args:
            spreadsheet_token: 表格 token（从 URL 或创建结果获取）
            range_str: 读取范围，如 "A1:D10" 或 "sheetId!A1:D10"
            sheet_id: 工作表 ID（如果 range 不包含 sheetId）
            value_render_option: 值渲染选项: ToString|FormattedValue|Formula|UnformattedValue
        
        Returns:
            单元格数据
        
        Example:
            # 读取整个表格
            result = manager.read_sheet("shtcnxxxx", "A1:Z1000")
            
            # 读取特定工作表
            result = manager.read_sheet("shtcnxxxx", "A1:D10", sheet_id="0")
        """
        cmd = [
            "sheets", "+read",
            "--spreadsheet-token", spreadsheet_token,
            "--range", range_str,
            "--value-render-option", value_render_option
        ]
        
        if sheet_id:
            cmd.extend(["--sheet-id", sheet_id])
        
        return self._run(cmd)
    
    def read_by_url(
        self,
        url: str,
        range_str: str,
        value_render_option: str = "ToString"
    ) -> Dict[str, Any]:
        """
        通过 URL 读取表格
        
        Args:
            url: 飞书表格 URL，如 https://feishu.cn/sheets/shtcnxxxx
            range_str: 读取范围
            value_render_option: 值渲染选项
        
        Example:
            result = manager.read_by_url(
                "https://feishu.cn/sheets/shtcnxxxx",
                "A1:D100"
            )
        """
        cmd = [
            "sheets", "+read",
            "--url", url,
            "--range", range_str,
            "--value-render-option", value_render_option
        ]
        
        return self._run(cmd)
    
    def get_spreadsheet_info(self, spreadsheet_token: str) -> Dict[str, Any]:
        """
        获取表格基本信息（工作表列表等）
        
        Args:
            spreadsheet_token: 表格 token
        
        Returns:
            表格信息，包含工作表列表
        """
        cmd = [
            "sheets", "+info",
            "--spreadsheet-token", spreadsheet_token
        ]
        
        return self._run(cmd)
    
    # ==================== 写入操作 ====================
    
    def write_cells(
        self,
        spreadsheet_token: str,
        range_str: str,
        values: List[List[Any]],
        sheet_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        写入单元格（覆盖模式）
        
        Args:
            spreadsheet_token: 表格 token
            range_str: 写入范围，如 "A1:D10"
            values: 二维数组数据
            sheet_id: 工作表 ID
        
        Returns:
            写入结果
        
        Example:
            manager.write_cells(
                "shtcnxxxx",
                "A1:C3",
                [
                    ["Spell ID", "名称", "状态"],
                    ["80146", "狡狐魔使", "已修复"],
                    ["80364", "膨水鳐", "正常"]
                ]
            )
        """
        cmd = [
            "sheets", "+write",
            "--spreadsheet-token", spreadsheet_token,
            "--range", range_str,
            "--values", json.dumps(values, ensure_ascii=False)
        ]
        
        if sheet_id:
            cmd.extend(["--sheet-id", sheet_id])
        
        return self._run(cmd)
    
    def append_rows(
        self,
        spreadsheet_token: str,
        range_str: str,
        values: List[List[Any]],
        sheet_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        追加行到表格
        
        Args:
            spreadsheet_token: 表格 token
            range_str: 追加范围，如 "A1:D10"（从第一行开始追加）
            values: 二维数组数据
            sheet_id: 工作表 ID
        
        Returns:
            追加结果
        
        Example:
            # 在表格末尾追加新坐骑数据
            manager.append_rows(
                "shtcnxxxx",
                "A1:D1",
                [["80450", "新坐骑", "飞行", "待测试"]]
            )
        """
        cmd = [
            "sheets", "+append",
            "--spreadsheet-token", spreadsheet_token,
            "--range", range_str,
            "--values", json.dumps(values, ensure_ascii=False)
        ]
        
        if sheet_id:
            cmd.extend(["--sheet-id", sheet_id])
        
        return self._run(cmd)
    
    # ==================== 删除操作 ====================
    
    def delete_rows(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        start_index: int,
        count: int = 1
    ) -> Dict[str, Any]:
        """
        删除行
        
        Args:
            spreadsheet_token: 表格 token
            sheet_id: 工作表 ID
            start_index: 起始行索引（从 0 开始）
            count: 删除行数
        
        Example:
            # 删除第 5 行（索引 4）
            manager.delete_rows("shtcnxxxx", "0", 4, 1)
        """
        cmd = [
            "sheets", "+delete-dimension",
            "--spreadsheet-token", spreadsheet_token,
            "--sheet-id", sheet_id,
            "--dimension", "ROWS",
            "--start-index", str(start_index),
            "--count", str(count)
        ]
        
        return self._run(cmd)
    
    def delete_columns(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        start_index: int,
        count: int = 1
    ) -> Dict[str, Any]:
        """
        删除列
        
        Args:
            spreadsheet_token: 表格 token
            sheet_id: 工作表 ID
            start_index: 起始列索引（从 0 开始）
            count: 删除列数
        """
        cmd = [
            "sheets", "+delete-dimension",
            "--spreadsheet-token", spreadsheet_token,
            "--sheet-id", sheet_id,
            "--dimension", "COLUMNS",
            "--start-index", str(start_index),
            "--count", str(count)
        ]
        
        return self._run(cmd)
    
    # ==================== 高级操作 ====================
    
    def find_and_replace(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        find: str,
        replacement: str,
        range_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查找替换
        
        Args:
            spreadsheet_token: 表格 token
            sheet_id: 工作表 ID
            find: 查找内容
            replacement: 替换内容
            range_str: 搜索范围（可选）
        
        Example:
            # 将所有 "5160" 替换为 "7644"
            manager.find_and_replace(
                "shtcnxxxx",
                "0",
                "5160",
                "7644"
            )
        """
        cmd = [
            "sheets", "+replace",
            "--spreadsheet-token", spreadsheet_token,
            "--sheet-id", sheet_id,
            "--find", find,
            "--replacement", replacement
        ]
        
        if range_str:
            cmd.extend(["--range", range_str])
        
        return self._run(cmd)
    
    def find_cells(
        self,
        spreadsheet_token: str,
        sheet_id: str,
        query: str,
        range_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查找单元格
        
        Args:
            spreadsheet_token: 表格 token
            sheet_id: 工作表 ID
            query: 搜索关键词
            range_str: 搜索范围（可选）
        
        Returns:
            匹配的单元格位置列表
        """
        cmd = [
            "sheets", "+find",
            "--spreadsheet-token", spreadsheet_token,
            "--sheet-id", sheet_id,
            "--query", query
        ]
        
        if range_str:
            cmd.extend(["--range", range_str])
        
        return self._run(cmd)
    
    def export_spreadsheet(
        self,
        spreadsheet_token: str,
        output_path: str,
        file_format: str = "xlsx"
    ) -> str:
        """
        导出表格到本地文件
        
        Args:
            spreadsheet_token: 表格 token
            output_path: 输出文件路径
            file_format: 导出格式: xlsx|csv|pdf
        
        Returns:
            导出后的文件路径
        
        Example:
            manager.export_spreadsheet(
                "shtcnxxxx",
                "/tmp/mount_list.xlsx",
                "xlsx"
            )
        """
        cmd = [
            "sheets", "+export",
            "--spreadsheet-token", spreadsheet_token,
            "--format", file_format,
            "-o", output_path
        ]
        
        result = self._run(cmd)
        return output_path
    
    def add_sheet(
        self,
        spreadsheet_token: str,
        title: str
    ) -> Dict[str, Any]:
        """
        在工作簿中添加新工作表
        
        Args:
            spreadsheet_token: 表格 token
            title: 工作表标题
        """
        cmd = [
            "sheets", "+create-sheet",
            "--spreadsheet-token", spreadsheet_token,
            "--title", title
        ]
        
        return self._run(cmd)
    
    def delete_sheet(
        self,
        spreadsheet_token: str,
        sheet_id: str
    ) -> Dict[str, Any]:
        """
        删除工作表
        
        Args:
            spreadsheet_token: 表格 token
            sheet_id: 要删除的工作表 ID
        """
        cmd = [
            "sheets", "+delete-sheet",
            "--spreadsheet-token", spreadsheet_token,
            "--sheet-id", sheet_id
        ]
        
        return self._run(cmd)


# ==================== 便捷函数 ====================

def quick_read_sheet(url_or_token: str, range_str: str = "A1:Z1000") -> List[List[Any]]:
    """
    快速读取表格内容
    
    Args:
        url_or_token: 表格 URL 或 token
        range_str: 读取范围
    
    Returns:
        二维数组数据
    
    Example:
        data = quick_read_sheet("https://feishu.cn/sheets/shtcnxxxx", "A1:D100")
        for row in data:
            print(row)
    """
    manager = FeishuSheetsManager()
    
    if url_or_token.startswith("http"):
        result = manager.read_by_url(url_or_token, range_str)
    else:
        result = manager.read_sheet(url_or_token, range_str)
    
    # 提取值数据
    if "data" in result and "valueRange" in result["data"]:
        return result["data"]["valueRange"].get("values", [])
    
    return []


def quick_write_sheet(
    spreadsheet_token: str,
    range_str: str,
    values: List[List[Any]]
) -> bool:
    """
    快速写入表格内容
    
    Args:
        spreadsheet_token: 表格 token
        range_str: 写入范围
        values: 二维数组数据
    
    Returns:
        是否成功
    """
    try:
        manager = FeishuSheetsManager()
        manager.write_cells(spreadsheet_token, range_str, values)
        return True
    except Exception as e:
        print(f"写入失败: {e}")
        return False


def sync_mount_data_to_sheet(
    spreadsheet_token: str,
    mount_data: List[Dict[str, Any]],
    sheet_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    同步坐骑数据到飞书表格
    
    Args:
        spreadsheet_token: 表格 token
        mount_data: 坐骑数据列表，每个元素是字典
        sheet_id: 工作表 ID（可选）
    
    Example:
        mount_data = [
            {"Spell ID": 80146, "名称": "狡狐魔使", "类型": "陆地", "状态": "已修复"},
            {"Spell ID": 80364, "名称": "膨水鳐", "类型": "陆地", "状态": "正常"}
        ]
        sync_mount_data_to_sheet("shtcnxxxx", mount_data)
    """
    if not mount_data:
        return {"error": "数据为空"}
    
    # 构建表头
    headers = list(mount_data[0].keys())
    
    # 构建数据行
    rows = []
    for item in mount_data:
        row = [str(item.get(key, "")) for key in headers]
        rows.append(row)
    
    # 合并表头和数据
    all_data = [headers] + rows
    
    # 计算范围
    end_col = chr(ord('A') + len(headers) - 1)
    end_row = len(all_data)
    range_str = f"A1:{end_col}{end_row}"
    
    manager = FeishuSheetsManager()
    return manager.write_cells(spreadsheet_token, range_str, all_data, sheet_id)


# ==================== 命令行入口 ====================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python feishu_sheets_manager.py <命令> [参数]")
        print("\n可用命令:")
        print("  read <token> <range>     - 读取表格")
        print("  write <token> <range>    - 写入表格")
        print("  create <title>           - 创建表格")
        print("  info <token>             - 获取表格信息")
        print("\n示例:")
        print('  python feishu_sheets_manager.py read shtcnxxxx "A1:D10"')
        sys.exit(1)
    
    command = sys.argv[1]
    manager = FeishuSheetsManager()
    
    if command == "read" and len(sys.argv) >= 4:
        token = sys.argv[2]
        range_str = sys.argv[3]
        result = manager.read_sheet(token, range_str)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "write" and len(sys.argv) >= 4:
        token = sys.argv[2]
        range_str = sys.argv[3]
        # 从 stdin 读取 JSON 数据
        data = json.load(sys.stdin)
        result = manager.write_cells(token, range_str, data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "create" and len(sys.argv) >= 3:
        title = sys.argv[2]
        result = manager.create_spreadsheet(title)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "info" and len(sys.argv) >= 3:
        token = sys.argv[2]
        result = manager.get_spreadsheet_info(token)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        print(f"未知命令或参数不足: {command}")
        sys.exit(1)
