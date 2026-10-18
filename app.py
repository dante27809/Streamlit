# -*- coding: utf-8 -*-
"""
THU VÀNG – Công thức nước hoa tương tác (Tổ 3 – mùa thu)
Dự án STEM Hóa học: Excel + lập trình + AI

Cách chạy:   pip install -r requirements.txt   →   streamlit run app.py

File gồm 5 phần, đọc theo thứ tự:
  1. Cấu hình và dữ liệu của nhóm
  2. Đọc bảng nguyên liệu do giáo viên cung cấp (nguyen_lieu_thu.csv)
  3. Hàm tính toán công thức     (không dùng Streamlit → kiểm thử được bằng test_app.py)
  4. Hàm hỗ trợ AI: soạn prompt, kiểm chứng đề xuất
  5. Giao diện Streamlit (hàm main)

ĐIỀU CẦN NHỚ
  • Giới hạn trong nguyen_lieu_thu.csv hiện là dữ liệu MÔ PHỎNG, KHÔNG phải giới hạn an toàn.
    Giáo viên phải thay bằng bảng đã duyệt (nhãn, SDS, giới hạn nhà cung cấp/IFRA).
  • "Hợp lệ" trong app chỉ có nghĩa là đúng phép tính và không vượt giới hạn dự án.
    Hợp lệ KHÔNG có nghĩa là an toàn.
  • Không ghi API key vào mã nguồn, prompt hay nhật ký.
"""
import csv
import math
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

# =====================================================================
# 1. CẤU HÌNH VÀ DỮ LIỆU CỦA NHÓM
# =====================================================================
THU_MUC = Path(__file__).resolve().parent
FILE_NGUYEN_LIEU = THU_MUC / "nguyen_lieu_thu.csv"

TEN_SAN_PHAM = "Thu Vàng"
MUA_MAC_DINH = "Thu"          # mùa mở sẵn khi vào app
MA_MAU_MAC_DINH = "THU-B2"    # mã mẫu điền sẵn (dùng trong tên file CSV)
DUNG_SAI = 1e-6          # sai số số học khi so sánh số thực (0.000001 điểm %)
DUNG_SAI_TONG = 0.01     # giống Excel: ABS(SUM(...) - 100) < 0.01
THE_TICH_MIN, THE_TICH_MAX = 1.0, 20.0
NGUONG_CAN_BANG = 5.0    # hai tầng lệch nhau dưới ngưỡng này (điểm %) → mô tả là "cân bằng"

TANG = ["Đầu", "Giữa", "Cuối"]            # thứ tự kim tự tháp mùi hương
MA_DUNG_MOI = "SO"
TEN_DUNG_MOI = "Dung môi (GV cung cấp)"

# Concept từng mùa và tỉ lệ tầng ĐỊNH HƯỚNG (lấy từ Bảng tham khảo bốn mẫu theo mùa).
# Chỉ để so sánh sau khi nhóm đã tự đề xuất công thức – KHÔNG phải quy tắc cố định.
MUA = {
    "Xuân": {"concept": "Tươi mới, trong trẻo, hoa dịu", "nhom_huong": "Citrus – Floral – Light Woody",
             "dinh_huong": {"Đầu": 35, "Giữa": 45, "Cuối": 20}},
    "Hạ": {"concept": "Mát, sáng, năng động", "nhom_huong": "Citrus – Herbal – Fresh",
           "dinh_huong": {"Đầu": 45, "Giữa": 40, "Cuối": 15}},
    "Thu": {"concept": "Dịu, ấm, trầm nhẹ", "nhom_huong": "Fruity – Floral – Woody",
            "dinh_huong": {"Đầu": 25, "Giữa": 40, "Cuối": 35}},
    "Đông": {"concept": "Ấm áp, sâu, sang trọng", "nhom_huong": "Aromatic – Vanilla – Woody",
             "dinh_huong": {"Đầu": 20, "Giữa": 35, "Cuối": 45}},
}

# Mô tả định tính từng tầng, dùng cho "hồ sơ mùi"
MO_TA_TANG = {
    "Đầu": "mở đầu tươi nhẹ, gợi trái cây ngọt dịu",
    "Giữa": "nét hoa cỏ mềm, chuyển mùa dịu",
    "Cuối": "nền gỗ ấm, sâu và lưu lại lâu hơn",
}

# ---- DỮ LIỆU CỦA NHÓM (nhóm được sửa phần này; GV KHÔNG khóa phần này) ----
# Tỉ lệ % trong chai thành phẩm. Phải nằm trong giới hạn của bảng GV.
CONG_THUC_NHOM = {
    "Thu": {
        "B":  {"SW": 2.1, "BG": 1.4, "LV": 2.4, "GE": 3.2, "CE": 2.5, "SA": 1.7, "VA": 0.7},  # v1: mẫu B vòng 1
        "B2": {"SW": 2.1, "BG": 1.7, "LV": 2.4, "GE": 3.2, "CE": 2.5, "SA": 2.0, "VA": 0.5},  # v2: P1 sau khi GV duyệt
    },
}

# Ví dụ đề xuất của AI (MÔ PHỎNG, xem prompt_log.md) – ghi dưới dạng CHÊNH LỆCH so với công thức B.
DE_XUAT_AI_MAU = {
    "Thu": {
        "P1": {"BG": +0.3, "SA": +0.3, "VA": -0.2},
        "P2": {"SW": -0.5, "LV": +0.5},
        "P3": {"GE": -0.4, "SA": +0.3, "VA": +0.5},   # VA vượt giới hạn → bị loại
    },
}

# Nội dung điền sẵn cho ô soạn prompt (mô phỏng, khớp prompt_log.md). Nhóm thật phải thay bằng dữ liệu của mình.
VI_DU_PROMPT = {
    "Thu": {
        "cam_quan": (
            "Mẫu B – vòng 1 – điểm trung bình của 5 người đánh giá qua các mốc thời gian, thang 1–5 "
            "(chấm theo mã mù; độ lưu mùi chỉ chấm ở 60 phút và 24 giờ):\n"
            "- Phù hợp mùa thu: 4.5\n"
            "- Cân bằng ba tầng: 4.3\n"
            "- Dễ chịu: 4.2\n"
            "- Độ rõ tầng hương: 4.2\n"
            "- Độ lưu mùi: 4.0\n"
            "- Điểm tổng hợp có trọng số (25-25-20-15-15): 4.27\n"
            "Diễn biến theo thời gian:\n"
            "- 0 phút: cam ngọt và bergamot mở đầu dịu, hơi ngọt trái cây.\n"
            "- 15 phút: hương hoa (geranium, lavender) hiện rõ, chuyển mùa mềm.\n"
            "- 60 phút: nền gỗ ấm xuất hiện; vài người thấy hơi ngọt kiểu kẹo.\n"
            "- 24 giờ: còn nền gỗ khô nhẹ, mỏng."
        ),
        "nhan_xet": "Ấm và dịu, đúng chất mùa thu nhưng hơi ngọt ở mốc 60 phút; nền gỗ cuối chưa đủ mịn và sâu.",
        "muc_tieu": "Giảm cảm giác ngọt ở 60 phút; tăng chiều sâu gỗ mịn ở tầng cuối; giữ nét trái cây nhẹ ở tầng đầu.",
    },
}
MAU_TRONG = {
    "cam_quan": "[DÁN BẢNG ĐIỂM CẢM QUAN: trung bình theo tiêu chí và theo mốc 0 phút – 15 phút – 60 phút – 24 giờ]",
    "nhan_xet": "[DÁN NHẬN XÉT CỦA NGƯỜI ĐÁNH GIÁ]",
    "muc_tieu": "[VIẾT MỤC TIÊU CẢI THIỆN CỦA NHÓM]",
}


# =====================================================================
# 2. ĐỌC BẢNG NGUYÊN LIỆU DO GIÁO VIÊN CUNG CẤP
# =====================================================================
COT_BAT_BUOC = ["ma", "mua", "ten", "tang", "vai_tro", "gioi_han_pct"]
_TANG_THEO_TEN = {"dau": "Đầu", "giua": "Giữa", "cuoi": "Cuối"}
_MUA_THEO_TEN = {"xuan": "Xuân", "ha": "Hạ", "thu": "Thu", "dong": "Đông"}


class LoiBangNguyenLieu(ValueError):
    """Bảng nguyên liệu do giáo viên cung cấp bị thiếu hoặc sai định dạng."""


def bo_dau(chuoi):
    """'Giữa' -> 'Giua', 'Đầu' -> 'Dau': so sánh chữ không phụ thuộc dấu."""
    s = unicodedata.normalize("NFD", str(chuoi))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def _chuan_hoa_ten_cot(ten_cot):
    return re.sub(r"[^a-z0-9]+", "_", bo_dau(ten_cot).lower()).strip("_")


def _doc_so(gia_tri):
    """'2.5' và '2,5' đều là 2.5. Trả về None nếu không phải số hữu hạn."""
    try:
        x = float(str(gia_tri).strip().replace(",", "."))
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def _doc_file_csv(duong_dan):
    """Thử UTF-8 trước, rồi cp1258 (Excel tiếng Việt đời cũ). Tự nhận dấu phân cách ',' hoặc ';'."""
    for ma_hoa in ("utf-8-sig", "cp1258"):
        try:
            return pd.read_csv(duong_dan, sep=None, engine="python", encoding=ma_hoa,
                               dtype=str, skipinitialspace=True)
        except UnicodeDecodeError:
            continue
        except (pd.errors.ParserError, pd.errors.EmptyDataError, csv.Error) as loi:
            raise LoiBangNguyenLieu(f"File '{duong_dan.name}' không đúng định dạng CSV ({loi}).")
    raise LoiBangNguyenLieu(
        f"Không đọc được tiếng Việt trong '{duong_dan.name}'. "
        "Hãy lưu lại bằng định dạng 'CSV UTF-8' (Excel: Save As → CSV UTF-8)."
    )


def doc_bang_nguyen_lieu(duong_dan=FILE_NGUYEN_LIEU):
    """
    Đọc và kiểm tra bảng nguyên liệu của GV. Trả về DataFrame gồm các cột:
    ma, mua, ten, tang, vai_tro, gioi_han_pct (số), trang_thai, da_duyet (True/False).
    Nếu dữ liệu sai, ném LoiBangNguyenLieu với danh sách lỗi cụ thể để GV sửa một lần.
    """
    duong_dan = Path(duong_dan)
    if not duong_dan.exists():
        raise LoiBangNguyenLieu(
            f"Không tìm thấy file '{duong_dan.name}'. Hãy đặt file này cùng thư mục với app.py."
        )
    df = _doc_file_csv(duong_dan)
    df.columns = [_chuan_hoa_ten_cot(c) for c in df.columns]

    thieu = [c for c in COT_BAT_BUOC if c not in df.columns]
    if thieu:
        raise LoiBangNguyenLieu(
            "Thiếu cột: " + ", ".join(thieu) + ". Hàng tiêu đề cần có: " + ", ".join(COT_BAT_BUOC)
            + " (cột trang_thai là tùy chọn)."
        )

    df = df.dropna(how="all").copy()
    if df.empty:
        raise LoiBangNguyenLieu("Bảng nguyên liệu không có dòng dữ liệu nào.")

    for c in ("ma", "mua", "ten", "tang", "vai_tro"):
        df[c] = df[c].fillna("").astype(str).str.strip()
    if "trang_thai" not in df.columns:
        df["trang_thai"] = ""
    df["trang_thai"] = df["trang_thai"].fillna("").astype(str).str.strip()

    loi, gioi_han = [], []
    for i, r in df.iterrows():
        dong = f"Dòng dữ liệu {i + 1}"
        if not r["ma"]:
            loi.append(f"{dong}: thiếu mã nguyên liệu.")
        elif r["ma"].upper() == MA_DUNG_MOI:
            loi.append(f"{dong}: mã '{MA_DUNG_MOI}' dành riêng cho dung môi, hãy dùng mã khác.")
        if bo_dau(r["mua"]).lower() not in _MUA_THEO_TEN:
            loi.append(f"{dong} ({r['ma']}): mùa '{r['mua']}' không hợp lệ (dùng Xuân, Hạ, Thu hoặc Đông).")
        if bo_dau(r["tang"]).lower() not in _TANG_THEO_TEN:
            loi.append(f"{dong} ({r['ma']}): tầng '{r['tang']}' không hợp lệ (dùng Đầu, Giữa hoặc Cuối).")
        x = _doc_so(r["gioi_han_pct"])
        if x is None or x < 0:
            loi.append(f"{dong} ({r['ma']}): giới hạn '{r['gioi_han_pct']}' phải là số không âm.")
        gioi_han.append(x)
    if loi:
        raise LoiBangNguyenLieu("\n".join("- " + x for x in loi))

    df["mua"] = df["mua"].map(lambda x: _MUA_THEO_TEN[bo_dau(x).lower()])
    df["tang"] = df["tang"].map(lambda x: _TANG_THEO_TEN[bo_dau(x).lower()])
    df["gioi_han_pct"] = gioi_han
    trung = df[df.duplicated(subset=["mua", "ma"], keep=False)]
    if not trung.empty:
        ds = ", ".join(sorted({f"{r.ma} ({r.mua})" for r in trung.itertuples()}))
        raise LoiBangNguyenLieu(f"- Mã bị trùng trong cùng một mùa: {ds}.")

    # Chỉ khi GV ghi đúng "ĐÃ DUYỆT" thì dữ liệu mới được coi là đã duyệt.
    df["da_duyet"] = df["trang_thai"].map(lambda x: bo_dau(x).upper().replace(" ", "_") == "DA_DUYET")
    cot = ["ma", "mua", "ten", "tang", "vai_tro", "gioi_han_pct", "trang_thai", "da_duyet"]
    return df[cot].reset_index(drop=True)


def nguyen_lieu_theo_mua(bang, mua):
    return bang[bang["mua"] == mua].reset_index(drop=True)


# =====================================================================
# 3. HÀM TÍNH TOÁN CÔNG THỨC (không dùng Streamlit)
# =====================================================================
def _la_so(x):
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def calculate_formula(volume, percents, ingredients):
    """
    volume      : thể tích mẻ (mL)
    percents    : dict {mã: % thể tích trong chai thành phẩm}
    ingredients : DataFrame bảng nguyên liệu của một mùa (cột ma, ten, tang, vai_tro, gioi_han_pct)

    Dung môi = 100 - tổng các thành phần hương. Thể tích từng dòng = volume × % / 100.
    Mọi phép so sánh dùng số CHƯA làm tròn; làm tròn chỉ khi hiển thị.
    Trả về dict: df, errors, valid, fragrance_pct, solvent_pct, total_pct, total_ml.
    """
    errors = []
    if not _la_so(volume) or float(volume) <= 0:
        errors.append("Thể tích mẻ phải là số lớn hơn 0 mL.")
        v = 0.0
    else:
        v = float(volume)

    rows, tong_huong = [], 0.0
    for r in ingredients.itertuples():
        gia_tri = percents.get(r.ma)
        if not _la_so(gia_tri):
            errors.append(f"{r.ten}: chưa có giá trị tỉ lệ.")
            pct = 0.0
        else:
            pct = float(gia_tri)
        tong_huong += pct

        kiem_tra = "Đạt"
        if pct < -DUNG_SAI:
            kiem_tra = "Âm"
            errors.append(f"{r.ten}: tỉ lệ {pct:.2f}% là số âm.")
        elif pct > r.gioi_han_pct + DUNG_SAI:
            kiem_tra = "Vượt giới hạn"
            errors.append(f"{r.ten}: {pct:.2f}% vượt giới hạn dự án {r.gioi_han_pct:.2f}%.")
        rows.append({
            "Mã": r.ma, "Thành phần": r.ten, "Tầng": r.tang, "Vai trò": r.vai_tro,
            "Tỉ lệ (%)": pct, "Giới hạn GV (%)": float(r.gioi_han_pct),
            "Thể tích (mL)": v * pct / 100.0, "Kiểm tra": kiem_tra,
        })

    solvent = 100.0 - tong_huong
    if abs(solvent) <= DUNG_SAI:
        solvent = 0.0                      # tránh hiển thị -0.000
    if solvent < 0:
        errors.append(f"Dung môi âm ({solvent:.2f}%): tổng các thành phần hương đang vượt 100%.")
    rows.append({
        "Mã": MA_DUNG_MOI, "Thành phần": TEN_DUNG_MOI, "Tầng": "Dung môi", "Vai trò": "Bù đến 100%",
        "Tỉ lệ (%)": solvent, "Giới hạn GV (%)": float("nan"),
        "Thể tích (mL)": v * solvent / 100.0, "Kiểm tra": "Đạt" if solvent >= 0 else "Âm",
    })

    df = pd.DataFrame(rows)
    # Phần/100 phần hương: so sánh được với "công thức 100 phần" trong bảng tham khảo
    huong = df["Mã"] != MA_DUNG_MOI
    df["Số phần / 100 phần hương"] = float("nan")
    if tong_huong > DUNG_SAI:
        df.loc[huong, "Số phần / 100 phần hương"] = df.loc[huong, "Tỉ lệ (%)"] / tong_huong * 100.0

    total_pct = float(df["Tỉ lệ (%)"].sum())
    total_ml = float(df["Thể tích (mL)"].sum())
    if abs(total_pct - 100.0) > 0.001:      # phòng thủ: không thể xảy ra nếu mã đúng
        errors.append(f"Tổng công thức hiện là {total_pct:.3f}%, không bằng 100%.")

    return {"df": df, "errors": errors, "valid": not errors, "fragrance_pct": tong_huong,
            "solvent_pct": solvent, "total_pct": total_pct, "total_ml": total_ml}


def tier_shares(df):
    """% của từng tầng TRONG hỗn hợp hương (không tính dung môi); tổng = 100. Rỗng nếu chưa có hương."""
    huong = df[df["Mã"] != MA_DUNG_MOI]
    tong = float(huong["Tỉ lệ (%)"].sum())
    if tong <= DUNG_SAI:
        return {}
    return {t: float(huong.loc[huong["Tầng"] == t, "Tỉ lệ (%)"].sum()) / tong * 100.0 for t in TANG}


def dominant_tier_description(df):
    """Mô tả định tính dựa trên tầng chiếm ưu thế; nếu hai tầng lớn nhất gần bằng nhau thì mô tả là cân bằng."""
    shares = tier_shares(df)
    if not shares:
        return "Chưa có thành phần hương để tạo mô tả."
    (t1, s1), (t2, s2) = sorted(shares.items(), key=lambda kv: kv[1], reverse=True)[:2]
    if s1 - s2 < NGUONG_CAN_BANG - 1e-9:
        return (f"Hồ sơ mùi cân bằng giữa tầng {t1} ({s1:.1f}% hỗn hợp hương) và tầng {t2} "
                f"({s2:.1f}%): {MO_TA_TANG[t1]}; {MO_TA_TANG[t2]}.")
    return f"Hồ sơ mùi thiên về tầng {t1} ({s1:.1f}% hỗn hợp hương): {MO_TA_TANG[t1]}."


def format_table(df):
    """Bảng hiển thị: mọi cột là chuỗi (tránh lỗi Arrow khi trộn số và chữ), mL và % có 3 chữ số thập phân."""
    def f(x, so_le):
        return "—" if pd.isna(x) else f"{x:.{so_le}f}"
    return pd.DataFrame({
        "Mã": df["Mã"], "Thành phần": df["Thành phần"], "Tầng": df["Tầng"], "Vai trò": df["Vai trò"],
        "Tỉ lệ trong chai (%)": [f(x, 3) for x in df["Tỉ lệ (%)"]],
        "Giới hạn GV (%)": [f(x, 2) for x in df["Giới hạn GV (%)"]],
        "Thể tích (mL)": [f(x, 3) for x in df["Thể tích (mL)"]],
        "Kiểm tra": df["Kiểm tra"],
        "Số phần / 100 phần hương": [f(x, 2) for x in df["Số phần / 100 phần hương"]],
    })


def ten_file_csv(ma_mau, the_tich):
    sach = re.sub(r"[^A-Za-z0-9_-]+", "_", bo_dau(ma_mau)).strip("_") or "cong_thuc"
    return f"{sach}_{the_tich:g}mL.csv"


def build_csv(result, ma_mau, the_tich, da_duyet):
    """CSV theo đúng cột của sheet CONG_THUC trong Excel (mục 7 kế hoạch) + cột trạng thái. UTF-8 có BOM."""
    df = result["df"]
    out = pd.DataFrame({
        "Mã mẫu": ma_mau.strip(),
        "Mã": df["Mã"],
        "Nguyên liệu": df["Thành phần"],
        "Tầng hương": df["Tầng"],
        "Tỉ lệ (%)": df["Tỉ lệ (%)"].round(3),
        "Giới hạn GV (%)": df["Giới hạn GV (%)"].round(3),
        "Thể tích mẻ (mL)": round(float(the_tich), 3),
        "Thể tích thành phần (mL)": df["Thể tích (mL)"].round(3),
        "Kiểm tra thành phần": df["Kiểm tra"],
        "Nguồn giới hạn": "GV đã đánh dấu duyệt" if da_duyet else "Mô phỏng – chưa duyệt",
        "Trạng thái": "Chưa GV duyệt an toàn",
    })
    return out.to_csv(index=False).encode("utf-8-sig")


# =====================================================================
# 4. HÀM HỖ TRỢ AI: SOẠN PROMPT VÀ KIỂM CHỨNG ĐỀ XUẤT
# =====================================================================
def build_prompt(mua, goc_df, cam_quan, nhan_xet, muc_tieu, so_tp_toi_da, muc_doi_toi_da):
    """
    Soạn prompt đủ 4 phần: DỮ LIỆU – MỤC TIÊU – RÀNG BUỘC – ĐỊNH DẠNG ĐẦU RA.
    goc_df: DataFrame có cột ma, ten, tang, gioi_han_pct, pct (công thức gốc, % trong chai).
    Số liệu và ràng buộc do app điền để không gõ nhầm; không chứa dữ liệu cá nhân hay API key.
    """
    dong_cong_thuc = "\n".join(
        f"- {r.ma} | {r.ten} | tầng {r.tang} | hiện tại {r.pct:g}% | giới hạn dự án ≤ {r.gioi_han_pct:g}%"
        for r in goc_df.itertuples()
    )
    dung_moi = 100.0 - float(goc_df["pct"].sum())
    concept = MUA[mua]["concept"]
    return (
        f"Bạn là trợ lý phân tích dữ liệu cho dự án STEM Hóa học về nước hoa học đường, chủ đề mùa {mua} "
        f"(concept: {concept}). Phạm vi: mô hình học tập, chỉ đánh giá mùi trên giấy thử.\n"
        "\n"
        "NHIỆM VỤ\n"
        "Phân tích dữ liệu cảm quan của công thức hiện tại và đề xuất tối đa 3 phương án điều chỉnh (P1, P2, P3).\n"
        "\n"
        "DỮ LIỆU\n"
        "1) Công thức hiện tại (tỉ lệ % thể tích trong chai thành phẩm):\n"
        f"{dong_cong_thuc}\n"
        f"- SO | Dung môi | bù đến 100% | hiện tại {dung_moi:g}%\n"
        "2) Điểm cảm quan và diễn biến theo thời gian:\n"
        f"{cam_quan.strip()}\n"
        "3) Nhận xét chính của người đánh giá:\n"
        f"{nhan_xet.strip()}\n"
        "\n"
        "MỤC TIÊU CẢI THIỆN\n"
        f"{muc_tieu.strip()}\n"
        "\n"
        "RÀNG BUỘC (bắt buộc)\n"
        "1. Chỉ dùng đúng các nguyên liệu trong bảng; không thêm nguyên liệu mới.\n"
        f"2. Mỗi phương án chỉ đổi tối đa {so_tp_toi_da} thành phần hương.\n"
        f"3. Mỗi thành phần đổi không quá ±{muc_doi_toi_da:g} điểm phần trăm so với hiện tại.\n"
        "4. Không vượt giới hạn dự án ở cột \"giới hạn\".\n"
        "5. Tổng tất cả thành phần, kể cả dung môi, phải đúng 100%; dung môi bù phần còn lại.\n"
        "6. Không kết luận công thức là an toàn; không thay thế SDS, giới hạn của nhà cung cấp/IFRA "
        "và quyết định của giáo viên.\n"
        "7. Chỉ dựa trên dữ liệu được cung cấp; không tự tạo dữ liệu; dự đoán về mùi chỉ là giả thuyết.\n"
        "\n"
        "ĐỊNH DẠNG ĐẦU RA\n"
        "- Mỗi phương án một bảng gồm: mã thành phần, tỉ lệ cũ, tỉ lệ mới, chênh lệch, lý do dựa trên dữ liệu.\n"
        "- Ghi rõ dung môi mới và tổng sau thay đổi.\n"
        "- Nêu những điểm nhóm cần kiểm chứng bằng Excel/ứng dụng và bằng thực nghiệm.\n"
        "- Không chọn phương án thay cho nhóm."
    )


def check_proposal(base, proposal, limits, max_changed=3, max_delta=0.5):
    """
    Kiểm chứng MỘT đề xuất của AI bằng đúng các ràng buộc đã ghi trong prompt.
    base, proposal : dict {mã: %}; proposal có thêm khóa 'SO' = dung môi do AI nêu (có thể None)
    limits         : dict {mã: giới hạn %}
    Trả về dict: rules (list {name, ok, detail}; ok=None nghĩa là chưa kiểm tra), passed, failed, delta.
    app KHÔNG tự sửa số của AI: nếu AI báo tổng sai thì phải bị phát hiện, không được che đi.
    """
    ma_list = list(limits)
    ten = ["Đủ số liệu", "Không có số âm", "Trong giới hạn dự án",
           f"Đổi tối đa {max_changed} thành phần", f"Mỗi thành phần đổi ≤ ±{max_delta:g} điểm %",
           "Tổng kể cả dung môi = 100%", "Dung môi không âm"]
    rules = []

    def them(chi_so, ok, chi_tiet):
        rules.append({"name": ten[chi_so], "ok": ok, "detail": chi_tiet})

    p = {m: proposal.get(m) for m in ma_list}
    sv = proposal.get(MA_DUNG_MOI)
    thieu = [m for m in ma_list if not _la_so(p[m])] + ([] if _la_so(sv) else [MA_DUNG_MOI])
    if thieu:
        them(0, False, "thiếu: " + ", ".join(thieu))
        for k in range(1, len(ten)):
            them(k, None, "chưa kiểm tra")
        return {"rules": rules, "passed": False, "failed": [ten[0]], "delta": {}}
    them(0, True, f"đủ {len(ma_list)} thành phần + dung môi")

    v = {m: float(p[m]) for m in ma_list}
    sv = float(sv)
    delta = {m: round(v[m] - float(base.get(m, 0.0)), 6) for m in ma_list}

    am = [m for m in ma_list if v[m] < -DUNG_SAI]
    them(1, not am, ", ".join(f"{m} {v[m]:g}%" for m in am) if am else "không có số âm")

    vuot = [m for m in ma_list if v[m] > float(limits[m]) + DUNG_SAI]
    them(2, not vuot, "; ".join(f"{m} {v[m]:.2f}% > {float(limits[m]):.2f}%" for m in vuot)
         if vuot else "đều ≤ giới hạn")

    doi = [m for m in ma_list if abs(delta[m]) > DUNG_SAI]
    them(3, len(doi) <= max_changed,
         f"đổi {len(doi)}: " + ", ".join(doi) if doi else "không đổi thành phần nào")

    qua_muc = [m for m in doi if abs(delta[m]) > max_delta + DUNG_SAI]
    if qua_muc:
        them(4, False, ", ".join(f"{m} {delta[m]:+.2f}" for m in qua_muc))
    elif doi:
        lon_nhat = max(doi, key=lambda m: abs(delta[m]))
        them(4, True, f"lớn nhất {lon_nhat} {delta[lon_nhat]:+.2f}")
    else:
        them(4, True, "không có thay đổi")

    tong = sum(v.values()) + sv
    them(5, abs(tong - 100.0) <= DUNG_SAI_TONG, f"tổng {tong:.2f}%")
    them(6, sv >= -DUNG_SAI, f"dung môi {sv:.2f}%")

    return {"rules": rules, "passed": all(r["ok"] is True for r in rules),
            "failed": [r["name"] for r in rules if r["ok"] is False], "delta": delta}


def mo_ta_loi(ket_qua):
    """'Trong giới hạn dự án (VA 1.20% > 1.00%); Tổng … (tổng 100.30%)': nói rõ sai ở đâu, không chỉ nêu tên điều kiện."""
    return "; ".join(f"{r['name']} ({r['detail']})" for r in ket_qua["rules"] if r["ok"] is False)


# =====================================================================
# 5. GIAO DIỆN STREAMLIT
# =====================================================================
MAU_CHINH, MAU_PHU = "#A55A08", "#6F7F3E"     # hổ phách và xanh rêu
COT_THANH_TRUOT = "Thanh trượt hiện tại"


def khoa_thanh_truot(mua, ma, gioi_han):
    """Khóa (key) của thanh trượt. Có cả giới hạn: khi GV đổi giới hạn trong CSV, thanh trượt được tạo lại
    với giá trị mặc định mới thay vì giữ giá trị cũ có thể đã vượt giới hạn mới."""
    return f"slider_{mua}_{ma}_{gioi_han:g}".replace(".", "p")


def render_sidebar():
    with st.sidebar:
        st.header("Thiết lập")
        ds_mua = list(MUA)
        mua = st.selectbox("Chọn mùa", ds_mua, index=ds_mua.index(MUA_MAC_DINH), key="mua")
        the_tich = st.number_input("Thể tích mẻ (mL)", min_value=THE_TICH_MIN, max_value=THE_TICH_MAX,
                                   value=10.0, step=0.5, key="the_tich")
        ma_mau = st.text_input("Mã mẫu", value=MA_MAU_MAC_DINH, key="ma_mau",
                               help="Ví dụ THU-A, THU-B2. Mã này nằm trong tên file CSV và cột 'Mã mẫu'.")
        st.info(f"Concept mùa {mua}: {MUA[mua]['concept']}\n\nNhóm hương: {MUA[mua]['nhom_huong']}")
    return mua, the_tich, ma_mau


def render_sliders(mua, nl):
    """Thanh trượt theo ba tầng. Giới hạn trên của mỗi thanh trượt lấy từ bảng của GV."""
    st.subheader("1. Điều chỉnh tỉ lệ thành phần")
    st.caption("Mỗi thanh trượt là % thể tích của thành phần trong CẢ CHAI thành phẩm; dung môi tự bù đến 100%. "
               "Đây không phải 'số phần trên 100 phần hương' trong bảng tham khảo.")
    mac_dinh = CONG_THUC_NHOM.get(mua, {}).get("B2", {})
    percents, thong_bao = {}, []
    cot = st.columns(len(TANG))
    for c, tang in zip(cot, TANG):
        with c:
            st.markdown(f"**Hương {tang.lower()}**")
            ma_tang = []
            for r in nl[nl["tang"] == tang].itertuples():
                gioi_han = float(r.gioi_han_pct)
                if gioi_han <= 0:
                    st.caption(f"{r.ten} ({r.ma}): giới hạn 0% – không sử dụng.")
                    percents[r.ma] = 0.0
                    continue
                gia_tri = float(mac_dinh.get(r.ma, 0.0))
                if gia_tri > gioi_han:      # GV hạ giới hạn thấp hơn giá trị mặc định → không để app báo lỗi
                    thong_bao.append(f"{r.ten}: giá trị mặc định {gia_tri:g}% vượt giới hạn {gioi_han:g}% "
                                     "nên được đặt bằng giới hạn.")
                    gia_tri = gioi_han
                percents[r.ma] = st.slider(
                    f"{r.ten} ({r.ma})", min_value=0.0, max_value=gioi_han, value=gia_tri,
                    step=0.1, format="%.1f", key=khoa_thanh_truot(mua, r.ma, gioi_han),
                    help=f"Vai trò: {r.vai_tro}. Giới hạn dự án: {gioi_han:g}%.")
                ma_tang.append(r.ma)
            st.caption(f"Tổng tầng {tang.lower()}: {sum(percents[m] for m in ma_tang):.2f}%")
    if thong_bao:
        st.info("\n\n".join(thong_bao))
    return percents


def render_validation(kq):
    st.subheader("2. Kiểm tra công thức")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Tổng hương", f"{kq['fragrance_pct']:.2f}%")
    m2.metric("Dung môi", f"{kq['solvent_pct']:.2f}%")
    m3.metric("Tổng cộng", f"{kq['total_pct']:.3f}%")
    m4.metric("Tổng thể tích", f"{kq['total_ml']:.3f} mL")
    m5.metric("Trạng thái (tính toán)", "Hợp lệ" if kq["valid"] else "Chưa hợp lệ")
    if kq["errors"]:
        for loi in kq["errors"]:
            st.error(loi)
    else:
        st.success("Công thức hợp lệ về mặt tính toán (tổng đúng 100%, không vượt giới hạn dự án): "
                   "đủ điều kiện gửi giáo viên xem xét. Điều này chưa có nghĩa là an toàn.")


def render_profile(mua, kq):
    st.subheader("4. Hồ sơ mùi theo tầng hương")
    st.write(dominant_tier_description(kq["df"]))
    shares = tier_shares(kq["df"])
    if shares:
        so_sanh = st.checkbox("So sánh với tỉ lệ tầng định hướng của mùa "
                              "(chỉ bật sau khi nhóm đã tự đề xuất công thức)", value=False, key="so_sanh")
        nhan = [f"{i + 1}. {t}" for i, t in enumerate(TANG)]      # tiền tố số để biểu đồ giữ đúng thứ tự tầng
        bieu_do = pd.DataFrame({"Công thức của nhóm (% hỗn hợp hương)": [shares[t] for t in TANG]}, index=nhan)
        mau = MAU_CHINH
        if so_sanh:
            bieu_do["Định hướng của mùa (tham khảo)"] = [float(MUA[mua]["dinh_huong"][t]) for t in TANG]
            mau = [MAU_CHINH, MAU_PHU]
        st.bar_chart(bieu_do, color=mau)
        st.caption("Tỉ lệ tầng tính trên hỗn hợp hương, không tính dung môi. Tỉ lệ định hướng chỉ là điểm xuất phát "
                   "để so sánh; không phải quy tắc cố định và không dùng để quyết định công thức hợp lệ.")
    st.caption("Mô tả định tính dựa trên tỉ lệ tầng hương; không phải đánh giá mùi thật và không phải đánh giá an toàn.")


def render_export(kq, ma_mau, the_tich, da_duyet):
    st.subheader("5. Xuất công thức")
    if not ma_mau.strip():
        st.info("Hãy nhập mã mẫu ở thanh bên để xuất CSV.")
    elif not kq["valid"]:
        st.info("Nút tải CSV chỉ xuất hiện khi công thức hợp lệ về mặt tính toán.")
    else:
        st.download_button("⬇️ Tải công thức CSV", data=build_csv(kq, ma_mau, the_tich, da_duyet),
                           file_name=ten_file_csv(ma_mau, the_tich), mime="text/csv")
        st.caption("File CSV ghi rõ 'Chưa GV duyệt an toàn'. Mở bằng Excel: Dữ liệu → Từ văn bản/CSV → chọn UTF-8, "
                   "dấu phân cách là dấu phẩy. Hoặc dùng Google Sheets: Tệp → Nhập.")


def render_ai(mua, nl, percents, kq):
    st.subheader("6. Dùng AI có kiểm soát")
    st.caption("AI chỉ đề xuất. Nhóm tự kiểm tra từng con số, chọn hoặc bác bỏ rồi ghi lý do vào prompt_log.md.")

    cong_thuc_goc = CONG_THUC_NHOM.get(mua, {}).get("B")
    de_xuat_mau = DE_XUAT_AI_MAU.get(mua)
    co_mau = bool(cong_thuc_goc and de_xuat_mau)
    lua_chon = ["Xem ví dụ mẫu (gốc = công thức B; đề xuất = P1–P3 trong prompt_log.md)",
                "Làm với công thức của nhóm (gốc = thanh trượt hiện tại)"]
    if not co_mau:
        lua_chon = lua_chon[1:]
    che_do = st.radio("Chế độ làm việc", lua_chon, key=f"che_do_ai_{mua}")
    dung_mau = co_mau and che_do == lua_chon[0]

    c1, c2 = st.columns(2)
    with c1:
        so_tp = st.number_input("Mỗi phương án chỉ đổi tối đa … thành phần", min_value=1, max_value=len(nl),
                                value=min(3, len(nl)), step=1, key="so_tp_toi_da")
    with c2:
        muc_doi = st.number_input("Mỗi thành phần đổi tối đa ± … điểm %", min_value=0.1, max_value=5.0,
                                  value=0.5, step=0.1, key="muc_doi_toi_da")
    st.caption("Hai con số này vừa được ghi vào prompt, vừa được dùng để kiểm chứng: ràng buộc nói với AI "
               "phải đúng bằng ràng buộc nhóm kiểm tra.")

    ma_list = list(nl["ma"])
    gioi_han = dict(zip(nl["ma"], nl["gioi_han_pct"].astype(float)))
    goc = {m: float(cong_thuc_goc.get(m, 0.0)) for m in ma_list} if dung_mau else dict(percents)

    tab_prompt, tab_kiem = st.tabs(["6a. Soạn prompt", "6b. Kiểm chứng đề xuất của AI"])

    with tab_prompt:
        st.markdown("Prompt tốt có 4 phần: **dữ liệu – mục tiêu – ràng buộc – định dạng đầu ra**. "
                    "App điền sẵn số liệu và ràng buộc để tránh gõ nhầm.")
        mau = VI_DU_PROMPT.get(mua, MAU_TRONG)
        cam_quan = st.text_area("Điểm cảm quan (dán từ Excel)", value=mau["cam_quan"], height=230,
                                key=f"cam_quan_{mua}")
        nhan_xet = st.text_area("Nhận xét chính của người đánh giá", value=mau["nhan_xet"], height=90,
                                key=f"nhan_xet_{mua}")
        muc_tieu = st.text_area("Mục tiêu cải thiện", value=mau["muc_tieu"], height=90, key=f"muc_tieu_{mua}")
        goc_df = nl[["ma", "ten", "tang", "gioi_han_pct"]].copy()
        goc_df["pct"] = [goc[m] for m in ma_list]
        st.code(build_prompt(mua, goc_df, cam_quan, nhan_xet, muc_tieu, so_tp, muc_doi), language=None)
        st.caption("Trước khi gửi: không có tên học sinh, ảnh hay thông tin liên hệ; không có API key; "
                   "số liệu khớp với Excel. Lưu nguyên văn prompt và phản hồi vào prompt_log.md.")

    with tab_kiem:
        st.markdown("Nhập **đủ số liệu AI đưa ra, kể cả dung môi**. App không tự sửa số của AI: "
                    "nếu AI tính tổng sai thì lỗi phải hiện ra. Nếu AI đề xuất nguyên liệu không có trong bảng, "
                    "loại ngay đề xuất đó.")
        nhan_hang = [f"{m} – {t}" for m, t in zip(nl["ma"], nl["ten"])] + [f"{MA_DUNG_MOI} – Dung môi (AI nêu)"]
        bang = pd.DataFrame(index=nhan_hang)
        bang["Giới hạn GV (%)"] = [gioi_han[m] for m in ma_list] + [float("nan")]
        bang["Gốc (%)"] = [goc[m] for m in ma_list] + [100.0 - sum(goc.values())]
        ten_pa = ["P1", "P2", "P3"]
        for pa in ten_pa:
            if dung_mau:
                gia_tri = {m: round(goc[m] + de_xuat_mau.get(pa, {}).get(m, 0.0), 3) for m in ma_list}
                cot = [gia_tri[m] for m in ma_list] + [round(100.0 - sum(gia_tri.values()), 3)]
            else:
                cot = [float("nan")] * (len(ma_list) + 1)
            bang[f"{pa} (%)"] = cot
        cau_hinh = {c: st.column_config.NumberColumn(c, format="%.2f", step=0.1) for c in bang.columns}
        sua = st.data_editor(bang, key=f"bang_ai_{mua}_{int(dung_mau)}", column_config=cau_hinh,
                             disabled=["Giới hạn GV (%)", "Gốc (%)"])

        de_xuat = {}
        for pa in ten_pa:
            cot = sua[f"{pa} (%)"].tolist()
            gia_tri = {m: cot[i] for i, m in enumerate(ma_list)}
            gia_tri[MA_DUNG_MOI] = cot[len(ma_list)]
            de_xuat[pa] = gia_tri
        if dung_mau:        # kiểm tra luôn công thức đang đặt trên thanh trượt (B2) so với gốc B
            de_xuat[COT_THANH_TRUOT] = {**percents, MA_DUNG_MOI: kq["solvent_pct"]}

        ket_qua, thu_tu = {}, list(de_xuat)
        for ten, gia_tri in de_xuat.items():
            trong = all(not _la_so(x) for x in gia_tri.values())
            ket_qua[ten] = None if trong else check_proposal(goc, gia_tri, gioi_han, so_tp, muc_doi)

        mau_hang = next((r for r in ket_qua.values() if r), None)
        if mau_hang is None:
            st.info("Chưa có đề xuất nào. Nhập số liệu AI đưa ra vào các cột P1, P2, P3.")
        else:
            bang_kq = {"Điều kiện": [r["name"] for r in mau_hang["rules"]]}
            for ten in thu_tu:
                kq_pa = ket_qua[ten]
                if kq_pa is None:
                    bang_kq[ten] = ["—"] * len(mau_hang["rules"])
                else:
                    bang_kq[ten] = ["—" if r["ok"] is None else ("✓ " if r["ok"] else "✗ ") + r["detail"]
                                    for r in kq_pa["rules"]]
            st.dataframe(pd.DataFrame(bang_kq), hide_index=True)
            for ten in thu_tu:
                kq_pa = ket_qua[ten]
                if kq_pa is None:
                    continue
                if ten == COT_THANH_TRUOT:      # không phải đề xuất của AI nên không dùng khung đỏ "loại"
                    if kq_pa["passed"]:
                        st.success(f"{ten} so với công thức gốc: đúng các ràng buộc đã đặt cho AI.")
                    else:
                        st.warning(f"{ten} so với công thức gốc: không đạt – {mo_ta_loi(kq_pa)}. "
                                   "Nếu nhóm tự chỉnh thêm ngoài đề xuất của AI, hãy ghi lý do vào nhật ký.")
                elif kq_pa["passed"]:
                    st.success(f"{ten}: đúng cả {len(kq_pa['rules'])} điều kiện toán học – đủ điều kiện để nhóm "
                               "xem xét (chưa phải quyết định chọn).")
                else:
                    st.error(f"{ten}: loại – không đạt: {mo_ta_loi(kq_pa)}.")
            st.caption("Dấu ✓ chỉ cho biết đề xuất đúng ràng buộc toán học. Nhóm vẫn phải đối chiếu với concept và "
                       "dữ liệu cảm quan, xin giáo viên duyệt, rồi mới kiểm chứng bằng thực nghiệm.")


def render_notes(kq, valid, da_duyet):
    with st.expander("7. Quy trình AI được sử dụng trong dự án"):
        st.markdown(
            "1. Cung cấp dữ liệu (công thức, điểm cảm quan, nhận xét) – không gửi dữ liệu cá nhân.\n"
            "2. Nêu mục tiêu cải thiện cụ thể.\n"
            "3. Khóa ràng buộc: nguyên liệu, giới hạn, mức đổi tối đa, tổng 100%, không khẳng định an toàn.\n"
            "4. Yêu cầu đầu ra: tối đa 3 phương án dạng bảng, có lý do dựa trên dữ liệu.\n"
            "5. Kiểm chứng bằng app/Excel → nhóm chọn hoặc bác bỏ và giải thích → giáo viên duyệt → mới pha và thực nghiệm.\n"
            "6. Truyền thông (slogan, giới thiệu): nhóm chọn, sửa và khai báo phần có AI hỗ trợ.\n\n"
            "**AI không tự quyết định công thức cuối cùng.**"
        )
    with st.expander("8. Thông tin để kiểm thử"):
        st.write({
            "Thể tích mặc định": "10 mL",
            "Số dòng bảng công thức": len(kq["df"]),
            "Tổng %": round(kq["total_pct"], 3),
            "Có thể xuất CSV": valid,
            "Nguồn giới hạn nguyên liệu": "GV đã đánh dấu duyệt" if da_duyet else "Mô phỏng – chưa duyệt",
            "Phiên bản": f"Streamlit {st.__version__} | pandas {pd.__version__}",
        })


def main():
    st.set_page_config(page_title=f"{TEN_SAN_PHAM} – Công thức tương tác", page_icon="🍂", layout="wide")
    st.title(f"🍂 {TEN_SAN_PHAM} – Công thức nước hoa tương tác")
    st.caption("Ứng dụng giáo dục STEM (Tổ 3 – mùa thu): kiểm tra công thức, quy đổi thể tích, "
               "kiểm chứng đề xuất của AI và xuất dữ liệu.")
    st.warning("⚠️ Hợp lệ về mặt toán học không đồng nghĩa với an toàn. "
               "Cần giáo viên duyệt an toàn trước khi pha.")

    try:
        bang = doc_bang_nguyen_lieu()
    except LoiBangNguyenLieu as loi:
        st.error(f"Không đọc được bảng nguyên liệu của giáo viên.\n\n{loi}")
        st.stop()

    mua, the_tich, ma_mau = render_sidebar()
    nl = nguyen_lieu_theo_mua(bang, mua)
    if nl.empty:
        st.info(f"Chưa có bảng nguyên liệu do giáo viên cung cấp cho mùa {mua}. "
                f"Giáo viên thêm các dòng có cột mua = {mua} vào file {FILE_NGUYEN_LIEU.name} để dùng mùa này.")
        st.stop()

    da_duyet = bool(nl["da_duyet"].all())
    if da_duyet:
        st.success("Bảng nguyên liệu đã được giáo viên đánh dấu ĐÃ DUYỆT. Ứng dụng vẫn chỉ kiểm tra tính toán.")
    else:
        st.info("**Dữ liệu giới hạn nguyên liệu đang là MÔ PHỎNG, chưa được giáo viên duyệt.** "
                "Không dùng để pha thật. Giáo viên thay bằng bảng đã duyệt trong nguyen_lieu_thu.csv.")

    percents = render_sliders(mua, nl)
    kq = calculate_formula(the_tich, percents, nl)

    render_validation(kq)
    st.subheader("3. Bảng công thức")
    st.dataframe(format_table(kq["df"]), hide_index=True)
    st.caption("mL làm tròn 3 chữ số thập phân khi hiển thị; tổng thể tích tính từ giá trị chưa làm tròn, "
               "nên cộng tay các dòng có thể lệch vài phần nghìn mL (tối đa 0.004 mL).")
    render_profile(mua, kq)
    render_export(kq, ma_mau, the_tich, da_duyet)
    render_ai(mua, nl, percents, kq)
    render_notes(kq, kq["valid"], da_duyet)

    st.divider()
    st.caption("Phạm vi: mô hình giáo dục; đánh giá trên giấy thử; không dùng trên cơ thể; không bán. "
               "Quyết định cuối cùng thuộc nhóm và giáo viên.")


if __name__ == "__main__":
    main()
