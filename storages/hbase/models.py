from storages.hbase import BaseModel


class OBDInfoBaseData(BaseModel):
    """
    基础信息
    """
    protocol = (b"A:a04", "协议")
    collectTimeStr = (b"A:a05", "采集时间")
    commandFlag = (b"A:a07", "命令单元")
    rawData = (b"B:a01", "原始数据")
    obdTimeStr = (b"B:a02", "obd时间")
    InfoList = (b"A:i03", "信息列表")

    class Meta:
        table_name = f"{BaseModel.table_prefix}_obd_info"
        row_key_format = "{unique_code}__{create_datetime}"
        hex_fields = ["rawData", ]
        json_fields = ["InfoList", ]
        json_fields_mapper = {
            "InfoList": (
                list[dict],
                [("Attr1", "Attr1描述"), ("Attr1", "Attr2描述")])
        }
