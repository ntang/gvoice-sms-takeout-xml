#!/bin/bash
# Run attachment mapping stage tests

cd /Users/nicholastang/gvoice-sms-takeout-xml
source env/bin/activate
python -m pytest tests/unit/test_attachment_mapping_stage.py -v --tb=short
