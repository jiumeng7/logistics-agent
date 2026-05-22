from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

def load_rates():
    try:
        with open('data/rates.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"carriers": []}

def find_matching_tier(tiers, weight):
    """查找匹配的重量区间（左闭右开）"""
    for tier in tiers:
        if tier['min'] <= weight < tier['max']:
            return tier
    return None

def calculate_base_cost(tier, weight):
    """计算基础运费"""
    return weight * tier['rate']

def calculate_surcharges(surcharges, base_cost):
    """计算附加费"""
    total = 0
    for s in surcharges:
        if s['apply_to'] == 'base':
            total += base_cost * s['value']
        else:  # fixed
            total += s['value']
    return total

@app.route('/api/compare', methods=['POST'])
def compare():
    data = request.get_json()
    
    if not data or not all(k in data for k in ['weight', 'origin', 'destination']):
        return jsonify({"error": "缺少必填字段: weight, origin, destination"}), 400
    
    weight = float(data['weight'])
    origin = data['origin'].strip().upper()
    destination = data['destination'].strip().upper()
    max_days = data.get('max_days')
    if max_days:
        max_days = int(max_days)
    
    rates = load_rates()
    results = []
    
    for carrier in rates.get('carriers', []):
        for route in carrier.get('routes', []):
            if route['origin'] != origin or route['destination'] != destination:
                continue
            if max_days and route['transit_days'] > max_days:
                continue
                
            tier = find_matching_tier(route['weight_tiers'], weight)
            if not tier:
                continue
                
            base_cost = calculate_base_cost(tier, weight)
            surcharge = calculate_surcharges(route.get('surcharges', []), base_cost)
            total_cost = base_cost + surcharge
            
            results.append({
                "carrier": carrier['name'],
                "route": f"{origin} → {destination}",
                "transit_days": route['transit_days'],
                "weight_tier": f"{tier['min']}-{tier['max']}kg",
                "base_cost": round(base_cost, 2),
                "surcharge": round(surcharge, 2),
                "total_cost": round(total_cost, 2)
            })
    
    # 排序（成本最低优先）
    results.sort(key=lambda x: x['total_cost'])
    
    recommendation = results[0] if results else None
    
    return jsonify({
        "all_schemes": results,
        "recommendation": recommendation,
        "message": f"找到 {len(results)} 个可用方案" if results else "未找到匹配的运输方案"
    })

if __name__ == '__main__':
    print("🚀 物流比价系统已启动！ http://localhost:5000")
    app.run(debug=True, port=5000)