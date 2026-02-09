import base64
import random
import re

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

USERNAME = ""
PASSWORD = ""

LOGIN_POST_URL = "https://authserver.gsau.edu.cn/authserver/login?service=https%3A%2F%2Fweb.gsau.edu.cn%2Fwengine-auth%2Flogin%3Fcas_login%3Dtrue"
SCHEDULE_URL = "https://jwgl.gsau.edu.cn/jsxsd/xskb/xskb_list.do"

DAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
SECTIONS = ["第一大节", "第二大节", "第三大节", "第四大节", "第五大节"]
AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def random_uagent():
    chrome = f"{random.randint(120, 144)}.0.{random.randint(0, 8000)}.{random.randint(0, 200)}"
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} Safari/537.36"


def random_string(length):
    return "".join(random.choice(AES_CHARS) for _ in range(length))


def encrypt_password(password, salt):
    if not salt:
        return password
    random_prefix = random_string(64)
    random_iv = random_string(16)
    data = random_prefix + password
    key = salt.strip().encode("utf-8")
    iv = random_iv.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def parse_cell(html):
    entries = re.split(r"-{10,}", html)
    courses = []
    for entry in entries:
        entry = entry.strip()
        if not entry or entry == "&nbsp;":
            continue
        text = re.sub(r"<[^>]+>", "\n", entry)
        text = text.replace("&nbsp;", "").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            courses.append(" / ".join(lines))
    return courses


def parse_schedule(html):
    rows = re.findall(r"<tr>(.*?)</tr>", html, re.DOTALL)
    schedule = []
    for row in rows:
        th = re.search(r"<th[^>]*>(.*?)</th>", row, re.DOTALL)
        if not th:
            continue
        section_name = re.sub(r"<[^>]+>", "", th.group(1)).replace("&nbsp;", "").strip()
        if section_name not in SECTIONS:
            continue
        cells = re.findall(r'class="kbcontent"[^>]*>(.*?)</div>', row, re.DOTALL)
        day_courses = []
        for cell in cells:
            day_courses.append(parse_cell(cell))
        schedule.append((section_name, day_courses))

    remark = ""
    m = re.search(r"备注.*?<td[^>]*>(.*?)</td>", html, re.DOTALL)
    if m:
        remark = re.sub(r"<[^>]+>", "", m.group(1)).strip()

    return schedule, remark


def print_schedule(schedule, remark):
    col_width = 28
    header = f"{'':^10}" + "".join(f"{d:^{col_width}}" for d in DAYS)
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for section_name, day_courses in schedule:
        lines_per_day = []
        max_lines = 1
        for courses in day_courses:
            if courses:
                lines_per_day.append(courses)
                max_lines = max(max_lines, len(courses))
            else:
                lines_per_day.append([])
        for line_idx in range(max_lines):
            label = section_name if line_idx == 0 else ""
            row = f"{label:^10}"
            for day_idx in range(len(lines_per_day)):
                if line_idx < len(lines_per_day[day_idx]):
                    text = lines_per_day[day_idx][line_idx]
                    if len(text) > col_width - 2:
                        text = text[: col_width - 4] + ".."
                    row += f" {text:<{col_width - 1}}"
                else:
                    row += " " * col_width
            print(row)
        print(sep)
    if remark:
        print(f"备注: {remark}")
        print(sep)


def extract_login_params(html):
    salt = ""
    execution = ""
    salt_match = re.search(r'id="pwdEncryptSalt"\s+value="([^"]*)"', html)
    if salt_match:
        salt = salt_match.group(1)
    pwd_start = html.find('id="pwdLoginDiv"')
    if pwd_start != -1:
        pwd_section = html[pwd_start:]
        execution_match = re.search(r'name="execution"\s+value="([^"]*)"', pwd_section)
        if execution_match:
            execution = execution_match.group(1)
    return salt, execution


print("[1/5] 初始化会话")
session = requests.Session()
session.trust_env = False
session.headers.update({"User-Agent": random_uagent()})

print("[2/5] 访问 jwgl 入口并跳转到 CAS 登录页")
response = session.get("https://jwgl.gsau.edu.cn/", allow_redirects=True, timeout=30)
response.encoding = "utf-8"
print(f"    当前 URL: {response.url}")

salt, execution = extract_login_params(response.text)
print(f"    提取到 salt: {'是' if salt else '否'}")
print(f"    提取到 execution: {'是' if execution else '否'}")
if not execution:
    raise RuntimeError("未能从 pwdLoginDiv 提取 execution")

encrypted_password = encrypt_password(PASSWORD, salt)

print("[3/5] 提交 CAS 登录表单")
form_data = {
    "username": USERNAME,
    "password": encrypted_password,
    "captcha": "",
    "_eventId": "submit",
    "cllt": "userNameLogin",
    "dllt": "generalLogin",
    "lt": "",
    "execution": execution,
}
login_response = session.post(
    LOGIN_POST_URL, data=form_data, allow_redirects=True, timeout=30
)
login_response.encoding = "utf-8"
print(f"    登录后 URL: {login_response.url}")

print("[4/5] 检查并处理 JS 跳转")
redirect_steps = 0
current_response = login_response
while True:
    js_redirect = re.search(r"window\.location\.href='([^']+)'", current_response.text)
    if not js_redirect:
        break
    redirect_steps += 1
    js_url = js_redirect.group(1)
    print(f"    检测到 JS 跳转 #{redirect_steps}: {js_url}")
    current_response = session.get(js_url, allow_redirects=True, timeout=30)
    current_response.encoding = "utf-8"
    print(f"    跳转后 URL: {current_response.url}")
    if redirect_steps >= 5:
        break

print("[5/5] 获取学期理论课表")
schedule_response = session.get(SCHEDULE_URL, allow_redirects=True, timeout=30)
schedule_response.encoding = "utf-8"
print(f"    课表页 URL: {schedule_response.url}")

html = schedule_response.text
if "学期理论课表" in html:
    schedule, remark = parse_schedule(html)
    if schedule:
        print()
        print_schedule(schedule, remark)
    else:
        print("未解析到课程数据")
elif "登录" in html or "authserver" in schedule_response.url:
    print("登录失败或会话已失效")
    print(html[:600])
else:
    print("未识别的响应内容")
    print(html[:600])
