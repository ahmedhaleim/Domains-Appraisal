# --- الكود المصحح ---
from flask import Flask, render_template_string, request
import requests
import json
import os
from urllib.parse import quote

app = Flask(__name__)

# --- إعدادات التطبيق ---
# سيتم قراءة المفاتيح من متغيرات البيئة في Vercel
API_KEY = os.environ.get('GODADDY_API_KEY')
API_SECRET = os.environ.get('GODADDY_API_SECRET')

GODADDY_API_URL = 'https://api.godaddy.com/v1/appraisal/{domain}'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أداة تقييم الدومينات</title>
    <style>
        body { font-family: 'Cairo', sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { width: 100%; max-width: 600px; margin: 20px; padding: 30px; background-color: #fff; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1 ); }
        h1 { color: #2c3e50; text-align: center; }
        form { display: flex; margin-top: 20px; }
        input[type="text"] { flex-grow: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px 0 0 5px; font-size: 16px; text-align: left; direction: ltr; }
        button { padding: 12px 20px; background-color: #3498db; color: white; border: none; cursor: pointer; border-radius: 0 5px 5px 0; font-size: 16px; white-space: nowrap; }
        button:hover { background-color: #2980b9; }
        .result-section { margin-top: 30px; padding: 20px; border: 1px solid #b8d9f3; border-radius: 5px; text-align: center; }
        .result-section h2 { margin-top: 0; color: #2980b9; }
        .error { background-color: #ffebee; border-color: #ffcdd2; color: #c62828; }
        .price { font-size: 28px; font-weight: bold; margin: 10px 0; color: #2c3e50; }
        .namebio-link { display: inline-block; margin-top: 15px; padding: 10px 15px; background-color: #27ae60; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .namebio-link:hover { background-color: #229954; }
    </style>
    <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <h1>أداة تقييم أسعار الدومينات</h1>
        <form method="post">
            <input type="text" name="domain" placeholder="example.com" required value="{{ domain_input or '' }}">
            <button type="submit">قيّم الآن</button>
        </form>
        
        {% if error %}
            <div class="result-section error">
                <p>{{ error }}</p>
            </div>
        {% endif %}

        {% if appraisal %}
            <div class="result-section">
                <h2>التقييم التقديري من GoDaddy</h2>
                <p class="price">${{ "{:,.0f}".format(appraisal.govalue ) }}</p>
                <p>النطاق: {{ appraisal.domain }}</p>
                <a class="namebio-link" href="https://namebio.com/?s=={{ namebio_query }}" target="_blank">ابحث عن مبيعات مشابهة في NameBio</a>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'] )
def home():
    appraisal_data = None
    error_message = None
    domain_input = request.form.get('domain', '').strip().lower() if request.method == 'POST' else ''
    namebio_query = None

    if request.method == 'POST':
        if not domain_input:
            error_message = "الرجاء إدخال اسم نطاق صحيح."
        elif not API_KEY or not API_SECRET:
             error_message = "خطأ في الإعداد: مفاتيح GoDaddy API غير موجودة. يرجى التأكد من إضافتها بشكل صحيح في إعدادات Vercel."
        else:
            headers = {'Authorization': f'sso-key {API_KEY}:{API_SECRET}'}
            try:
                response = requests.get(GODADDY_API_URL.format(domain=domain_input), headers=headers)
                response.raise_for_status() # سيؤدي هذا إلى ظهور خطأ في حالة الاستجابات الفاشلة (4xx أو 5xx)
                appraisal_data = response.json()
                main_keyword = domain_input.split('.')[0].replace('-', ' ')
                namebio_query = quote(main_keyword)
            except requests.exceptions.HTTPError as err:
                error_message = f"حدث خطأ من GoDaddy (Code: {err.response.status_code}). تأكد من أن النطاق صحيح وأن مفاتيح API تعمل."
            except Exception as e:
                error_message = f"فشل الاتصال بالخادم: {e}"
    
    return render_template_string(HTML_TEMPLATE, appraisal=appraisal_data, error=error_message, domain_input=domain_input, namebio_query=namebio_query)

# هذا السطر ليس ضروريًا لـ Vercel ولكنه جيد للاختبار المحلي
if __name__ == '__main__':
    app.run(debug=True)
