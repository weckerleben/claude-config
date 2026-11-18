"""Tests de las funciones puras de shifted_dates.py (sin red ni credenciales).

    python3 -I -m unittest discover -s tests -v      (desde la carpeta del skill)
"""
import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import shifted_dates as sd  # noqa: E402


class ClassifyKey(unittest.TestCase):
    def test_document_key_carries_the_v16_id(self):
        self.assertEqual(sd.classify_key("move_3mit_grupocashea_96641784"), ("document", 96641784))

    def test_aggregate_key_has_no_v16_id(self):
        self.assertEqual(sd.classify_key("agg_e3fd8e1311e2d4296b69994b"), ("aggregate", None))

    def test_statement_group_key(self):
        self.assertEqual(sd.classify_key("sagg_0123456789abcdef01234567"), ("statement", None))

    def test_anything_else_is_other(self):
        self.assertEqual(sd.classify_key("slice_74774941_a"), ("other", None))
        self.assertEqual(sd.classify_key("move_without_number"), ("other", None))


class AggregateDay(unittest.TestCase):
    def test_reads_the_day_from_the_reference(self):
        ref = "Aggregated entries 2026-10-31 [Cashea Valores, C.A]"
        self.assertEqual(sd.aggregate_day(ref), "2026-10-31")

    def test_reference_without_a_day_gives_none(self):
        self.assertIsNone(sd.aggregate_day("MISC adjustment"))
        self.assertIsNone(sd.aggregate_day(False))


class Compare(unittest.TestCase):
    def test_same_date_is_not_a_difference(self):
        self.assertIsNone(sd.date_gap("2026-10-31", "2026-10-31"))

    def test_gap_is_destination_minus_source_in_days(self):
        self.assertEqual(sd.date_gap("2026-10-31", "2026-11-13"), 13)
        self.assertEqual(sd.date_gap("2026-10-31", "2026-10-30"), -1)

    def test_missing_source_date_gives_none(self):
        self.assertIsNone(sd.date_gap(False, "2026-11-13"))


class BuildRows(unittest.TestCase):
    def setUp(self):
        self.tagged = [
            {"name": "move_x_100", "res_id": 1},
            {"name": "agg_aaa", "res_id": 2},
            {"name": "move_x_300", "res_id": 3},
            {"name": "slice_q", "res_id": 4},
        ]
        self.v19 = {
            1: {"id": 1, "name": "INV/1", "date": "2026-11-13", "ref": False, "state": "posted",
                "move_type": "out_invoice", "company_id": [58, "Cashea Valores"], "amount_total_signed": 10.0},
            2: {"id": 2, "name": "MISC/1", "date": "2026-11-13", "state": "posted",
                "ref": "Aggregated entries 2026-10-31 [Cashea]", "move_type": "entry",
                "company_id": [58, "Cashea Valores"], "amount_total_signed": 5.0},
            3: {"id": 3, "name": "INV/3", "date": "2026-10-05", "ref": False, "state": "posted",
                "move_type": "out_invoice", "company_id": [58, "Cashea Valores"], "amount_total_signed": 7.0},
            4: {"id": 4, "name": "MISC/4", "date": "2026-10-09", "ref": "x", "state": "posted",
                "move_type": "entry", "company_id": [58, "Cashea Valores"], "amount_total_signed": 1.0},
        }
        self.v16 = {
            100: {"id": 100, "date": "2026-10-31", "sync_v19_move_id": 1},
            300: {"id": 300, "date": "2026-10-05", "sync_v19_move_id": 3},
        }

    def test_only_shifted_moves_come_out(self):
        rows, stats = sd.build_rows(self.tagged, self.v19, self.v16)
        self.assertEqual([r["v19_id"] for r in rows], [1, 2])
        self.assertEqual(stats["checked"], 3)
        self.assertEqual(stats["other"], 1)

    def test_row_carries_both_dates_and_the_gap(self):
        rows, _ = sd.build_rows(self.tagged, self.v19, self.v16)
        doc = rows[0]
        self.assertEqual((doc["kind"], doc["v16_id"], doc["date_v16"], doc["date_v19"], doc["gap_days"]),
                         ("document", 100, "2026-10-31", "2026-11-13", 13))
        agg = rows[1]
        self.assertEqual((agg["kind"], agg["v16_id"], agg["date_v16"], agg["gap_days"]),
                         ("aggregate", "", "2026-10-31", 13))

    def test_a_document_whose_v16_move_points_elsewhere_is_reported(self):
        self.v16[100]["sync_v19_move_id"] = 999
        rows, stats = sd.build_rows(self.tagged, self.v19, self.v16)
        self.assertEqual(stats["link_mismatch"], 1)
        self.assertEqual(rows[0]["link_ok"], "no")

    def test_missing_v16_record_is_counted_not_crashed_on(self):
        del self.v16[100]
        rows, stats = sd.build_rows(self.tagged, self.v19, self.v16)
        self.assertEqual(stats["v16_missing"], 1)
        self.assertEqual([r["v19_id"] for r in rows], [2])

    def test_tagged_move_that_no_longer_exists_in_v19_is_counted(self):
        del self.v19[1]
        _, stats = sd.build_rows(self.tagged, self.v19, self.v16)
        self.assertEqual(stats["v19_missing"], 1)


class OrphanSlices(unittest.TestCase):
    def setUp(self):
        self.tagged = [{"name": "orphan_x_77_123", "res_id": 9}]
        self.v19 = {9: {"id": 9, "name": "MISC/9", "date": "2026-10-01", "state": "posted",
                        "ref": "x EP443 orphan matching 77/123", "move_type": "entry",
                        "company_id": [1, "VE"], "amount_total_signed": 3.0}}

    def test_partial_id_is_the_last_number_of_the_link_key(self):
        self.assertEqual(sd.orphan_partial_id("EP443 orphan matching 123"), 123)
        self.assertEqual(sd.orphan_partial_id("a EP443 orphan matching 77/123 b"), 123)
        self.assertIsNone(sd.orphan_partial_id("MISC adjustment"))
        self.assertIsNone(sd.orphan_partial_id(False))

    def test_slice_dated_as_neither_move_of_the_matching_is_shifted(self):
        rows, stats = sd.build_rows(self.tagged, self.v19, {}, {123: {"2025-12-04", "2026-07-01"}})
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["kind"], rows[0]["date_v16"], rows[0]["gap_days"]),
                         ("orphan", "2025-12-04", 301))
        self.assertEqual(stats["checked"], 1)

    def test_slice_dated_as_one_of_the_moves_is_not_shifted(self):
        self.v19[9]["date"] = "2026-07-01"
        rows, stats = sd.build_rows(self.tagged, self.v19, {}, {123: {"2025-12-04", "2026-07-01"}})
        self.assertEqual(rows, [])
        self.assertEqual(stats["checked"], 1)

    def test_matching_gone_from_v16_is_counted(self):
        rows, stats = sd.build_rows(self.tagged, self.v19, {}, {})
        self.assertEqual(rows, [])
        self.assertEqual(stats["v16_missing"], 1)

    def test_without_the_matching_dates_slices_are_just_counted(self):
        rows, stats = sd.build_rows(self.tagged, self.v19, {})
        self.assertEqual(rows, [])
        self.assertEqual(stats["other"], 1)


class Csv(unittest.TestCase):
    def test_csv_has_a_stable_header_and_one_line_per_row(self):
        rows = [{"company": "A", "kind": "document", "v16_id": 1, "v19_id": 2, "v19_name": "N",
                 "move_type": "entry", "state": "posted", "date_v16": "2026-10-31",
                 "date_v19": "2026-11-13", "gap_days": 13, "amount": 5.0, "link_ok": "yes"}]
        buf = io.StringIO()
        sd.write_csv(rows, buf)
        out = list(csv.reader(io.StringIO(buf.getvalue())))
        self.assertEqual(out[0], sd.CSV_FIELDS)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[1][out[0].index("gap_days")], "13")


if __name__ == "__main__":
    unittest.main()
