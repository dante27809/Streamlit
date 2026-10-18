# -*- coding: utf-8 -*-
"""
Kiểm thử tự động cho app.py – chạy bằng:   python -m unittest -v test_app

Không cần cài pytest. Số ca (Ca 01, Ca 02, …) khớp với bảng trong test_plan.md.

Cách kiểm thử:
  • Hàm tính toán, đọc CSV, soạn prompt, kiểm chứng AI: gọi trực tiếp.
  • Giao diện: dùng FakeSt (một "Streamlit giả" chỉ ghi lại các lệnh app gọi) để chạy hàm main()
    với những giá trị mà thanh trượt thật KHÔNG thể tạo ra (vượt giới hạn, dung môi âm…).
    FakeSt không thay thế việc chạy thật `streamlit run app.py` (xem Ca 18 trong test_plan.md).
  • Nếu máy đã cài Streamlit, lớp TestAppTest chạy thêm app bằng công cụ AppTest chính thức.
"""
import io
import random
import re
import sys
import tempfile
import types
import unicodedata
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pandas as pd

THU_MUC = Path(__file__).resolve().parent
sys.path.insert(0, str(THU_MUC))

try:
    import streamlit  # noqa: F401
    CO_STREAMLIT = True
except ImportError:                       # máy chưa cài Streamlit: tạo module rỗng để import được app.py
    CO_STREAMLIT = False
    sys.modules["streamlit"] = types.ModuleType("streamlit")

import app  # noqa: E402

ST_THAT = app.st


# ---------------------------------------------------------------------
# "Streamlit giả": ghi lại mọi thứ app hiển thị để kiểm tra
# ---------------------------------------------------------------------
class _Khung:
    """Thay cho st.columns / st.tabs / st.expander / st.sidebar: dùng được với `with` và gọi hàm của FakeSt."""
    def __init__(self, st):
        self._st = st

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, ten):
        return getattr(self._st, ten)


class DungLai(Exception):
    """st.stop() trong FakeSt."""


class FakeSt(types.ModuleType):
    def __init__(self, ghi_de=None):
        super().__init__("streamlit")
        self.ghi_de = ghi_de or {}      # {key: giá trị người dùng chọn}; số nguyên với radio = chỉ số lựa chọn
        self.__version__ = "stub"
        self.van_ban = []               # (loại, nội dung) – mọi chữ hiển thị trừ khối code
        self.nut_tai, self.khoi_code, self.bang, self.bieu_do = [], [], [], []
        self.bang_sua, self.thanh_truot = [], []
        self.sidebar = _Khung(self)
        self.column_config = types.SimpleNamespace(NumberColumn=lambda *a, **k: {"a": a, "k": k})

    def _ghi(self, loai, noi_dung):
        self.van_ban.append((loai, str(noi_dung)))

    def van_ban_loai(self, *loai):
        return [t for k, t in self.van_ban if k in loai]

    # ----- hiển thị chữ -----
    def set_page_config(self, **k): pass
    def title(self, t): self._ghi("title", t)
    def header(self, t): self._ghi("header", t)
    def subheader(self, t): self._ghi("subheader", t)
    def caption(self, t, **k): self._ghi("caption", t)
    def markdown(self, t, **k): self._ghi("markdown", t)
    def write(self, x): self._ghi("write", x)
    def warning(self, t, **k): self._ghi("warning", t)
    def error(self, t, **k): self._ghi("error", t)
    def info(self, t, **k): self._ghi("info", t)
    def success(self, t, **k): self._ghi("success", t)
    def metric(self, label, value, **k): self._ghi("metric", f"{label}: {value}")
    def divider(self): pass

    def stop(self):
        raise DungLai()

    # ----- ô nhập -----
    def selectbox(self, label, options, index=0, key=None, **k):
        return self.ghi_de.get(key, options[index])

    def number_input(self, label, min_value=None, max_value=None, value=None, step=None, key=None, **k):
        return self.ghi_de.get(key, value)

    def text_input(self, label, value="", key=None, **k):
        return self.ghi_de.get(key, value)

    def text_area(self, label, value="", key=None, **k):
        return self.ghi_de.get(key, value)

    def checkbox(self, label, value=False, key=None, **k):
        return self.ghi_de.get(key, value)

    def radio(self, label, options, index=0, key=None, **k):
        chon = self.ghi_de.get(key, index)
        return options[chon] if isinstance(chon, int) else chon

    def slider(self, label, min_value=0.0, max_value=1.0, value=0.0, step=None, key=None, **k):
        self.thanh_truot.append({"label": label, "min": min_value, "max": max_value, "value": value, "key": key})
        return self.ghi_de.get(key, value)

    # ----- bố cục và bảng -----
    def columns(self, n):
        return [_Khung(self) for _ in range(n if isinstance(n, int) else len(n))]

    def tabs(self, nhan):
        return [_Khung(self) for _ in nhan]

    def expander(self, nhan, **k):
        self._ghi("expander", nhan)
        return _Khung(self)

    def dataframe(self, df, **k): self.bang.append(df)
    def bar_chart(self, df, **k): self.bieu_do.append((df, k))
    def code(self, noi_dung, language=None, **k): self.khoi_code.append(noi_dung)

    def download_button(self, label, data=None, file_name=None, mime=None, **k):
        self.nut_tai.append({"label": label, "data": data, "file_name": file_name, "mime": mime})

    def data_editor(self, df, key=None, **k):
        self.bang_sua.append({"df": df, "key": key})
        sua = self.ghi_de.get(key)
        return sua(df.copy()) if callable(sua) else df


def chay_app(ghi_de=None, bang_nguyen_lieu=None):
    """Chạy app.main() với FakeSt. bang_nguyen_lieu: thay bảng GV bằng DataFrame hoặc một lỗi để thử."""
    fake = FakeSt(ghi_de)
    app.st = fake
    try:
        if bang_nguyen_lieu is None:
            app.main()
        elif isinstance(bang_nguyen_lieu, Exception):
            with mock.patch.object(app, "doc_bang_nguyen_lieu", side_effect=bang_nguyen_lieu):
                app.main()
        else:
            with mock.patch.object(app, "doc_bang_nguyen_lieu", return_value=bang_nguyen_lieu):
                app.main()
    except DungLai:
        pass
    finally:
        app.st = ST_THAT
    return fake


def loi_cong_thuc(fake):
    """Các khung đỏ ở phần 1–5 (lỗi công thức). Phần 6 có thể có 'P3: loại' – đó là kết luận về đề xuất AI."""
    ket_qua = []
    for loai, noi_dung in fake.van_ban:
        if loai == "subheader" and noi_dung.startswith("6."):
            break
        if loai == "error":
            ket_qua.append(noi_dung)
    return ket_qua


MA_THU = ("SW", "BG", "LV", "GE", "CE", "SA", "VA")


def khoa(ma, mua="Thu"):
    """Khóa thanh trượt của nguyên liệu `ma` theo bảng GV hiện tại."""
    gh = dict(zip(nguyen_lieu_thu()["ma"], nguyen_lieu_thu()["gioi_han_pct"]))
    return app.khoa_thanh_truot(mua, ma, gh[ma])


def tat_ca_slider(gia_tri):
    """Ghi đè cả 7 thanh trượt mùa thu bằng một giá trị."""
    return {khoa(m): gia_tri for m in MA_THU}


def bang_gv():
    return app.doc_bang_nguyen_lieu()


def nguyen_lieu_thu():
    return app.nguyen_lieu_theo_mua(bang_gv(), "Thu")


def b2():
    return dict(app.CONG_THUC_NHOM["Thu"]["B2"])


# =====================================================================
class TestCa01CongThucMacDinh(unittest.TestCase):
    """Ca 01: giá trị mặc định B2, 10 mL."""

    def test_bang_8_dong_tong_100_va_tong_ml_bang_the_tich(self):
        kq = app.calculate_formula(10.0, b2(), nguyen_lieu_thu())
        self.assertEqual(len(kq["df"]), 8)                       # 7 nguyên liệu + dung môi
        self.assertTrue(kq["valid"])
        self.assertAlmostEqual(kq["total_pct"], 100.0, places=9)
        self.assertAlmostEqual(kq["total_ml"], 10.0, places=9)
        self.assertAlmostEqual(kq["fragrance_pct"], 14.4, places=9)
        self.assertAlmostEqual(kq["solvent_pct"], 85.6, places=9)

    def test_ml_tung_dong_dung_theo_cong_thuc(self):
        kq = app.calculate_formula(10.0, b2(), nguyen_lieu_thu())
        ml = dict(zip(kq["df"]["Mã"], kq["df"]["Thể tích (mL)"]))
        for ma, mong_doi in {"SW": 0.21, "BG": 0.17, "LV": 0.24, "GE": 0.32, "CE": 0.25,
                             "SA": 0.20, "VA": 0.05, "SO": 8.56}.items():
            self.assertAlmostEqual(ml[ma], mong_doi, places=9, msg=ma)

    def test_giao_dien_mac_dinh_hop_le_va_co_nut_tai_csv(self):
        fake = chay_app()
        self.assertEqual(loi_cong_thuc(fake), [])
        self.assertEqual(len(fake.thanh_truot), 7)
        self.assertTrue(any("hợp lệ về mặt tính toán" in t and "gửi giáo viên xem xét" in t
                            for t in fake.van_ban_loai("success")))
        self.assertEqual(len(fake.nut_tai), 1)
        self.assertEqual(fake.nut_tai[0]["file_name"], "THU-B2_10mL.csv")
        mac_dinh = {s["key"]: s["value"] for s in fake.thanh_truot}
        for ma, gia_tri in b2().items():
            self.assertEqual(mac_dinh[khoa(ma)], gia_tri)

    def test_gia_tri_mac_dinh_cua_nhom_nam_trong_gioi_han(self):
        gh = dict(zip(nguyen_lieu_thu()["ma"], nguyen_lieu_thu()["gioi_han_pct"]))
        for ten in ("B", "B2"):
            for ma, gia_tri in app.CONG_THUC_NHOM["Thu"][ten].items():
                self.assertLessEqual(gia_tri, gh[ma], f"{ten}:{ma}")


class TestCa02Ca03TheTich(unittest.TestCase):
    """Ca 02 và 03: đổi thể tích mẻ."""

    def setUp(self):
        self.ml10 = app.calculate_formula(10.0, b2(), nguyen_lieu_thu())["df"]["Thể tích (mL)"]

    def test_5_ml_bang_mot_nua(self):
        ml = app.calculate_formula(5.0, b2(), nguyen_lieu_thu())["df"]["Thể tích (mL)"]
        for a, b in zip(ml, self.ml10):
            self.assertAlmostEqual(a, b / 2, places=9)

    def test_20_ml_gap_doi(self):
        ml = app.calculate_formula(20.0, b2(), nguyen_lieu_thu())["df"]["Thể tích (mL)"]
        for a, b in zip(ml, self.ml10):
            self.assertAlmostEqual(a, b * 2, places=9)

    def test_giao_dien_hien_tong_the_tich_dung(self):
        for v in (5.0, 20.0):
            fake = chay_app({"the_tich": v})
            self.assertIn(f"Tổng thể tích: {v:.3f} mL", fake.van_ban_loai("metric"))

    def test_the_tich_khong_hop_le_bi_bao_loi(self):
        for v in (0, -5, float("nan"), None):
            kq = app.calculate_formula(v, b2(), nguyen_lieu_thu())
            self.assertFalse(kq["valid"], v)


class TestCa04TatCaBangKhong(unittest.TestCase):
    """Ca 04: tất cả thành phần hương = 0."""

    def test_dung_moi_100_hop_le(self):
        kq = app.calculate_formula(10.0, {m: 0.0 for m in b2()}, nguyen_lieu_thu())
        self.assertTrue(kq["valid"])
        self.assertEqual(kq["solvent_pct"], 100.0)
        self.assertAlmostEqual(kq["total_ml"], 10.0, places=9)

    def test_mo_ta_noi_chua_co_huong(self):     # lỗi của bản mẫu: báo "thiên về tầng Cuối (0.00%)"
        kq = app.calculate_formula(10.0, {m: 0.0 for m in b2()}, nguyen_lieu_thu())
        self.assertEqual(app.dominant_tier_description(kq["df"]), "Chưa có thành phần hương để tạo mô tả.")
        self.assertEqual(app.tier_shares(kq["df"]), {})

    def test_giao_dien_van_co_canh_bao_giao_vien(self):
        fake = chay_app(tat_ca_slider(0.0))
        self.assertEqual(loi_cong_thuc(fake), [])
        self.assertTrue(any("không đồng nghĩa với an toàn" in t for t in fake.van_ban_loai("warning")))
        self.assertTrue(any("Chưa có thành phần hương" in t for t in fake.van_ban_loai("write")))
        self.assertEqual(fake.bieu_do, [])       # không vẽ biểu đồ khi chưa có hương


class TestCa05DungGioiHan(unittest.TestCase):
    """Ca 05: thành phần đúng bằng giới hạn max."""

    def test_dung_gioi_han_khong_bao_vuot(self):
        nl = nguyen_lieu_thu()
        tai_max = dict(zip(nl["ma"], nl["gioi_han_pct"]))
        kq = app.calculate_formula(10.0, tai_max, nl)
        self.assertTrue(kq["valid"], kq["errors"])
        self.assertNotIn("Vượt giới hạn", set(kq["df"]["Kiểm tra"]))

    def test_nhieu_so_thuc_sat_gioi_han_khong_bi_bao_nham(self):
        # Cộng dồn từng bước 0.1 cho ra 3.0000000000000013 chứ không phải 3.0: lớn hơn giới hạn một chút do số thực.
        nl = nguyen_lieu_thu()
        co_nhieu = 0
        for ma, gh in zip(nl["ma"], nl["gioi_han_pct"]):
            x = 0.0
            for _ in range(round(gh * 10)):
                x += 0.1
            co_nhieu += x > gh                                    # phép thử phải thật sự có giá trị > giới hạn
            kq = app.calculate_formula(10, {**{m: 0.0 for m in nl["ma"]}, ma: x}, nl)
            self.assertTrue(kq["valid"], (ma, x, kq["errors"]))
        self.assertGreaterEqual(co_nhieu, 3)

    def test_giao_dien_keo_het_co(self):
        fake = chay_app({khoa(m): g for m, g in zip(MA_THU, (3.0, 2.0, 4.0, 4.0, 3.5, 2.5, 1.0))})
        self.assertEqual(loi_cong_thuc(fake), [])
        self.assertEqual(len(fake.nut_tai), 1)


class TestCa06Ca07LoiToanHoc(unittest.TestCase):
    """Ca 06 và 07: thanh trượt thật không thể vượt max nên phải thử bằng hàm và giao diện giả."""

    def test_vuot_gioi_han_bao_loi(self):
        x = b2()
        x["VA"] = 1.5
        kq = app.calculate_formula(10.0, x, nguyen_lieu_thu())
        self.assertFalse(kq["valid"])
        self.assertTrue(any("Vanilla accord" in e and "vượt giới hạn" in e for e in kq["errors"]))
        self.assertIn("Vượt giới hạn", set(kq["df"]["Kiểm tra"]))

    def test_gia_tri_am_bao_loi(self):
        x = b2()
        x["SW"] = -0.5
        kq = app.calculate_formula(10.0, x, nguyen_lieu_thu())
        self.assertFalse(kq["valid"])
        self.assertTrue(any("số âm" in e for e in kq["errors"]))

    def test_thieu_gia_tri_bao_loi(self):
        x = b2()
        del x["GE"]
        self.assertFalse(app.calculate_formula(10.0, x, nguyen_lieu_thu())["valid"])

    def test_tong_huong_tren_100_dung_moi_am(self):
        nl = nguyen_lieu_thu()
        # nâng giới hạn để có thể nhập tổng > 100% (bảng thật không cho phép điều này qua thanh trượt)
        nl = nl.assign(gioi_han_pct=100.0)
        x = {m: 20.0 for m in nl["ma"]}                        # 7 × 20 = 140%
        kq = app.calculate_formula(10.0, x, nl)
        self.assertFalse(kq["valid"])
        self.assertAlmostEqual(kq["solvent_pct"], -40.0, places=9)
        self.assertEqual(sum("Dung môi âm" in e for e in kq["errors"]), 1)     # chỉ báo một lần
        self.assertEqual(kq["df"].iloc[-1]["Kiểm tra"], "Âm")

    def test_giao_dien_vuot_gioi_han_khong_co_nut_tai(self):
        fake = chay_app({khoa("VA"): 1.5})
        self.assertTrue(any("vượt giới hạn dự án" in t for t in loi_cong_thuc(fake)))
        self.assertEqual(fake.nut_tai, [])
        self.assertIn("Trạng thái (tính toán): Chưa hợp lệ", fake.van_ban_loai("metric"))

    def test_giao_dien_dung_moi_am_khong_co_nut_tai(self):
        fake = chay_app(tat_ca_slider(60.0))
        self.assertTrue(any("Dung môi âm" in t for t in loi_cong_thuc(fake)))
        self.assertEqual(fake.nut_tai, [])
        self.assertTrue(any("không đồng nghĩa với an toàn" in t for t in fake.van_ban_loai("warning")))


class TestCa08XuatCsv(unittest.TestCase):
    def setUp(self):
        self.kq = app.calculate_formula(10.0, b2(), nguyen_lieu_thu())
        self.du_lieu = app.build_csv(self.kq, "THU-B2", 10.0, da_duyet=False)
        self.csv = pd.read_csv(io.BytesIO(self.du_lieu), encoding="utf-8-sig")

    def test_utf8_co_bom_va_giu_tieng_viet(self):
        self.assertTrue(self.du_lieu.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Cuối", set(self.csv["Tầng hương"]))
        self.assertIn("Cam ngọt (Sweet orange)", set(self.csv["Nguyên liệu"]))

    def test_cot_khop_sheet_cong_thuc_trong_excel(self):
        self.assertEqual(list(self.csv.columns), [
            "Mã mẫu", "Mã", "Nguyên liệu", "Tầng hương", "Tỉ lệ (%)", "Giới hạn GV (%)", "Thể tích mẻ (mL)",
            "Thể tích thành phần (mL)", "Kiểm tra thành phần", "Nguồn giới hạn", "Trạng thái"])

    def test_tong_ml_bang_the_tich_va_tong_phan_tram_100(self):
        self.assertEqual(len(self.csv), 8)
        self.assertAlmostEqual(self.csv["Thể tích thành phần (mL)"].sum(), 10.0, places=6)
        self.assertAlmostEqual(self.csv["Tỉ lệ (%)"].sum(), 100.0, places=6)
        self.assertTrue((self.csv["Mã mẫu"] == "THU-B2").all())

    def test_csv_ghi_ro_chua_duyet_an_toan_va_nguon_mo_phong(self):
        self.assertEqual(set(self.csv["Trạng thái"]), {"Chưa GV duyệt an toàn"})
        self.assertEqual(set(self.csv["Nguồn giới hạn"]), {"Mô phỏng – chưa duyệt"})
        duyet = app.build_csv(self.kq, "THU-B2", 10.0, da_duyet=True)
        self.assertIn("GV đã đánh dấu duyệt", duyet.decode("utf-8-sig"))
        self.assertIn("Chưa GV duyệt an toàn", duyet.decode("utf-8-sig"))     # vẫn chưa nói là an toàn

    def test_the_tich_le_van_dung_trong_sai_so_lam_tron(self):
        for v in (1.5, 7.5, 12.5, 19.5):
            kq = app.calculate_formula(v, b2(), nguyen_lieu_thu())
            csv = pd.read_csv(io.BytesIO(app.build_csv(kq, "X", v, False)), encoding="utf-8-sig")
            self.assertAlmostEqual(csv["Thể tích thành phần (mL)"].sum(), v, delta=0.004, msg=str(v))
            self.assertAlmostEqual(kq["total_ml"], v, places=9)             # tổng chưa làm tròn đúng tuyệt đối

    def test_ten_file(self):
        self.assertEqual(app.ten_file_csv("THU-B2", 10.0), "THU-B2_10mL.csv")
        self.assertEqual(app.ten_file_csv("Thu Vàng #1", 7.5), "Thu_Vang_1_7.5mL.csv")
        self.assertEqual(app.ten_file_csv("  ", 5.0), "cong_thuc_5mL.csv")

    def test_giao_dien_ma_mau_trong_khong_co_nut_tai(self):
        fake = chay_app({"ma_mau": "   "})
        self.assertEqual(fake.nut_tai, [])
        self.assertTrue(any("mã mẫu" in t for t in fake.van_ban_loai("info")))


class TestCa09DoiMua(unittest.TestCase):
    def test_concept_doi_theo_mua(self):
        fake = chay_app({"mua": "Thu"})
        self.assertTrue(any("Dịu, ấm, trầm nhẹ" in t and "Fruity – Floral – Woody" in t
                            for t in fake.van_ban_loai("info")))

    def test_mua_chua_co_du_lieu_gv_thong_bao_va_khong_co_thanh_truot(self):
        for mua, concept in (("Xuân", "Tươi mới, trong trẻo"), ("Hạ", "Mát, sáng"), ("Đông", "Ấm áp, sâu")):
            fake = chay_app({"mua": mua})
            self.assertEqual(fake.thanh_truot, [], mua)
            self.assertTrue(any(f"mùa {mua}" in t and "Chưa có bảng nguyên liệu" in t
                                for t in fake.van_ban_loai("info")), mua)
            self.assertTrue(any(concept in t for t in fake.van_ban_loai("info")), mua)
            self.assertTrue(any("không đồng nghĩa với an toàn" in t for t in fake.van_ban_loai("warning")), mua)


class TestCa10MoTa(unittest.TestCase):
    def mo_ta(self, x):
        return app.dominant_tier_description(app.calculate_formula(10.0, x, nguyen_lieu_thu())["df"])

    def test_thien_ve_tang_dau(self):
        x = {m: 0.0 for m in b2()}
        x.update(SW=3.0, BG=2.0, LV=0.5)
        self.assertIn("thiên về tầng Đầu", self.mo_ta(x))

    def test_thien_ve_tang_cuoi(self):
        x = {m: 0.0 for m in b2()}
        x.update(CE=3.0, SA=2.0, GE=0.5)
        self.assertIn("thiên về tầng Cuối", self.mo_ta(x))

    def test_b2_can_bang_giua_va_cuoi(self):
        mo_ta = self.mo_ta(b2())
        self.assertIn("cân bằng giữa tầng Giữa", mo_ta)
        self.assertIn("tầng Cuối", mo_ta)

    def test_dung_o_nguong_5_diem_khong_con_la_can_bang(self):
        # Công thức B có tầng 25/40/35: Giữa hơn Cuối đúng 5.0 điểm → "thiên về", không bị nhiễu số thực
        self.assertIn("thiên về tầng Giữa", self.mo_ta(app.CONG_THUC_NHOM["Thu"]["B"]))

    def test_ty_le_tang_tinh_tren_hon_hop_huong(self):
        kq = app.calculate_formula(10.0, app.CONG_THUC_NHOM["Thu"]["B"], nguyen_lieu_thu())
        s = app.tier_shares(kq["df"])
        self.assertAlmostEqual(s["Đầu"], 25.0, places=9)
        self.assertAlmostEqual(s["Giữa"], 40.0, places=9)
        self.assertAlmostEqual(s["Cuối"], 35.0, places=9)
        self.assertAlmostEqual(sum(s.values()), 100.0, places=9)

    def test_so_phan_tren_100_phan_huong(self):
        df = app.calculate_formula(10.0, b2(), nguyen_lieu_thu())["df"]
        phan = dict(zip(df["Mã"], df["Số phần / 100 phần hương"]))
        self.assertAlmostEqual(sum(v for k, v in phan.items() if k != "SO"), 100.0, places=9)
        self.assertAlmostEqual(phan["SW"], 2.1 / 14.4 * 100, places=9)
        self.assertTrue(pd.isna(phan["SO"]))

    def test_bieu_do_giu_dung_thu_tu_tang_va_tuy_chon_so_sanh(self):
        fake = chay_app()
        df, _ = fake.bieu_do[0]
        self.assertEqual(list(df.index), ["1. Đầu", "2. Giữa", "3. Cuối"])
        self.assertEqual(df.shape[1], 1)
        fake = chay_app({"so_sanh": True})
        df, _ = fake.bieu_do[0]
        self.assertEqual(df.shape[1], 2)
        self.assertEqual(list(df["Định hướng của mùa (tham khảo)"]), [25.0, 40.0, 35.0])


# =====================================================================
def ghi_csv(thu_muc, noi_dung, ma_hoa="utf-8-sig", ten="nl.csv"):
    p = Path(thu_muc) / ten
    data = noi_dung if isinstance(noi_dung, bytes) else noi_dung.encode(ma_hoa)
    p.write_bytes(data)
    return p


def sang_cp1258(text):
    """Mô phỏng cách Excel tiếng Việt đời cũ lưu 'CSV': dấu thanh tách rời, chữ có mũ/móc giữ nguyên."""
    out = bytearray()
    for ch in unicodedata.normalize("NFC", text):
        try:
            out += ch.encode("cp1258")
            continue
        except UnicodeEncodeError:
            pass
        seq = unicodedata.normalize("NFD", ch)
        cur, i = seq[0], 1
        while i < len(seq):
            ghep = unicodedata.normalize("NFC", cur + seq[i])
            try:
                ghep.encode("cp1258")
            except UnicodeEncodeError:
                break
            cur, i = ghep, i + 1
        out += cur.encode("cp1258")
        for dau in seq[i:]:
            out += dau.encode("cp1258")
    return bytes(out)


TIEU_DE = "ma,mua,ten,tang,vai_tro,gioi_han_pct,trang_thai\n"


class TestCa11BangGvSai(unittest.TestCase):
    """Ca 11: file của giáo viên sai → thông báo cụ thể, không sập."""

    def doc_loi(self, noi_dung):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(app.LoiBangNguyenLieu) as cm:
                app.doc_bang_nguyen_lieu(ghi_csv(d, noi_dung))
        return str(cm.exception)

    def test_thieu_file(self):
        with self.assertRaises(app.LoiBangNguyenLieu) as cm:
            app.doc_bang_nguyen_lieu(THU_MUC / "khong_ton_tai.csv")
        self.assertIn("Không tìm thấy file", str(cm.exception))

    def test_thieu_cot(self):
        loi = self.doc_loi("ma,mua,ten,tang\nSW,Thu,Cam,Đầu\n")
        self.assertIn("Thiếu cột", loi)
        self.assertIn("gioi_han_pct", loi)

    def test_chi_co_tieu_de(self):
        self.assertIn("không có dòng dữ liệu", self.doc_loi(TIEU_DE))

    def test_gioi_han_khong_phai_so_hoac_am(self):
        loi = self.doc_loi(TIEU_DE + "SW,Thu,Cam,Đầu,x,abc,\nLV,Thu,Lav,Giữa,x,-1,\nCE,Thu,Ced,Cuối,x,,\n")
        self.assertEqual(loi.count("phải là số không âm"), 3)      # báo đủ cả ba dòng trong một lần

    def test_gioi_han_vo_cuc_hoac_nan_bi_tu_choi(self):
        self.assertIn("phải là số không âm", self.doc_loi(TIEU_DE + "SW,Thu,Cam,Đầu,x,inf,\n"))
        self.assertIn("phải là số không âm", self.doc_loi(TIEU_DE + "SW,Thu,Cam,Đầu,x,nan,\n"))

    def test_tang_hoac_mua_khong_hop_le(self):
        loi = self.doc_loi(TIEU_DE + "SW,Mùa lạ,Cam,Đỉnh,x,3,\n")
        self.assertIn("mùa 'Mùa lạ' không hợp lệ", loi)
        self.assertIn("tầng 'Đỉnh' không hợp lệ", loi)

    def test_ma_trung_va_ma_so_danh_rieng(self):
        self.assertIn("bị trùng", self.doc_loi(TIEU_DE + "SW,Thu,A,Đầu,x,3,\nSW,Thu,B,Giữa,x,2,\n"))
        self.assertIn("dành riêng cho dung môi", self.doc_loi(TIEU_DE + "SO,Thu,A,Đầu,x,3,\n"))

    def test_cung_ma_o_hai_mua_khac_nhau_la_hop_le(self):
        with tempfile.TemporaryDirectory() as d:
            df = app.doc_bang_nguyen_lieu(ghi_csv(d, TIEU_DE + "LV,Xuân,Lav,Giữa,x,4,\nLV,Thu,Lav,Giữa,x,4,\n"))
        self.assertEqual(len(df), 2)

    def test_giao_dien_bao_loi_ro_rang_va_khong_sap(self):
        fake = chay_app(bang_nguyen_lieu=app.LoiBangNguyenLieu("- Dòng dữ liệu 3 (SW): giới hạn 'abc' phải là số."))
        self.assertTrue(any("Không đọc được bảng nguyên liệu" in t and "Dòng dữ liệu 3" in t
                            for t in fake.van_ban_loai("error")))
        self.assertEqual(fake.thanh_truot, [])
        self.assertEqual(fake.nut_tai, [])
        self.assertTrue(any("không đồng nghĩa với an toàn" in t for t in fake.van_ban_loai("warning")))


class TestCa12DinhDangExcelVietNam(unittest.TestCase):
    """Ca 12: file lưu từ Excel tiếng Việt (dấu ';', số thập phân dấu phẩy, mã hóa cũ)."""

    def doc(self, noi_dung, ma_hoa="utf-8-sig"):
        with tempfile.TemporaryDirectory() as d:
            return app.doc_bang_nguyen_lieu(ghi_csv(d, noi_dung, ma_hoa))

    def test_dau_cham_phay_va_so_thap_phan_dau_phay(self):
        df = self.doc("ma;mua;ten;tang;vai_tro;gioi_han_pct;trang_thai\n"
                      "SW;Thu;Cam ngọt;Đầu;Ngọt dịu;3,0;ĐÃ DUYỆT\nGE;Thu;Geranium;Giữa;Hoa xanh;2,75;ĐÃ DUYỆT\n")
        self.assertEqual(list(df["gioi_han_pct"]), [3.0, 2.75])
        self.assertTrue(df["da_duyet"].all())

    def test_ma_hoa_cp1258(self):
        text = (TIEU_DE + "SW,Thu,Cam ngọt,Đầu,Ngọt dịu - trái cây chín,3.0,MÔ PHỎNG\n"
                          "LV,Thu,Lavender,Giữa,Hoa cỏ sạch,4.0,MÔ PHỎNG\nCE,Thu,Cedarwood,Cuối,Gỗ khô ấm,3.5,MÔ PHỎNG\n")
        du_lieu = sang_cp1258(text)
        with self.assertRaises(UnicodeDecodeError):
            du_lieu.decode("utf-8")                                   # đúng là không đọc được bằng UTF-8
        df = self.doc(du_lieu)
        self.assertEqual(list(df["tang"]), ["Đầu", "Giữa", "Cuối"])
        self.assertEqual(list(df["gioi_han_pct"]), [3.0, 4.0, 3.5])

    def test_ten_tang_va_mua_khong_dau_cung_duoc(self):
        df = self.doc(TIEU_DE + "SW,thu,Cam,dau,x,3,\nLV,THU,Lav,GIUA,x,4,\nCE,Thu,Ced,cuoi,x,3,\n")
        self.assertEqual(list(df["tang"]), ["Đầu", "Giữa", "Cuối"])
        self.assertEqual(set(df["mua"]), {"Thu"})

    def test_tieu_de_co_dau_cach_hoac_viet_hoa_va_cot_thua(self):
        df = self.doc("Ma , MUA , Ten , Tang , Vai tro , Gioi han pct , Nha cung cap\n"
                      "SW,Thu,Cam,Đầu,x,3,Công ty A\n")
        self.assertEqual(list(df["ma"]), ["SW"])
        self.assertFalse(df["da_duyet"].any())                         # không có cột trang_thai → coi là chưa duyệt

    def test_bo_qua_dong_trong(self):
        df = self.doc(TIEU_DE + "SW,Thu,Cam,Đầu,x,3,\n,,,,,,\n\nLV,Thu,Lav,Giữa,x,4,\n")
        self.assertEqual(list(df["ma"]), ["SW", "LV"])


class TestCa13NhanDuLieuVaGioiHanThayDoi(unittest.TestCase):
    def test_chi_dung_chu_da_duyet_moi_duoc_coi_la_da_duyet(self):
        with tempfile.TemporaryDirectory() as d:
            for gia_tri, mong_doi in (("ĐÃ DUYỆT", True), ("đã duyệt", True), ("DA_DUYET", True),
                                      ("MÔ PHỎNG (chưa duyệt)", False), ("CHƯA DUYỆT", False),
                                      ("duyệt", False), ("", False)):
                df = app.doc_bang_nguyen_lieu(ghi_csv(d, TIEU_DE + f"SW,Thu,Cam,Đầu,x,3,{gia_tri}\n"))
                self.assertEqual(bool(df["da_duyet"].iloc[0]), mong_doi, gia_tri)

    def test_bang_that_dang_la_mo_phong(self):
        self.assertFalse(bang_gv()["da_duyet"].any())
        fake = chay_app()
        self.assertTrue(any("MÔ PHỎNG" in t and "chưa được giáo viên duyệt" in t for t in fake.van_ban_loai("info")))
        self.assertFalse(any("ĐÃ DUYỆT" in t for t in fake.van_ban_loai("success")))

    def test_khi_gv_danh_dau_da_duyet_nhan_doi_nhung_van_khong_noi_la_an_toan(self):
        bang = bang_gv().assign(trang_thai="ĐÃ DUYỆT", da_duyet=True)
        fake = chay_app(bang_nguyen_lieu=bang)
        self.assertTrue(any("ĐÃ DUYỆT" in t for t in fake.van_ban_loai("success")))
        self.assertFalse(any("MÔ PHỎNG" in t for t in fake.van_ban_loai("info")))
        self.assertIn("GV đã đánh dấu duyệt", fake.nut_tai[0]["data"].decode("utf-8-sig"))
        self.assertIn("Chưa GV duyệt an toàn", fake.nut_tai[0]["data"].decode("utf-8-sig"))

    def test_gv_ha_gioi_han_thap_hon_mac_dinh_app_khong_sap(self):
        bang = bang_gv()
        bang.loc[bang["ma"] == "BG", "gioi_han_pct"] = 1.5            # mặc định B2 của BG là 1.7
        fake = chay_app(bang_nguyen_lieu=bang)
        bg = next(s for s in fake.thanh_truot if s["key"].startswith("slider_Thu_BG_"))
        self.assertEqual((bg["max"], bg["value"]), (1.5, 1.5))
        self.assertTrue(any("vượt giới hạn 1.5%" in t for t in fake.van_ban_loai("info")))
        self.assertEqual(loi_cong_thuc(fake), [])

    def test_doi_gioi_han_thi_khoa_thanh_truot_doi_theo(self):
        self.assertNotEqual(app.khoa_thanh_truot("Thu", "BG", 2.0), app.khoa_thanh_truot("Thu", "BG", 1.5))
        self.assertNotIn(".", app.khoa_thanh_truot("Thu", "CE", 3.5))

    def test_gv_dat_gioi_han_0_khong_tao_thanh_truot(self):
        bang = bang_gv()
        bang.loc[bang["ma"] == "CE", "gioi_han_pct"] = 0.0
        fake = chay_app(bang_nguyen_lieu=bang)
        self.assertEqual(len(fake.thanh_truot), 6)
        self.assertFalse([s for s in fake.thanh_truot if s["key"].startswith("slider_Thu_CE_")])
        self.assertTrue(any("giới hạn 0%" in t for t in fake.van_ban_loai("caption")))
        self.assertEqual(loi_cong_thuc(fake), [])


# =====================================================================
class TestCa14KiemChungDeXuatAI(unittest.TestCase):
    def setUp(self):
        nl = nguyen_lieu_thu()
        self.ma = list(nl["ma"])
        self.gh = dict(zip(nl["ma"], nl["gioi_han_pct"]))
        self.B = dict(app.CONG_THUC_NHOM["Thu"]["B"])

    def de_xuat(self, delta):
        v = {m: round(self.B[m] + delta.get(m, 0.0), 3) for m in self.ma}
        v["SO"] = round(100.0 - sum(v[m] for m in self.ma), 3)
        return v

    def kiem(self, delta=None, **ghi_de):
        v = self.de_xuat(delta or {})
        v.update(ghi_de)
        return app.check_proposal(self.B, v, self.gh, 3, 0.5)

    def test_p1_dat_ca_7_dieu_kien(self):
        kq = self.kiem(app.DE_XUAT_AI_MAU["Thu"]["P1"])
        self.assertTrue(kq["passed"], kq["failed"])
        self.assertEqual(len(kq["rules"]), 7)

    def test_p2_dat_dung_o_bien_pm_0_5_du_so_thuc_nhieu(self):
        kq = self.kiem(app.DE_XUAT_AI_MAU["Thu"]["P2"])
        self.assertTrue(kq["passed"], kq["failed"])
        self.assertAlmostEqual(abs(kq["delta"]["SW"]), 0.5, places=6)

    def test_p3_bi_loai_vi_vanilla_vuot_gioi_han(self):
        kq = self.kiem(app.DE_XUAT_AI_MAU["Thu"]["P3"])
        self.assertFalse(kq["passed"])
        self.assertEqual(kq["failed"], ["Trong giới hạn dự án"])
        chi_tiet = next(r["detail"] for r in kq["rules"] if r["name"] == "Trong giới hạn dự án")
        self.assertEqual(chi_tiet, "VA 1.20% > 1.00%")

    def test_b2_dang_dat_tren_thanh_truot_chinh_la_p1(self):
        self.assertEqual({m: round(v + 0.0, 3) for m, v in app.CONG_THUC_NHOM["Thu"]["B2"].items()},
                         {m: self.de_xuat(app.DE_XUAT_AI_MAU["Thu"]["P1"])[m] for m in self.ma})

    def test_doi_4_thanh_phan_bi_loai(self):
        kq = self.kiem({"SW": 0.1, "BG": 0.1, "LV": 0.1, "GE": 0.1})
        self.assertIn("Đổi tối đa 3 thành phần", kq["failed"])

    def test_doi_qua_0_5_diem_bi_loai(self):
        kq = self.kiem({"LV": 0.6})
        self.assertIn("Mỗi thành phần đổi ≤ ±0.5 điểm %", kq["failed"])

    def test_ai_tinh_tong_sai_phai_hien_ra_va_app_khong_tu_sua(self):
        v = self.de_xuat({"BG": 0.3})
        v["SO"] = 86.0                                              # AI quên bù dung môi: tổng = 100.3%
        kq = app.check_proposal(self.B, v, self.gh, 3, 0.5)
        self.assertEqual(kq["failed"], ["Tổng kể cả dung môi = 100%"])
        chi_tiet = next(r["detail"] for r in kq["rules"] if r["name"].startswith("Tổng"))
        self.assertEqual(chi_tiet, "tổng 100.30%")

    def test_dung_moi_am_bi_loai(self):
        kq = self.kiem(SO=-1.0)
        self.assertIn("Dung môi không âm", kq["failed"])

    def test_so_am_bi_loai(self):
        kq = self.kiem(VA=-0.2)
        self.assertIn("Không có số âm", kq["failed"])

    def test_thieu_so_lieu_bi_loai_va_khong_kiem_cac_dieu_kien_con_lai(self):
        v = self.de_xuat({})
        v["GE"] = None
        v["SO"] = float("nan")
        kq = app.check_proposal(self.B, v, self.gh)
        self.assertFalse(kq["passed"])
        self.assertEqual(kq["rules"][0]["detail"], "thiếu: GE, SO")
        self.assertTrue(all(r["ok"] is None for r in kq["rules"][1:]))

    def test_ap_dung_dung_tham_so_nhom_dat(self):
        v = self.de_xuat({"LV": 0.9})
        self.assertFalse(app.check_proposal(self.B, v, self.gh, 3, 0.5)["passed"])
        self.assertTrue(app.check_proposal(self.B, v, self.gh, 3, 1.0)["passed"])        # nhóm cho phép ±1.0
        v = self.de_xuat({"SW": 0.1, "BG": 0.1})
        self.assertTrue(app.check_proposal(self.B, v, self.gh, 2, 0.5)["passed"])
        self.assertFalse(app.check_proposal(self.B, self.de_xuat({"SW": 0.1, "BG": 0.1, "LV": 0.1}),
                                            self.gh, 2, 0.5)["passed"])

    def test_giao_dien_mau_p1_p2_dat_p3_bi_loai_va_kiem_ca_thanh_truot(self):
        fake = chay_app()
        loi = fake.van_ban_loai("error")
        self.assertEqual(len(loi), 1)
        self.assertTrue(loi[0].startswith("P3: loại") and "Trong giới hạn dự án (VA 1.20% > 1.00%)" in loi[0])
        dat = fake.van_ban_loai("success")
        for ten in ("P1", "P2"):
            self.assertTrue(any(t.startswith(f"{ten}: đúng cả 7 điều kiện") for t in dat), ten)
        self.assertTrue(any(t.startswith("Thanh trượt hiện tại so với công thức gốc: đúng") for t in dat))
        bang_kq = fake.bang[-1]
        self.assertEqual(list(bang_kq.columns), ["Điều kiện", "P1", "P2", "P3", "Thanh trượt hiện tại"])
        hang = bang_kq[bang_kq["Điều kiện"] == "Trong giới hạn dự án"].iloc[0]
        self.assertEqual((hang["P1"], hang["P3"]), ("✓ đều ≤ giới hạn", "✗ VA 1.20% > 1.00%"))

    def test_keo_thu_thanh_truot_van_hop_le_khong_hien_khung_do_ve_thanh_truot(self):
        fake = chay_app({khoa("LV"): 3.5, khoa("GE"): 2.0})        # lệch xa công thức B nhưng vẫn hợp lệ
        self.assertEqual(loi_cong_thuc(fake), [])
        self.assertEqual(fake.van_ban_loai("error"), ["P3: loại – không đạt: Trong giới hạn dự án (VA 1.20% > 1.00%)."])
        canh_bao = [t for t in fake.van_ban_loai("warning") if t.startswith("Thanh trượt hiện tại so với công thức gốc")]
        self.assertEqual(len(canh_bao), 1)
        self.assertIn("hãy ghi lý do vào nhật ký", canh_bao[0])

    def test_giao_dien_bang_nhap_co_dung_hinh_dang(self):
        fake = chay_app()
        df = fake.bang_sua[0]["df"]
        self.assertEqual(df.shape, (8, 5))
        self.assertEqual(list(df.columns), ["Giới hạn GV (%)", "Gốc (%)", "P1 (%)", "P2 (%)", "P3 (%)"])
        self.assertAlmostEqual(df["Gốc (%)"].iloc[-1], 86.0, places=9)
        self.assertAlmostEqual(df["P1 (%)"].iloc[-1], 85.6, places=9)

    def test_giao_dien_che_do_tu_nhap_bat_dau_trong(self):
        fake = chay_app({"che_do_ai_Thu": 1})
        self.assertTrue(fake.bang_sua[0]["df"][["P1 (%)", "P2 (%)", "P3 (%)"]].isna().all().all())
        self.assertTrue(any("Chưa có đề xuất nào" in t for t in fake.van_ban_loai("info")))
        self.assertEqual(fake.van_ban_loai("error"), [])

    def test_giao_dien_nhom_nhap_de_xuat_ai_tinh_sai_tong(self):
        def nhap(df):
            df["P1 (%)"] = df["Gốc (%)"]
            df.iloc[1, df.columns.get_loc("P1 (%)")] += 0.3          # BG +0.3 nhưng quên giảm dung môi
            return df
        fake = chay_app({"che_do_ai_Thu": 1, "bang_ai_Thu_0": nhap})
        loi = fake.van_ban_loai("error")
        self.assertEqual(len(loi), 1)
        self.assertIn("P1: loại", loi[0])
        self.assertIn("Tổng kể cả dung môi = 100% (tổng 100.30%)", loi[0])
        self.assertEqual(list(fake.bang[-1].columns), ["Điều kiện", "P1", "P2", "P3"])   # không có cột thanh trượt


class TestCa15SoanPrompt(unittest.TestCase):
    def setUp(self):
        nl = nguyen_lieu_thu()
        self.goc_df = nl[["ma", "ten", "tang", "gioi_han_pct"]].copy()
        self.goc_df["pct"] = [app.CONG_THUC_NHOM["Thu"]["B"][m] for m in nl["ma"]]
        mau = app.VI_DU_PROMPT["Thu"]
        self.prompt = app.build_prompt("Thu", self.goc_df, mau["cam_quan"], mau["nhan_xet"], mau["muc_tieu"], 3, 0.5)

    def test_co_du_4_phan(self):
        for phan in ("DỮ LIỆU", "MỤC TIÊU CẢI THIỆN", "RÀNG BUỘC (bắt buộc)", "ĐỊNH DẠNG ĐẦU RA"):
            self.assertIn(phan, self.prompt)

    def test_so_lieu_va_gioi_han_khop_bang(self):
        self.assertIn("- SW | Cam ngọt (Sweet orange) | tầng Đầu | hiện tại 2.1% | giới hạn dự án ≤ 3%", self.prompt)
        self.assertIn("- VA | Vanilla accord | tầng Cuối | hiện tại 0.7% | giới hạn dự án ≤ 1%", self.prompt)
        self.assertIn("- SO | Dung môi | bù đến 100% | hiện tại 86%", self.prompt)
        self.assertEqual(self.prompt.count("giới hạn dự án ≤"), 7)

    def test_rang_buoc_theo_tham_so_nhom_dat(self):
        self.assertIn("tối đa 3 thành phần hương", self.prompt)
        self.assertIn("không quá ±0.5 điểm phần trăm", self.prompt)
        mau = app.VI_DU_PROMPT["Thu"]
        khac = app.build_prompt("Thu", self.goc_df, mau["cam_quan"], mau["nhan_xet"], mau["muc_tieu"], 2, 1.0)
        self.assertIn("tối đa 2 thành phần hương", khac)
        self.assertIn("không quá ±1 điểm phần trăm", khac)

    def test_co_cac_rang_buoc_an_toan_va_du_lieu(self):
        for cau in ("không thêm nguyên liệu mới", "Không vượt giới hạn dự án", "đúng 100%",
                    "Không kết luận công thức là an toàn", "không tự tạo dữ liệu", "Không chọn phương án thay cho nhóm"):
            self.assertIn(cau, self.prompt)

    def test_khong_co_khoa_api_hay_du_lieu_ca_nhan(self):
        self.assertIsNone(re.search(r"api[_ -]?key|sk-[A-Za-z0-9]{8,}|token|mật khẩu", self.prompt, re.I))

    def test_prompt_trong_giao_dien_dung_cong_thuc_b_o_che_do_mau(self):
        fake = chay_app()
        self.assertEqual(fake.khoi_code[0], self.prompt)

    def test_che_do_nhom_dung_thanh_truot_hien_tai(self):
        fake = chay_app({"che_do_ai_Thu": 1, khoa("VA"): 0.9})
        self.assertIn("- VA | Vanilla accord | tầng Cuối | hiện tại 0.9% | giới hạn dự án ≤ 1%", fake.khoi_code[0])

    def test_mua_chua_co_vi_du_dung_o_mau_trong(self):
        nl = nguyen_lieu_thu().assign(mua="Hạ")
        bang = pd.concat([bang_gv(), nl], ignore_index=True)
        fake = chay_app({"mua": "Hạ"}, bang_nguyen_lieu=bang)
        self.assertIn("[DÁN BẢNG ĐIỂM CẢM QUAN", fake.khoi_code[0])


class TestCa16KhongNoiLaAnToan(unittest.TestCase):
    CAU_CAM = [r"công thức (này )?(là |đã )?an toàn", r"đã an toàn", r"hoàn toàn an toàn", r"đảm bảo an toàn",
               r"an toàn để (pha|dùng|sử dụng)", r"an toàn khi", r"safe"]

    def quet(self, fake):
        van_ban = "\n".join(t for _, t in fake.van_ban).lower()      # khối code (prompt) được kiểm tra riêng ở Ca 15
        for mau in self.CAU_CAM:
            self.assertIsNone(re.search(mau, van_ban), f"có câu khẳng định an toàn: {mau}")
        self.assertTrue(any("không đồng nghĩa với an toàn" in t for t in fake.van_ban_loai("warning")))

    def test_moi_tinh_huong_giao_dien(self):
        for ghi_de in ({}, {khoa("VA"): 1.5}, tat_ca_slider(0.0), tat_ca_slider(60.0), {"mua": "Hạ"},
                       {"che_do_ai_Thu": 1}, {"so_sanh": True}):
            self.quet(chay_app(ghi_de))
        self.quet(chay_app(bang_nguyen_lieu=app.LoiBangNguyenLieu("lỗi")))
        self.quet(chay_app(bang_nguyen_lieu=bang_gv().assign(trang_thai="ĐÃ DUYỆT", da_duyet=True)))

    def test_thong_diep_hop_le_noi_ro_chua_co_nghia_la_an_toan(self):
        fake = chay_app()
        self.assertTrue(any("chưa có nghĩa là an toàn" in t for t in fake.van_ban_loai("success")))


class TestCa17AppVaExcelCungKetLuan(unittest.TestCase):
    """Ca 17: 2000 tổ hợp ngẫu nhiên (bội của 0.1); đối chiếu với phép tính Decimal chính xác tuyệt đối."""

    def test_ket_luan_hop_le_va_dung_moi_khop_phep_tinh_chinh_xac(self):
        nl = nguyen_lieu_thu()
        gh = {m: Decimal(str(g)) for m, g in zip(nl["ma"], nl["gioi_han_pct"])}
        rng = random.Random(2026)
        so_hop_le = so_khong_hop_le = 0
        for _ in range(2000):
            x = {m: Decimal(rng.randint(-3, int(g * 10) + 3)) / 10 for m, g in gh.items()}   # có cả âm và vượt max
            the_tich = 1 + rng.randint(0, 38) / 2
            kq = app.calculate_formula(the_tich, {m: float(v) for m, v in x.items()}, nl)
            dung = (all(0 <= x[m] <= gh[m] for m in gh)) and (100 - sum(x.values()) >= 0)
            self.assertEqual(kq["valid"], dung, x)
            self.assertAlmostEqual(kq["solvent_pct"], float(100 - sum(x.values())), places=9)
            self.assertAlmostEqual(kq["total_ml"], the_tich, places=9)
            so_hop_le += dung
            so_khong_hop_le += not dung
        self.assertGreater(so_hop_le, 100)               # bảo đảm phép thử có cả hai loại
        self.assertGreater(so_khong_hop_le, 100)


class TestCaPhuGiaoDienNho(unittest.TestCase):
    def test_slider_cap_tren_bang_gioi_han_cua_gv(self):
        fake = chay_app()
        gh = dict(zip(nguyen_lieu_thu()["ma"], nguyen_lieu_thu()["gioi_han_pct"]))
        for s in fake.thanh_truot:
            ma = s["key"].split("_")[2]
            self.assertEqual(s["max"], gh[ma])
            self.assertEqual(s["key"], app.khoa_thanh_truot("Thu", ma, gh[ma]))
            self.assertEqual(s["min"], 0.0)

    def test_bang_hien_thi_toan_chuoi_de_tranh_loi_arrow(self):
        df = app.format_table(app.calculate_formula(10.0, b2(), nguyen_lieu_thu())["df"])
        for cot in df.columns:
            self.assertTrue(all(isinstance(x, str) for x in df[cot]), cot)
        self.assertEqual(df.iloc[-1]["Giới hạn GV (%)"], "—")
        self.assertEqual(df.iloc[0]["Thể tích (mL)"], "0.210")

    def test_khong_con_dung_tham_so_da_loi_thoi_use_container_width(self):
        ma_nguon = (THU_MUC / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("use_container_width", ma_nguon)

    def test_khong_ghi_khoa_api_trong_ma_nguon(self):
        ma_nguon = (THU_MUC / "app.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"sk-[A-Za-z0-9]{8,}|api_key\s*=|ANTHROPIC|OPENAI", ma_nguon))


@unittest.skipUnless(CO_STREAMLIT, "Chưa cài Streamlit nên bỏ qua AppTest (chạy: pip install streamlit)")
class TestAppTest(unittest.TestCase):
    """Chạy app thật bằng công cụ AppTest chính thức của Streamlit."""

    def chay(self):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(str(THU_MUC / "app.py"), default_timeout=60).run()

    def test_chay_lan_dau_khong_loi(self):
        at = self.chay()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        self.assertEqual(len(at.slider), 7)

    def test_keo_thanh_truot_va_doi_mua_khong_loi(self):
        at = self.chay()
        at.slider(key=app.khoa_thanh_truot("Thu", "VA", 1.0)).set_value(1.0).run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        at.selectbox(key="mua").select("Hạ").run()
        self.assertEqual(len(at.exception), 0, [e.value for e in at.exception])
        self.assertEqual(len(at.slider), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
