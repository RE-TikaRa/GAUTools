# GSAU 教务系统工具

用于登录甘肃农业大学教务系统并抓取：
- 学期课表
- 成绩列表
- 单门课程成绩详情

## 运行环境

- Python 3.10+

## 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

当前依赖：
- requests
- beautifulsoup4
- lxml
- python-dotenv
- pycryptodome
- pytest

## 账号配置

程序支持三种凭据来源，优先级如下：

1. 环境变量
2. 配置文件
3. 交互输入（仅当前两者缺失时）

### 方式一：环境变量

```bash
set GSAU_USERNAME=你的学号
set GSAU_PASSWORD=你的密码
```

### 方式二：配置文件

复制并修改 `config.example.ini` 为 `config.ini`：

```ini
[auth]
username = 你的学号
password = 你的密码
```

## 命令行使用方法

入口文件：`cli.py`

```bash
python cli.py <command> [options]
```

支持命令：
- `terms`：列出可用学期
- `schedule`：获取课表
- `grades`：获取成绩列表
- `grade-detail`：获取单门课程成绩详情
- `proofs`：列出可用证明模板
- `proof-history`：列出已生成证明记录

### 1) 列出可用学期

```bash
python cli.py terms --format table
python cli.py terms --format json
```

### 2) 获取课表

```bash
python cli.py schedule --year 2024-2025 --term 1 --format table
python cli.py schedule --year 2024-2025 --term 1 --format json
python cli.py schedule --year 2024-2025 --term 1 --format csv --output schedule.csv
```

参数说明：
- `--year`：学年，例如 `2024-2025`
- `--term`：学期，例如 `1` 或 `2`
- `--format`：输出格式，`table` / `json` / `csv`
- `--output`：可选，输出到文件

### 3) 获取成绩列表

```bash
python cli.py grades --year 2024-2025 --term 1 --format table
python cli.py grades --year 2024-2025 --term 1 --format json
python cli.py grades --year 2024-2025 --term 1 --format csv --output grades.csv
```

说明：
- `--year` 和 `--term` 可不填，不填时按系统默认查询。

### 4) 获取成绩详情

```bash
python cli.py grade-detail ^
  --jxb-id "/jsxsd/kscj/pscj_list.do?xs0101id=你的学号&jx0404id=教学班ID&zcj=总评" ^
  --course-name "课程名" ^
  --student-id "你的学号" ^
  --student-name "你的姓名" ^
  --year 2024-2025 ^
  --term 1 ^
  --format json
```

`--jxb-id` 推荐传成绩列表中 `raw.detail_url` 的值。

也支持自动匹配模式（不传 `--jxb-id`）：

```bash
python cli.py grade-detail --course-name "线性代数" --year 2024-2025 --term 1 --format json
```

程序会先查询该学期成绩，再按课程名自动匹配详情链接。

### 5) 查询可用证明模板

```bash
python cli.py proofs --format table
python cli.py proofs --format json
```

### 6) 查询已生成证明记录

```bash
python cli.py proof-history --format table
python cli.py proof-history --format json
```

## Python API 使用方法

### 获取课表

```python
from gautools.client import GSAUClient
from gautools.schedule import get_schedule

client = GSAUClient(prompt=False)
courses = get_schedule(client, "2024-2025", "1")
for course in courses:
    print(course)
```

### 获取成绩列表

```python
from gautools.client import GSAUClient
from gautools.grades import get_grades

client = GSAUClient(prompt=False)
grades = get_grades(client, year="2024-2025", term="1")
for grade in grades:
    print(grade.course_name, grade.score)
```

### 获取成绩详情

```python
from gautools.client import GSAUClient
from gautools.grades import get_grades, get_grade_detail

client = GSAUClient(prompt=False)
grades = get_grades(client, year="2024-2025", term="1")

if grades:
    detail_url = grades[0].raw.get("detail_url", "")
    detail = get_grade_detail(
        client,
        jxb_id=detail_url,
        year="2024-2025",
        term="1",
        course_name=grades[0].course_name,
        student_id="你的学号",
        student_name="你的姓名",
    )
    print(detail.breakdown)
```

## 常见问题

### 1) 登录失败

- 检查账号密码是否正确。
- 检查 `config.ini` 是否位于项目根目录。
- 检查环境变量 `GSAU_USERNAME` / `GSAU_PASSWORD` 是否设置正确。

### 2) 命令报参数缺失

- `schedule` 必须提供 `--year` 与 `--term`。
- `grade-detail` 必须提供：
  - `--jxb-id`
  - `--course-name`
  - `--student-id`
  - `--student-name`
  - `--year`
  - `--term`

### 3) 中文显示异常

优先使用 `--format json`，并在支持 UTF-8 的终端查看。

## 测试

```bash
python -m pytest -q
```
