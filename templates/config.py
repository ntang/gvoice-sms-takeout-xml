# Template configuration for Google Voice SMS Takeout XML Converter

# SMS XML template for individual messages
SMS_XML_TEMPLATE = '<sms protocol="0" address="{alias}" date="{time}" type="{type}" subject="null" body="{message}" toa="null" sc_toa="null" service_center="null" read="1" status="1" locked="0" />\n'

# MMS XML template for multimedia messages (complex version with parts)
MMS_XML_TEMPLATE = """<mms address="{participants}" ct_t="application/vnd.wap.multipart.related" date="{time}" m_type="{m_type}" msg_box="{msg_box}" read="1" rr="129" seen="1" sim_slot="1" sub_id="-1" text_only="{text_only}">
    <parts>
{text_part}{image_parts}{vcard_parts}  </parts>
    <addrs>
{participants_xml}  </addrs>
</mms>"""

# MMS part templates
TEXT_PART_TEMPLATE = '    <part ct="text/plain" seq="0" text="{text}"/> \n'
PARTICIPANT_TEMPLATE = '    <addr address="{number}" charset="106" type="{code}"/> \n'
IMAGE_PART_TEMPLATE = '    <part seq="0" ct="{type}" name="{name}" chset="null" cd="null" fn="null" cid="&lt;{name}&gt;" cl="{name}" ctt_s="null" ctt_t="null" text="null" data="{data}" />\n'
VCARD_PART_TEMPLATE = '    <part seq="0" ct="text/x-vCard" name="{name}" chset="null" cd="null" fn="null" cid="&lt;{name}&gt;" cl="{name}" ctt_s="null" ctt_t="null" text="null" data="{data}" />\n'

# Call log XML template
CALL_XML_TEMPLATE = """<call number="{alias}" duration="{duration}" date="{time}" type="{call_type}" presentation="1" readable_date="{readable_date}" readable_duration="{readable_duration}" />"""

# Voicemail XML template
VOICEMAIL_XML_TEMPLATE = """<voicemail number="{alias}" duration="{duration}" date="{time}" transcription="{transcription}" />"""
