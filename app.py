from flask import Flask, render_template, request, send_file, Response
import requests
from bs4 import BeautifulSoup
import re
import json
import pandas as pd
import os
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

base_url = "https://www.daangn.com/kr/buy-sell/?in={}&search={}"

# HTML template for the form page
html_template = '''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
    <title>Product Search</title>
    <style>
      body {
        background-color: #f8f9fa;
      }
      .container {
        margin-top: 50px;
        max-width: 600px;
        background: #ffffff;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      }
      h1 {
        text-align: center;
        color: #007bff;
      }
      .btn-primary {
        width: 100%;
        padding: 10px;
      }
      .form-group label {
        font-weight: bold;
      }
      #progress {
        margin-top: 20px;
        text-align: center;
        font-size: 1.2em;
        color: #007bff;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1 class="mt-3 mb-4">Search for Products</h1>
      <form method="POST" action="/search">
        <div class="form-group">
          <label for="keyword">Enter Product Keyword:</label>
          <input type="text" class="form-control" id="keyword" name="keyword" placeholder="e.g. laptop, phone, shoes" required>
        </div>
        <button type="submit" class="btn btn-primary">Search</button>
      </form>
      <div id="progress"></div>
    </div>
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script>
      $(function() {
        if (typeof(EventSource) !== "undefined") {
          var source = new EventSource("/progress");
          source.onmessage = function(event) {
            $("#progress").text(event.data);
          };
        }
      });
    </script>
    <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.3/dist/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
  </body>
</html>
'''


progress_message = ""


regions = ["강남구",
"강동구",
"강북구",
"강서구",
"관악구",
"광진구",
"구로구",
"금천구",
"노원구",
"도봉구",
"동대문구",
"동작구",
"마포구",
"서대문구",
"서초구",
"성동구",
"성북구",
"송파구",
"양천구",
"영등포구",
"용산구",
"은평구",
"종로구",
"중구",
"중랑구",
"북구",
"부산진구",
"동구",
"동래구",
"강서구",
"금정구",
"해운대구",
"중구",
"남구",
"사하구",
"사상구",
"서구",
"수영구",
"영도구",
"연제구",
"기장군",
"북구",
"동구",
"중구",
"남구",
"서구",
"달서구",
"수성구",
"달성군",
"군위군",
"부평구",
"계양구",
"동구",
"중구",
"미추홀구",
"서구",
"남동구",
"연수구",
"강화군",
"옹진군",
"북구",
"동구",
"남구",
"서구",
"광산구",
"중구",
"동구",
"대덕구",
"서구",
"유성구",
"북구",
"동구",
"중구",
"남구",
"울주군",
"한솔동",
"연기면",
"금남면",
"장군면",
"부강면",
"연동면",
"연서면",
"전의면",
"전동면",
"소정면",
"조치원읍",
"수원시",
"고양시",
"용인시",
"성남시",
"부천시",
"안산시",
"안양시",
"남양주시",
"화성시",
"의정부시",
"시흥시",
"평택시",
"광명시",
"파주시",
"군포시",
"광주시",
"김포시",
"이천시",
"양주시",
"구리시",
"오산시",
"안성시",
"의왕시",
"포천시",
"하남시",
"동두천시",
"과천시",
"여주시",
"양평군",
"가평군",
"연천군",
"원주시",
"춘천시",
"강릉시",
"동해시",
"속초시",
"삼척시",
"태백시",
"홍천군",
"철원군",
"횡성군",
"평창군",
"정선군",
"영월군",
"인제군",
"고성군",
"양양군",
"화천군",
"양구군",
"청주시",
"충주시",
"제천시",
"음성군",
"진천군",
"옥천군",
"영동군",
"괴산군",
"증평군",
"보은군",
"단양군",
"천안시",
"아산시",
"서산시",
"당진시",
"공주시",
"논산시",
"보령시",
"계룡시",
"홍성군",
"예산군",
"부여군",
"서천군",
"태안군",
"금산군",
"청양군",
"전주시",
"익산시",
"군산시",
"정읍시",
"김제시",
"남원시",
"완주군",
"고창군",
"부안군",
"순창군",
"임실군",
"무주군",
"진안군",
"장수군",
"여수시",
"목포시",
"순천시",
"광양시",
"나주시",
"무안군",
"해남군",
"고흥군",
"화순군",
"영암군",
"영광군",
"완도군",
"담양군",
"보성군",
"장성군",
"장흥군",
"강진군",
"신안군",
"함평군",
"진도군",
"곡성군",
"구례군",
"포항시",
"구미시",
"경산시",
"경주시",
"안동시",
"김천시",
"영주시",
"상주시",
"영천시",
"문경시",
"칠곡군",
"의성군",
"울진군",
"예천군",
"청도군",
"성주군",
"영덕군",
"고령군",
"봉화군",
"청송군",
"영양군",
"울릉군",
"창원시",
"김해시",
"진주시",
"양산시",
"거제시",
"통영시",
"사천시",
"밀양시",
"함안군",
"거창군",
"창녕군",
"고성군",
"남해군",
"합천군",
"하동군",
"함양군",
"산청군",
"의령군",
"제주시",
"서귀포시"]

def search_for_products(url, progress_queue=None):
    response = requests.get(url)
    if progress_queue:
        progress_queue.put("Fetched data from URL")
    soup = BeautifulSoup(response.content, 'html.parser')
    script_tag = soup.find("script", string=re.compile(r'{"@type":"ListItem"'))
    if not script_tag:
        return pd.DataFrame()  # Return an empty DataFrame if no data is found

    json_text = script_tag.string
    match = re.findall(r'{"@type":"ListItem".*?}}}}', json_text)
    dfs = []
    if match:
        for json_fragment in match:
            data = json.loads(json_fragment)
            df = pd.DataFrame([{
                "Type": data["@type"],
                "Position": data["position"],
                "Name": data["item"]["name"],
                "Description": data["item"].get("description", "N/A"),
                "Image": data["item"]["image"],
                "URL": data["item"]["url"],
                "Price": data["item"]["offers"].get("price", "N/A"),
                "Currency": data["item"]["offers"].get("priceCurrency", "N/A"),
                "Condition": data["item"]["offers"].get("itemCondition", "N/A"),
                "Availability": data["item"]["offers"].get("availability", "N/A"),
                "Seller": data["item"]["offers"].get("seller", {}).get("name", "N/A")
            }])
            dfs.append(df)
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return combined_df

@app.route('/')
def index():
    return html_template

@app.route('/progress')
def progress():
    def generate():
        global progress_message
        while True:
            time.sleep(1)
            yield f"data: {progress_message}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/search', methods=['POST'])
def search():
    global progress_message
    search_keyword = request.form.get('keyword')
    urls = [base_url.format(region, search_keyword) for region in regions]

    product_tables = []

    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(search_for_products, url): url for url in urls}
        for i, future in enumerate(as_completed(future_to_url), 1):
            url = future_to_url[future]
            try:
                progress_message = f"Processing region {i}/{len(regions)}: {regions[i-1]}"
                product_table = future.result()
                product_tables.append(product_table)
            except requests.exceptions.RequestException as e:
                progress_message = f"Request failed for URL: {url}, Error: {str(e)}"
                return f"<p>Request failed for URL: {url}, Error: {str(e)}</p>", 500
            except Exception as e:
                progress_message = f"Error processing URL: {url}, Error: {str(e)}"
                return f"<p>Error processing URL: {url}, Error: {str(e)}</p>", 500

    combined_table = pd.concat(product_tables, ignore_index=True) if product_tables else pd.DataFrame()
    csv_filename = 'result_products.csv'
    combined_table.to_csv(csv_filename, index=False)

    progress_message = "Search completed. Preparing download."
    return send_file(csv_filename, as_attachment=True, download_name='result_products.csv')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
