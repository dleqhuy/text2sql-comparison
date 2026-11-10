"""Generate report SVG figures from saved CSVs; standard library only."""

import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
COLORS = ["#2563eb", "#d97706", "#15803d", "#7c3aed"]
NAMES = ["DIN-SQL", "MAC-SQL", "DAIL-SQL", "Codex MCP SQL"]
KEYS = ["few_shot", "mac_sql", "dail_sql", "codex_mcp"]


def text(x, y, value, size=20, fill="#172033", anchor="middle", weight="normal"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(value))}</text>'


def save(name, title, height, parts, width=1000):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8" fill="none" stroke="#64748b" stroke-width="1.5"/></marker></defs>
<rect width="100%" height="100%" fill="white"/>
<g font-family="Arial, Helvetica, sans-serif">{text(width / 2, 39, title, 25, weight="bold")}{"".join(parts)}</g></svg>'''
    (OUT / f"{name}.svg").write_text(svg)


def flow(name, title, nodes, color="#2563eb", note=None):
    parts = []
    for i, lines in enumerate(nodes):
        y = 75 + i * 112
        parts.append(
            f'<rect x="130" y="{y}" width="740" height="78" rx="12" fill="#f8fafc" stroke="{color}" stroke-width="2"/>'
        )
        lines = lines if isinstance(lines, list) else [lines]
        for j, line in enumerate(lines):
            parts.append(
                text(500, y + (45 if len(lines) == 1 else 30 + j * 27), line, 20)
            )
        if i < len(nodes) - 1:
            parts.append(
                f'<path d="M500,{y + 78} V{y + 105}" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>'
            )
    height = 75 + len(nodes) * 112 + (35 if note else 0)
    if note:
        parts.append(text(500, height - 20, note, 17, "#475569"))
    save(name, title, height, parts)


flow(
    "01-overview",
    "Luồng thực nghiệm Text-to-SQL",
    [
        [
            "Spider dev: câu hỏi + db_id + schema/database",
            "1.034 câu • 20 database • cùng ID và thứ tự",
        ],
        "Chuẩn bị input chung và giữ gold cho bước đánh giá",
        [
            "DIN-SQL | MAC-SQL | DAIL-SQL | Codex MCP SQL",
            "Mỗi hệ thống sinh SQL theo cơ chế riêng",
        ],
        "Lưu raw/trace → chuẩn hóa prediction SQL",
        [
            "Chạy prediction và gold trên cùng database SQLite",
            "So sánh kết quả bằng evaluator chung",
        ],
        "Tổng hợp EX toàn tập và theo bốn mức độ khó",
    ],
)
flow(
    "07-evaluation",
    "Quy trình tính SQLite execution accuracy",
    [
        [
            "Prediction SQL + gold SQL + database tương ứng",
            "Gold không được dùng làm đáp án đầu vào cho mô hình",
        ],
        "Thực thi hai truy vấn bằng SQLite read-only",
        [
            "Kiểm tra số cột và so sánh kết quả",
            "Giữ dòng trùng; cho phép hoán vị cột nhất quán",
        ],
        [
            "Gold có ORDER BY ngoài cùng → xét thứ tự dòng",
            "Prediction rỗng hoặc lỗi thực thi → tính sai",
        ],
        [
            "EX = số câu khớp kết quả / tổng số câu",
            "Một database mỗi câu; không phải Test Suite Accuracy",
        ],
    ],
)

rows = list(csv.DictReader((ROOT.parent / "results/full_dev/by_difficulty.csv").open()))
summary = {
    r["method"]: float(r["EX"]) * 100
    for r in csv.DictReader((ROOT.parent / "results/full_dev/summary.csv").open())
}


def axes(parts, ymax=100, bottom=450, top=100):
    for tick in range(0, ymax + 1, 20):
        y = bottom - (bottom - top) * tick / ymax
        parts.append(f'<path d="M90,{y} H960" stroke="#e2e8f0"/>')
        parts.append(text(72, y + 6, tick, 17, anchor="end"))
    parts.append(text(90, 78, "EX (%)", 18, anchor="start"))


parts = []
for i, (label, count) in enumerate(
    zip(["Easy", "Medium", "Hard", "Extra"], [248, 446, 174, 166])
):
    x = 150 + i * 215
    h = count / 500 * 300
    parts.append(
        f'<rect x="{x}" y="{420 - h}" width="125" height="{h}" rx="4" fill="#2563eb"/>'
    )
    parts += [
        text(x + 62.5, 405 - h, count, 23, weight="bold"),
        text(x + 62.5, 455, label, 21),
    ]
parts.append(text(500, 505, "Tổng: 1.034 câu hỏi trên 20 database", 20, "#475569"))
save("02-difficulty", "Phân bố độ khó của Spider dev", 540, parts)
parts = []
axes(parts)
for i, key in enumerate(KEYS):
    x = 145 + i * 213
    value = summary[key]
    h = value * 3.5
    parts.append(
        f'<rect x="{x}" y="{450 - h}" width="120" height="{h}" rx="4" fill="{COLORS[i]}"/>'
    )
    parts += [
        text(x + 60, 435 - h, f"{value:.2f}%", 23, weight="bold"),
        text(x + 60, 485, NAMES[i], 19),
    ]
save("08-overall", "SQLite EX trên toàn bộ 1.034 câu", 530, parts)
parts = []
axes(parts, bottom=440, top=110)
for g, level in enumerate(["easy", "medium", "hard", "extra"]):
    for i, key in enumerate(KEYS):
        value = next(
            float(r["EX"]) * 100
            for r in rows
            if r["method"] == key and r["difficulty"] == level
        )
        x = 119 + g * 215 + i * 43
        h = value * 3.3
        parts.append(
            f'<rect x="{x}" y="{440 - h}" width="35" height="{h}" fill="{COLORS[i]}"/>'
        )
        parts.append(text(x + 17.5, 430 - h, f"{value:.1f}", 13))
    parts.append(text(201 + g * 215, 475, level.capitalize(), 20))
for i, name in enumerate(NAMES):
    x = 100 + i * 225
    parts.append(f'<rect x="{x}" y="510" width="16" height="16" fill="{COLORS[i]}"/>')
    parts.append(text(x + 24, 524, name, 18, anchor="start"))
save("09-by-difficulty", "SQLite EX theo độ khó", 560, parts)

files = sorted(OUT.glob("*.svg"))
(ROOT / "diagrams/preview.html").write_text(
    """<!doctype html><html lang="vi"><meta charset="utf-8"><title>Hình báo cáo Text-to-SQL</title><style>body{font-family:Arial;background:#e2e8f0;margin:32px}main{max-width:1000px;margin:auto}figure{margin:32px 0;padding:24px;background:white;border-radius:12px}img{width:100%;height:auto}figcaption{text-align:center;margin-top:12px;color:#475569}</style><main><h1>Hình báo cáo Text-to-SQL</h1>"""
    + "".join(
        f'<figure><img src="../figures/{p.name}" alt="{p.stem}"><figcaption>{p.name}</figcaption></figure>'
        for p in files
    )
    + "</main></html>"
)
print(f"Generated {len(files)} SVG figures.")
