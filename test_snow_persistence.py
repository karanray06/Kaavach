import unittest
from unittest.mock import MagicMock, patch
import pytest

from app.snow import insert_scan, insert_indicators, insert_or_update_campaign
from app.pipeline import sync_persist_to_snowflake
from app.extract import hash_ioc

def test_snowflake_inserts_mocked():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("app.snow.get_snowflake_connection", return_value=mock_conn):
        # 1. Test insert_scan
        scan_data = {
            "scan_id": "test-uuid-1",
            "lang": "en",
            "input_type": "text",
            "channel": "sms",
            "verdict": "LIKELY_SCAM",
            "risk_score": 0.95,
            "tactics": [{"code": "FAKE_KYC"}],
            "campaign": {"id": "C-TEST-01"}
        }
        res_scan = insert_scan(scan_data)
        assert res_scan is True
        mock_cursor.execute.assert_called()
        scan_sql, scan_params = mock_cursor.execute.call_args[0]
        assert "is_demo" in scan_sql.lower()
        assert "false" in scan_sql.lower()
        assert scan_params[0] == "test-uuid-1"
        assert scan_params[6] == "FAKE_KYC"
        assert scan_params[7] == "C-TEST-01"

        # 2. Test insert_indicators with 64-char HMAC hash
        test_ioc_val = "+919876543210"
        hashed_val = hash_ioc(test_ioc_val)
        assert len(hashed_val) == 64
        indicators_data = [
            {
                "scan_id": "test-uuid-1",
                "ioc_type": "phone",
                "ioc_hash": hashed_val,
                "ioc_display": "+91***",
                "tld": None
            }
        ]
        res_ind = insert_indicators(indicators_data)
        assert res_ind is True
        mock_cursor.executemany.assert_called()
        ind_sql, ind_params = mock_cursor.executemany.call_args[0]
        assert "is_demo" in ind_sql.lower()
        assert "false" in ind_sql.lower()
        assert len(ind_params[0][2]) == 64  # Must be 64-char hash
        assert ind_params[0][2] == hashed_val

        # 3. Test insert_or_update_campaign
        camp_data = {
            "id": "C-TEST-01",
            "primary_tactic": "FAKE_KYC",
            "variant_no": 3,
            "centroid_simhash": 123456789
        }
        res_camp = insert_or_update_campaign(camp_data)
        assert res_camp is True
        camp_sql, camp_params = mock_cursor.execute.call_args[0]
        assert "merge into campaigns" in camp_sql.lower()
        assert camp_params[0] == "C-TEST-01"

def test_sync_persist_to_snowflake_invokes_all_three():
    mock_scan_record = {
        "scan_id": "test-uuid-2",
        "lang": "en",
        "input_type": "text",
        "channel": "sms",
        "verdict": "LIKELY_SCAM",
        "risk_score": 0.88,
        "tactics": [{"code": "OTP_THEFT"}],
        "campaign": {"id": "C-TEST-02", "variant_no": 1, "centroid_simhash": 999}
    }
    raw_phone = "+919999988888"
    h = hash_ioc(raw_phone)
    mock_indicators = [
        {
            "scan_id": "test-uuid-2",
            "ioc_type": "phone",
            "ioc_hash": h,
            "ioc_display": "+91***",
            "tld": None
        }
    ]

    with patch("app.pipeline.insert_scan") as mock_ins_scan, \
         patch("app.pipeline.insert_indicators") as mock_ins_ind, \
         patch("app.pipeline.insert_or_update_campaign") as mock_ins_camp:

        sync_persist_to_snowflake(mock_scan_record, mock_indicators)

        mock_ins_scan.assert_called_once_with(mock_scan_record)
        mock_ins_ind.assert_called_once_with(mock_indicators)
        mock_ins_camp.assert_called_once()
        camp_arg = mock_ins_camp.call_args[0][0]
        assert camp_arg["id"] == "C-TEST-02"
        assert camp_arg["primary_tactic"] == "OTP_THEFT"
