from storages.hbase import BaseModel


class FaultRecordData(BaseModel):
    vin = b"A:a01"
    unique_code = b"A:a02"
    first_alert_time = b"A:a03"
    obd_time = b"A:a04"
    receive_time = b"A:a05"

    class Meta:
        table_name = "fault_record"
        row_key_format = "{vin}__{create_datetime}"
