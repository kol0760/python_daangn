from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import json
import pandas as pd

app = Flask(__name__)

base_url = "https://www.daangn.com/kr/buy-sell/?in={}&search={}"

def search_for_products(url):
    response = requests.get(url)
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
                "Description": data["item"]["description"],
                "Image": data["item"]["image"],
                "URL": data["item"]["url"],
                "Price": data["item"]["offers"]["price"],
                "Currency": data["item"]["offers"]["priceCurrency"],
                "Condition": data["item"]["offers"]["itemCondition"],
                "Availability": data["item"]["offers"]["availability"],
                "Seller": data["item"]["offers"]["seller"]["name"]
            }])
            dfs.append(df)
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return combined_df

@app.route('/search', methods=['GET'])
def search():
    search_keyword = request.args.get('keyword')
    regions = request.args.getlist('region')
    urls = [base_url.format(region, search_keyword) for region in regions]

    product_tables = []
    for url in urls:
        try:
            product_table = search_for_products(url)
            product_tables.append(product_table)
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Request failed for URL: {url}, Error: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"Error processing URL: {url}, Error: {str(e)}"}), 500

    combined_table = pd.concat(product_tables, ignore_index=True) if product_tables else pd.DataFrame()
    result = combined_table.to_dict(orient='records')
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)

