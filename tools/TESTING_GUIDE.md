# NumVerify API Testing Guide

## 🧪 OVERVIEW
This guide shows you how to test the NumVerify API with a small sample of numbers before using your full free tier allocation.

**Goal**: Validate API functionality with minimal cost (under $0.10)

---

## 🚀 QUICK START

### Step 1: Create Test Sample
```bash
cd /Users/nicholastang/gvoice-sms-takeout-xml
source env/bin/activate
python tools/create_test_sample.py
```

This creates `test_sample_numbers.csv` with 5 random numbers from your dataset.

### Step 2: Test API Functionality
```bash
python tools/test_numverify_api.py
```

Enter your NumVerify API key when prompted.

### Step 3: Review Results
- Check `numverify_test_results.csv` for detailed results
- Verify API responses are correct
- Confirm cost is as expected

---

## 📊 TESTING OPTIONS

### Option 1: Random Sample (Recommended)
- **File**: `tools/create_test_sample.py`
- **Numbers**: 5 random numbers from your dataset
- **Cost**: $0.05
- **Time**: ~3 minutes

### Option 2: Manual Test Numbers
- **File**: `tools/test_numverify_api.py` (fallback mode)
- **Numbers**: Pre-defined test numbers (US, UK, France, toll-free)
- **Cost**: $0.05
- **Time**: ~3 minutes

### Option 3: Custom Sample
Modify `create_test_sample.py` to change sample size:
```python
sample_size = 10  # Change from 5 to 10 for more thorough testing
```

---

## 🔍 WHAT TO LOOK FOR

### ✅ Success Indicators:
- **API Key Valid**: No authentication errors
- **Responses Received**: All numbers get API responses
- **Data Quality**: Carrier, country, line type information present
- **Cost Accurate**: Matches expected $0.01 per lookup

### ❌ Warning Signs:
- **Authentication Errors**: Check API key
- **Rate Limiting**: Increase delay between calls
- **Network Errors**: Check internet connection
- **Invalid Responses**: Check API service status

---

## 📋 SAMPLE TEST RESULTS

### Expected Output:
```csv
phone_number,test_status,valid,carrier,line_type,country_name,location
+12025551234,success,true,Twilio,voip,United States,New York
+15551234567,success,true,Verizon,mobile,United States,California
+18001234567,success,true,Toll Free,landline,United States,Unknown
+447700900123,success,true,EE,mobile,United Kingdom,London
+33123456789,success,true,Orange,mobile,France,Paris
```

### Classification Examples:
- **Commercial**: Twilio, Bandwidth, business carriers
- **Personal**: Verizon, AT&T, T-Mobile, EE, Orange
- **Spam**: Toll-free, premium rate, suspicious carriers
- **Invalid**: Disconnected, invalid format

---

## 🛠️ TROUBLESHOOTING

### Common Issues:

#### 1. API Key Invalid
```
Error: Invalid API key
Solution: Double-check key from NumVerify dashboard
```

#### 2. Rate Limiting
```
Error: Too many requests
Solution: Increase delay in test script
```

#### 3. Network Errors
```
Error: Connection timeout
Solution: Check internet connection, try again
```

#### 4. No Response
```
Error: Empty response
Solution: Check API service status, verify endpoint
```

---

## 💰 COST MANAGEMENT

### Free Tier Usage:
- **NumVerify Free Tier**: 1,000 requests/month
- **Test Cost**: $0.05 (5 numbers)
- **Remaining**: 995 requests for full implementation
- **Full Implementation**: 646 numbers = $6.46

### Cost Tracking:
The test script shows:
- Real-time cost per request
- Total test cost
- Remaining free tier allocation

---

## 🎯 VALIDATION CHECKLIST

Before proceeding with full implementation:

- [ ] **API Key Works**: No authentication errors
- [ ] **Responses Complete**: All test numbers get responses
- [ ] **Data Quality Good**: Carrier, country, line type present
- [ ] **Cost Accurate**: Matches $0.01 per lookup
- [ ] **Classification Logic**: Commercial/Personal/Spam detection works
- [ ] **Error Handling**: Failed requests are handled gracefully
- [ ] **Export Format**: CSV output is correct

---

## 🚀 NEXT STEPS

### If Test Passes:
1. ✅ Proceed with full implementation
2. ✅ Run `python tools/numverify_api_lookup.py`
3. ✅ Process all 646 numbers
4. ✅ Integrate results into your system

### If Test Fails:
1. ❌ Fix API issues first
2. ❌ Check API key validity
3. ❌ Verify network connectivity
4. ❌ Contact NumVerify support if needed

---

## 📞 SUPPORT

### NumVerify Support:
- **Email**: support@numverify.com
- **Documentation**: [NumVerify API Docs](https://numverify.com/documentation)
- **Status**: [API Status Page](https://status.numverify.com/)

### Test Script Issues:
- Check Python environment: `source env/bin/activate`
- Verify dependencies: `pip install requests`
- Check file permissions and paths

---

## ✅ SUCCESS CRITERIA

Your test is successful when:
- ✅ All 5 test numbers get API responses
- ✅ Response data includes carrier, country, line type
- ✅ Cost matches expected $0.05
- ✅ No authentication or network errors
- ✅ Classification logic works correctly

**Ready to test? Run the commands above!** 🚀
