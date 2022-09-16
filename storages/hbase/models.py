from storages.hbase import BaseModel


class OBDInfoBaseData(BaseModel):
    """
    基础信息
    """

    Columns = {
        b"A:a04": "协议",
        b"A:a05": "采集时间",
        b"A:a07": "命令单元",
        b"B:a01": "原始数据",
        b"B:a02": "obd时间",
        b"A:i03": "信息列表",
    }

    class Meta:
        table_name = f"{BaseModel.table_prefix}_obd_info"
        row_key_format = "{unique_code}__{create_datetime}"
        hex_columns = [
            b"A:a04",
        ]
        json_columns = [
            b"A:i03",
        ]
        json_column_mapper = {b"A:i03": (list[dict], [("Attr1", "Attr1描述"), ("Attr2", "Attr2描述")])}
