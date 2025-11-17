# Shopee Calculator - Detailed Breakdown Guide

## Tổng quan

Feature **Detailed Breakdown** hiển thị bảng kết quả tính toán chi tiết theo từng bước, giống cách Shopee tính phí và lợi nhuận. Giúp người bán hiểu rõ ràng từng khoản phí, chi phí và lợi nhuận.

## Cấu trúc Breakdown

### 1. Workflow Profit Calculation

Khi tính lợi nhuận từ giá bán, breakdown bao gồm 7 sections:

#### Section 1: Giá bán
```
Giá bán sản phẩm: 500,000 VND
```

#### Section 2: Phí Shopee
```
Phí thanh toán (5.00%): -25,000 VND
  💡 500,000 × 5.00% = 25,000

Phí cố định - Hoa hồng (1.47%): -7,350 VND
  💡 500,000 × 1.47% = 7,350

Phí hạ tầng: -3,000 VND
  💡 3,000 VND cố định/đơn
──────────────────────────────────────────────────
Tổng phí Shopee: -35,350 VND
```

#### Section 3: Doanh thu ròng sau phí Shopee
```
Giá bán - Phí Shopee: 464,650 VND
  💡 500,000 - 35,350 = 464,650
```

#### Section 4: Chi phí khác
```
Chi phí vận chuyển: -25,000 VND
Chi phí đóng gói: -5,000 VND
──────────────────────────────────────────────────
Tổng chi phí khác: -30,000 VND
```

#### Section 5: Giá vốn
```
Giá vốn sản phẩm: -300,000 VND
```

#### Section 6: Lợi nhuận ròng
```
Doanh thu ròng - Chi phí khác - Giá vốn: 134,650 VND
  💡 464,650 - 30,000 - 300,000 = 134,650
```

#### Section 7: Chỉ số hiệu quả
```
Tỷ suất lợi nhuận (Profit Margin): 26.93%
  💡 (Lợi nhuận / Giá bán) × 100 = (134,650 / 500,000) × 100

ROI (Return on Investment): 44.88%
  💡 (Lợi nhuận / Giá vốn) × 100 = (134,650 / 300,000) × 100

Giá hòa vốn (Breakeven): 412,000 VND
  💡 Giá bán tối thiểu để đạt lợi nhuận = 0
```

### 2. Workflow Pricing Calculation

Khi tính giá bán từ giá vốn và lợi nhuận mong muốn, breakdown tương tự nhưng bắt đầu từ giá đề xuất:

#### Cấu trúc tương tự với 6 sections:
1. Giá bán được đề xuất
2. Phí Shopee (ước tính)
3. Chi phí khác
4. Giá vốn
5. Lợi nhuận dự kiến
6. Chỉ số hiệu quả

## API Response Format

### Profit Calculation Response

```json
{
  "success": true,
  "data": {
    "sale_price": 500000,
    "cost_price": 300000,
    "total_shopee_fees": 35350,
    "net_profit": 134650,
    "profit_margin_percent": 26.93,

    "breakdown": {
      "calculation_type": "profit",
      "sections": [
        {
          "title": "Giá bán",
          "items": [
            {
              "label": "Giá bán sản phẩm",
              "value": 500000,
              "formatted": "500,000 VND",
              "type": "base",
              "highlight": true
            }
          ],
          "subtotal": null
        },
        {
          "title": "Phí Shopee",
          "items": [
            {
              "label": "Phí thanh toán (5.00%)",
              "value": -25000,
              "formatted": "-25,000 VND",
              "type": "fee",
              "calculation": "500,000 × 5.00% = 25,000"
            }
          ],
          "subtotal": {
            "label": "Tổng phí Shopee",
            "value": -35350,
            "formatted": "-35,350 VND",
            "type": "negative"
          }
        }
      ],
      "summary": {
        "sale_price": 500000,
        "total_fees": 35350,
        "total_custom_costs": 30000,
        "cost_price": 300000,
        "net_profit": 134650,
        "profit_margin_percent": 26.93,
        "roi_percent": 44.88,
        "is_profitable": true
      }
    },

    "breakdown_text": "... (formatted plain text version)"
  }
}
```

## Sử dụng API

### 1. Calculate Profit với Breakdown

```bash
POST /api/shopee-calculator/calculate/profit
Content-Type: application/json

{
  "user_email": "seller@example.com",
  "product_name": "iPhone 15 Pro",
  "product_sku": "IP15P-001",
  "seller_type": "non_mall",
  "category_code": "non_mall_electronics",
  "sale_price": 500000,
  "cost_price": 300000,
  "enabled_fees": {
    "payment_fee": true,
    "fixed_fee": true,
    "infrastructure_fee": true
  },
  "custom_costs": [
    {
      "enabled": true,
      "cost_name": "Chi phí vận chuyển",
      "value": 25000,
      "calculation_type": "fixed_per_order"
    }
  ]
}
```

**Response** sẽ bao gồm:
- `breakdown`: Object chi tiết từng section
- `breakdown_text`: Text format để hiển thị trên console/log

### 2. Calculate Pricing với Breakdown

```bash
POST /api/shopee-calculator/calculate/pricing
Content-Type: application/json

{
  "cost_price": 300000,
  "desired_profit": 100000,
  "pricing_reference_point": "target_profit",
  "num_price_options": 5,
  ...
}
```

**Response** sẽ bao gồm breakdown cho giá được đề xuất (recommended_price).

### 3. Get Breakdown cho Price Option cụ thể

Nếu user muốn xem breakdown cho một price option khác trong danh sách 5-10 options:

```bash
POST /api/shopee-calculator/calculate/breakdown
Content-Type: application/json

{
  "calculation_type": "pricing",
  "calc_result": {...},  // Full pricing result
  "selected_price": 450000,
  "price_option": {
    "price": 450000,
    "profit": 120000,
    "margin_percent": 26.67,
    "total_fees": 30000,
    ...
  }
}
```

## Item Types

Breakdown sử dụng các `type` để phân loại items:

- `base`: Giá trị cơ bản (giá bán, giá vốn)
- `fee`: Các khoản phí
- `cost`: Chi phí
- `negative`: Tổng các khoản trừ
- `subtotal`: Tổng phụ
- `profit`: Lợi nhuận (dương)
- `loss`: Lỗ (âm)
- `metric`: Chỉ số (%, ratio)

## Highlight

Items có `"highlight": true` được đánh dấu quan trọng:
- Giá bán
- Giá vốn
- Lợi nhuận ròng
- Doanh thu ròng

## Frontend Integration

### Hiển thị Breakdown

```javascript
// React/Next.js example
function BreakdownDisplay({ breakdown }) {
  return (
    <div className="breakdown-container">
      {breakdown.sections.map((section, idx) => (
        <div key={idx} className="section">
          <h3>{section.title}</h3>

          {section.items.map((item, i) => (
            <div key={i} className={`item ${item.highlight ? 'highlight' : ''}`}>
              <span className="label">{item.label}</span>
              <span className={`value ${item.type}`}>{item.formatted}</span>

              {item.calculation && (
                <div className="calculation-hint">💡 {item.calculation}</div>
              )}
            </div>
          ))}

          {section.subtotal && (
            <div className="subtotal">
              <span>{section.subtotal.label}</span>
              <span className={section.subtotal.type}>
                {section.subtotal.formatted}
              </span>
            </div>
          )}
        </div>
      ))}

      <div className="summary">
        <h3>Kết quả cuối cùng</h3>
        <div className="profit">
          Lợi nhuận: {breakdown.summary.net_profit.toLocaleString()} VND
        </div>
        <div className="margin">
          Margin: {breakdown.summary.profit_margin_percent.toFixed(2)}%
        </div>
      </div>
    </div>
  );
}
```

### Hiển thị Text Version (Console/Log)

```javascript
console.log(result.breakdown_text);
```

Output:
```
📊 GIÁ BÁN
──────────────────────────────────────────────────
Giá bán sản phẩm.......................... 500,000 VND

📊 PHÍ SHOPEE
──────────────────────────────────────────────────
Phí thanh toán (5.00%).................... -25,000 VND
   💡 500,000 × 5.00% = 25,000
...
```

## Lợi ích

1. **Minh bạch**: Người bán hiểu rõ từng khoản phí
2. **Giáo dục**: Công thức tính toán được hiển thị rõ ràng
3. **So sánh**: Dễ dàng so sánh các price options
4. **Tin cậy**: Tính toán giống Shopee chính thức
5. **Flexible**: Hỗ trợ cả JSON và text format

## Các trường hợp đặc biệt

### Khi không có custom costs

Section 4 (Chi phí khác) sẽ bị bỏ qua nếu `total_custom_costs = 0`.

### Khi lỗ (negative profit)

- Item type sẽ là `loss` thay vì `profit`
- `is_profitable` = false trong summary

### Voucher Xtra special rate

Nếu seller đủ điều kiện (≥10 Shopee Live sessions/tháng):
```
Phí dịch vụ (Voucher Xtra 2.5%): -12,500 VND
```

Thay vì 3%.

## Best Practices

1. **Luôn hiển thị breakdown** sau mỗi calculation
2. **Highlight breakeven price** để user biết giá tối thiểu
3. **Show calculation formulas** để tăng transparency
4. **Use color coding**: green cho profit, red cho loss
5. **Mobile responsive**: Breakdown dài, cần scroll tốt trên mobile
