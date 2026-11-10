"""Report-native SVG/HTML flows inspired by BPMN (not BPMN 2.0 XML)."""

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, H = 1400, 1400


class Flow:
    def __init__(self, color, lanes):
        self.color = color
        self.parts = []
        for i, (x, width, title) in enumerate(lanes):
            self.parts += [
                f'<rect x="{x}" y="0" width="{width}" height="{H}" fill="{["#f8fafc", "#fff", "#f1f5f9"][i % 3]}" stroke="#cbd5e1"/>',
                f'<rect x="{x}" width="{width}" height="64" fill="{color}" opacity="0.09"/>',
            ]
            self.text(x + width / 2, 37, [title], 21, bold=True)

    def text(self, x, y, lines, size=19, bold=False, color="#1e293b"):
        for i, line in enumerate(lines):
            self.parts.append(
                f'<text x="{x}" y="{y + (i - (len(lines) - 1) / 2) * 25}" text-anchor="middle" dominant-baseline="middle" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(line)}</text>'
            )

    def task(self, x, y, lines, width=188, height=76, kind="task"):
        self.parts.append(
            f'<rect x="{x - width / 2}" y="{y - height / 2}" width="{width}" height="{height}" rx="12" fill="white" stroke="{self.color}" stroke-width="2"/>'
        )
        if kind == "data":
            self.parts.append(
                f'<path d="M{x - width / 2 + 8},{y - height / 2 + 12} h14 v14 h-14 z" stroke="#64748b" fill="none"/>'
            )
        self.text(x, y, lines, 18, bold=True)

    def gateway(self, x, y, lines):
        self.parts.append(
            f'<path d="M{x},{y - 49} L{x + 73},{y} L{x},{y + 49} L{x - 73},{y} Z" fill="#fffbeb" stroke="#b45309" stroke-width="2"/>'
        )
        self.text(x, y, lines, 16, bold=True)

    def event(self, x, y, label, end=False):
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="23" fill="white" stroke="{self.color}" stroke-width="{5 if end else 2}"/>'
        )
        self.text(x, y + 45, [label], 17)

    def edge(self, points, label=None, at=None, dashed=False):
        d = "M" + " L".join(f"{x},{y}" for x, y in points)
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"'
            + (' stroke-dasharray="7 5"' if dashed else "")
            + "/>"
        )
        if label:
            x, y = at
            self.parts.append(
                f'<rect x="{x - len(label) * 5.3 - 7}" y="{y - 13}" width="{len(label) * 10.6 + 14}" height="26" rx="4" fill="white"/>'
            )
            self.text(x, y, [label], 16, color="#475569")

    def svg(self, title):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(title)}"><defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0 0 L10 4 L0 8 Z" fill="#475569"/></marker></defs><g font-family="Arial, Helvetica, sans-serif">'
            + "".join(self.parts)
            + "</g></svg>"
        )


def din():
    f = Flow(
        "#2563eb",
        [(0, 310, "ĐIỀU PHỐI"), (310, 780, "LLM"), (1090, 310, "SQLITE / ĐÁNH GIÁ")],
    )
    f.event(155, 125, "Bắt đầu")
    f.task(155, 250, ["Câu hỏi", "+ schema"])
    f.task(700, 250, ["Schema linking"])
    f.task(700, 385, ["Phân loại"])
    f.gateway(700, 515, ["Nhánh", "prompt?"])
    for x, lines in [
        (445, ["EASY"]),
        (700, ["NON-NESTED"]),
        (955, ["NESTED", "Câu hỏi con"]),
    ]:
        f.task(x, 655, lines, width=200)
    f.gateway(700, 770, ["Hợp luồng"])
    f.task(700, 900, ["Sinh SQL"])
    f.task(700, 1050, ["Self-correction"])
    f.task(155, 1050, ["SQL cuối"])
    f.task(1245, 1160, ["Chấm SQLite EX"])
    f.event(1245, 1240, "", True)
    f.edge([(155, 148), (155, 212)])
    f.edge([(249, 250), (606, 250)])
    f.edge([(700, 288), (700, 347)])
    f.edge([(700, 423), (700, 466)])
    f.edge([(627, 515), (445, 515), (445, 617)], "Easy", (488, 515))
    f.edge([(700, 564), (700, 617)], "Non-nested", (785, 589))
    f.edge([(773, 515), (955, 515), (955, 617)], "Nested", (920, 515))
    f.edge([(445, 693), (445, 770), (627, 770)])
    f.edge([(700, 693), (700, 721)])
    f.edge([(955, 693), (955, 770), (773, 770)])
    f.edge([(700, 819), (700, 862)])
    f.edge([(700, 938), (700, 1012)])
    f.edge([(606, 1050), (249, 1050)])
    f.edge([(155, 1088), (155, 1160), (1151, 1160)])
    f.edge([(1245, 1198), (1245, 1217)])
    f.text(
        700,
        1210,
        ["Debug bằng prompt; không lấy lỗi thực thi SQLite."],
        18,
        color="#64748b",
    )
    return f


def mac():
    f = Flow(
        "#d97706",
        [
            (0, 310, "ĐIỀU PHỐI"),
            (310, 650, "SELECTOR / LLM"),
            (960, 440, "SQLITE / REFINER"),
        ],
    )
    f.event(155, 125, "Bắt đầu")
    f.task(155, 250, ["Câu hỏi, schema", "+ giá trị mẫu"])
    f.gateway(155, 430, ["Cần lọc", "schema?"])
    f.task(635, 430, ["Selector"])
    f.task(635, 600, ["Decomposer", "Sinh SQL"])
    f.task(1180, 600, ["Refiner", "Thực thi SQL"])
    f.gateway(1180, 790, ["Lỗi thực", "thi?"])
    f.gateway(635, 790, ["Còn lượt", "sửa?"])
    f.task(635, 970, ["LLM sửa SQL", "từ thông báo lỗi"])
    f.event(155, 790, "Kết thúc với lỗi", True)
    f.task(1180, 1000, ["SQL cuối"])
    f.task(1180, 1150, ["Chấm SQLite EX"])
    f.event(1180, 1240, "", True)
    f.edge([(155, 148), (155, 212)])
    f.edge([(155, 288), (155, 381)])
    f.edge([(228, 430), (541, 430)], "Có", (360, 430))
    f.edge([(635, 468), (635, 562)])
    f.edge([(155, 479), (155, 600), (541, 600)], "Không", (350, 600))
    f.edge([(729, 600), (1086, 600)])
    f.edge([(1180, 638), (1180, 741)])
    f.edge([(1107, 790), (708, 790)], "Có", (930, 790))
    f.edge([(562, 790), (178, 790)], "Hết vòng", (400, 790))
    f.edge([(635, 839), (635, 932)], "Còn", (680, 886))
    f.edge(
        [(729, 970), (1000, 970), (1000, 685), (1180, 685), (1180, 638)],
        "Kiểm tra lại",
        (1000, 925),
    )
    f.edge([(1253, 790), (1355, 790), (1355, 1000), (1274, 1000)], "Không", (1300, 825))
    f.edge([(1180, 1038), (1180, 1112)])
    f.edge([(1180, 1188), (1180, 1217)])
    f.text(
        580,
        1160,
        ["Giới hạn vòng theo ChatManager.", "Chạy được chưa bảo đảm khớp gold."],
        18,
        color="#64748b",
    )
    return f


def dail():
    f = Flow(
        "#15803d",
        [
            (0, 310, "ĐIỀU PHỐI / DỮ LIỆU"),
            (310, 650, "TRUY XUẤT VÍ DỤ"),
            (960, 440, "LLM / ĐÁNH GIÁ"),
        ],
    )
    f.event(155, 125, "Bắt đầu")
    f.task(155, 250, ["Câu hỏi", "+ schema/database"])
    f.task(635, 250, ["Tiền xử lý", "Schema linking"])
    f.task(155, 470, ["Kho ví dụ train", "Câu hỏi + SQL"], kind="data")
    f.task(635, 470, ["Lượt 1", "Chọn 9 ví dụ"])
    f.task(1180, 470, ["LLM", "Sinh SQL sơ bộ"])
    f.task(1180, 680, ["SQL sơ bộ"], kind="data")
    f.task(635, 840, ["Lượt 2", "Chọn lại 9 ví dụ"])
    f.task(1180, 840, ["LLM", "Sinh SQL cuối"])
    f.task(155, 1050, ["Prediction SQL"])
    f.task(1180, 1160, ["Chấm SQLite EX"])
    f.event(1180, 1240, "", True)
    f.edge([(155, 148), (155, 212)])
    f.edge([(249, 250), (541, 250)])
    f.edge([(635, 288), (635, 432)])
    f.edge([(249, 470), (541, 470)], "Ví dụ train", (395, 470), dashed=True)
    f.edge([(155, 508), (155, 840), (541, 840)], "Ví dụ train", (350, 840), dashed=True)
    f.edge([(729, 470), (1086, 470)])
    f.edge([(1180, 508), (1180, 642)])
    f.edge(
        [(1086, 680), (820, 680), (820, 765), (635, 765), (635, 802)],
        "Tín hiệu cấu trúc",
        (920, 680),
    )
    f.edge(
        [(635, 508), (635, 600), (400, 600), (400, 740), (555, 740), (555, 802)],
        "Câu hỏi",
        (400, 700),
    )
    f.edge([(729, 840), (1086, 840)])
    f.edge([(1180, 878), (1180, 970), (155, 970), (155, 1012)])
    f.edge([(155, 1088), (155, 1160), (1086, 1160)])
    f.edge([(1180, 1198), (1180, 1217)])
    f.text(
        635,
        1230,
        ["SQL sơ bộ do mô hình sinh; gold chỉ dùng khi chấm."],
        18,
        color="#64748b",
    )
    return f


def codex():
    f = Flow(
        "#7c3aed",
        [(0, 310, "ĐIỀU PHỐI"), (310, 650, "AGENT CODEX"), (960, 440, "MCP / SQLITE")],
    )
    f.event(155, 125, "Bắt đầu")
    f.task(155, 250, ["Câu hỏi + db_id"])
    f.task(635, 250, ["Agent chọn", "bước tiếp theo"])
    f.gateway(635, 420, ["Còn ngân", "sách?"])
    f.event(155, 420, "Lưu trạng thái lỗi", True)
    f.gateway(635, 600, ["Chọn", "thao tác"])
    f.task(1180, 520, ["search_objects", "Khám phá schema"])
    f.task(1180, 710, ["execute_sql", "Thử SQL read-only"])
    f.task(1180, 880, ["Kết quả / lỗi", "công cụ"])
    f.gateway(635, 880, ["Đủ thông", "tin?"])
    f.task(635, 1060, ["Trả SQL cuối"])
    f.task(1180, 1060, ["Đối chiếu SQL", "với audit thành công"])
    f.gateway(1180, 1190, ["Audit", "khớp?"])
    f.event(155, 1190, "Lưu trạng thái lỗi", True)
    f.task(1180, 1320, ["Chấm SQLite EX"])
    f.event(900, 1320, "Kết thúc", True)
    f.edge([(155, 148), (155, 212)])
    f.edge([(249, 250), (541, 250)])
    f.edge([(635, 288), (635, 371)])
    f.edge([(562, 420), (178, 420)], "Không", (395, 420))
    f.edge([(635, 469), (635, 551)], "Có", (680, 510))
    f.edge([(708, 600), (875, 600), (875, 520), (1086, 520)], "Đọc schema", (885, 520))
    f.edge([(635, 649), (635, 710), (1086, 710)], "Thử truy vấn", (850, 710))
    f.edge([(1274, 520), (1345, 520), (1345, 880), (1274, 880)])
    f.edge([(1180, 748), (1180, 842)])
    f.edge([(1086, 880), (708, 880)])
    f.edge([(562, 880), (355, 880), (355, 250), (541, 250)], "Chưa đủ", (430, 880))
    f.edge([(635, 929), (635, 1022)], "Đủ", (675, 972))
    f.edge([(729, 1060), (1086, 1060)])
    f.edge([(1180, 1098), (1180, 1141)])
    f.edge([(1107, 1190), (178, 1190)], "Không", (620, 1190))
    f.edge([(1180, 1239), (1180, 1282)], "Có", (1220, 1260))
    f.edge([(1086, 1320), (923, 1320)])
    f.text(
        635,
        1380,
        ["Kết quả/lỗi giúp agent điều chỉnh trong ngân sách."],
        18,
        color="#64748b",
    )
    return f


CSS = """*{box-sizing:border-box}body{margin:0;padding:24px;background:#e8edf4;color:#172033;font-family:Arial,sans-serif}.sheet{width:1450px;max-width:none;margin:0 auto 36px;background:white;padding:24px;border-top:6px solid var(--accent);border-radius:12px}h1{font-size:28px;margin:0 0 10px}.subtitle{font-size:16px;color:#526174;line-height:1.6}.flow{width:1400px;height:auto;display:block;margin:22px 0;border-radius:6px}pre{background:#172437;color:white;padding:18px;border-radius:8px;font-size:16px;line-height:1.55;white-space:pre-wrap}.example{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:18px;background:#f1f5f9;border-radius:9px;font-size:17px;line-height:1.6}.example h2{font-size:18px;margin:0 0 8px}.legend{font-size:14px;color:#64748b;line-height:1.7;margin-top:18px}@media(max-width:700px){.example{grid-template-columns:1fr}body{padding:10px}.sheet{padding:14px}}@media print{body{padding:0;background:white}.sheet{break-after:page}}"""
COLORS = {"din": "#2563eb", "mac": "#d97706", "dail": "#15803d", "codex": "#7c3aed"}
TITLES = {
    "din": "DIN-SQL",
    "mac": "MAC-SQL",
    "dail": "DAIL-SQL",
    "codex": "Codex MCP SQL",
}
SQL = "SELECT COUNT(*)\nFROM ship\nWHERE disposition_of_ship = 'Captured';"
sections = []
for key, build in [("din", din), ("mac", mac), ("dail", dail), ("codex", codex)]:
    title = TITLES[key]
    svg = build().svg(title)
    (ROOT / "figures" / f"pipeline-{key}.svg").write_text(svg)
    example = (
        "Sơ đồ mô tả hai lượt trong implementation. Ví dụ DAIL live sẽ được bổ sung sau khi hoàn tất chạy."
        if key == "dail"
        else "Ví dụ từ phiên c9a7a364f737 · dev_0491 · battle_death. Kết quả thực thi: 4; khớp gold."
    )
    if key == "dail" and (ROOT / "examples/dail.json").exists():
        live = json.loads((ROOT / "examples/dail.json").read_text())
        example = (
            "Ví dụ thực tế từ phiên "
            + live["meta"]["id"]
            + " · dev_0491 · battle_death. Cả hai lượt chọn 9 ví dụ; SQL sơ bộ và SQL cuối cùng trả về 4, khớp gold."
        )
    if key == "mac":
        example += (
            " Trong phiên này Selector giữ schema; không phát sinh vòng LLM sửa SQL."
        )
    if key == "codex":
        example += " Trace có lỗi tham số search_objects rồi phục hồi thành công; SQL cuối thêm alias captured_ship_count."
    sql = (
        SQL
        if key != "codex"
        else SQL.replace("COUNT(*)", "COUNT(*) AS captured_ship_count")
    )
    if key == "dail" and (ROOT / "examples/dail.json").exists():
        sqls = [
            e["output"]
            for e in live["events"]
            if e["kind"] == "finish" and e["stage"].startswith("SQL generation")
        ]
        code = (
            "<p>Lượt 1 và lượt 2 sinh cùng SQL:</p><pre><code>"
            + escape(
                sqls[-1].replace(" FROM ", "\nFROM ").replace(" WHERE ", "\nWHERE ")
            )
            + "</code></pre>"
        )
    elif key == "dail":
        code = "<p>SQL sơ bộ → chọn lại ví dụ → SQL cuối</p>"
    else:
        code = f"<pre><code>{escape(sql)}</code></pre>"
    styled_svg = svg.replace("<svg ", '<svg class="flow" ', 1)
    body = f'<article class="sheet" id="{key}" style="--accent:{COLORS[key]}"><h1>{title}</h1><div class="subtitle">Luồng theo phong cách BPMN · swimlane, tác vụ, nút quyết định và vòng lặp</div>{styled_svg}<div class="example"><div><h2>Ví dụ và phạm vi quan sát</h2>{escape(example)}</div><div><h2>SQL / dữ liệu đi qua luồng</h2>{code}</div></div><div class="legend">○ Bắt đầu · ◉ Kết thúc · Hộp bo góc: tác vụ · Hình thoi: quyết định/hợp luồng · Nét liền: luồng xử lý · Nét đứt: dữ liệu đầu vào.<br>Sơ đồ thể hiện cơ chế tổng quát; các nhánh không nhất thiết xảy ra trong mọi lần chạy. Đây là hình minh hoạ cho báo cáo, không phải tệp BPMN 2.0 để thực thi.</div></article>'
    sections.append(body)
    (ROOT / "diagrams" / f"pipeline-{key}.html").write_text(
        f'<!doctype html><html lang="vi"><meta charset="utf-8"><title>Pipeline {title}</title><style>{CSS}</style>{body}</html>'
    )
(ROOT / "diagrams" / "pipelines.html").write_text(
    f'<!doctype html><html lang="vi"><meta charset="utf-8"><title>Pipeline Text-to-SQL · BPMN style</title><style>{CSS}</style>'
    + "".join(sections)
    + "</html>"
)
print("Generated four BPMN-style SVG/HTML flows.")
