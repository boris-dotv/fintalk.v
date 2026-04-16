#!/bin/bash
# FinTalk.ai - CDN 国内化替换脚本
# 用法: 在项目根目录运行 bash fix-cdn-for-china.sh
# 
# 替换清单:
#   fonts.googleapis.com  → fonts.font.im     (Google Fonts 中国站)
#   cdn.jsdelivr.net      → cdn.bootcdn.net    (BootCDN 国内加速)
#   cdnjs.cloudflare.com  → cdn.bootcdn.net    (BootCDN 国内加速)

set -e

FILE="index.html"

if [ ! -f "$FILE" ]; then
    echo "❌ 未找到 $FILE，请在项目根目录运行此脚本"
    exit 1
fi

echo "🔧 开始替换 CDN 链接..."

# 1. Google Fonts → fonts.font.im (Google Fonts 中国站 API)
sed -i.bak 's|https://fonts.googleapis.com/css2|https://fonts.font.im/css2|g' "$FILE"
echo "  ✓ Google Fonts → fonts.font.im"

# 2. PapaParse → BootCDN
sed -i.bak 's|https://cdn.jsdelivr.net/npm/papaparse@5/papaparse.min.js|https://cdn.bootcdn.net/ajax/libs/PapaParse/5.4.1/papaparse.min.js|g' "$FILE"
echo "  ✓ PapaParse → BootCDN 5.4.1"

# 3. marked → BootCDN
sed -i.bak 's|https://cdn.jsdelivr.net/npm/marked/marked.min.js|https://cdn.bootcdn.net/ajax/libs/marked/12.0.0/marked.min.js|g' "$FILE"
echo "  ✓ marked → BootCDN 12.0.0"

# 4. Chart.js → BootCDN
sed -i.bak 's|https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js|https://cdn.bootcdn.net/ajax/libs/Chart.js/4.4.1/chart.umd.min.js|g' "$FILE"
echo "  ✓ Chart.js → BootCDN 4.4.1"

# 5. sql.js (script tag + locateFile WASM loader) → BootCDN
sed -i.bak 's|https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/|https://cdn.bootcdn.net/ajax/libs/sql.js/1.10.3/|g' "$FILE"
echo "  ✓ sql.js + WASM → BootCDN 1.10.3"

# 清理 sed 备份文件
rm -f "${FILE}.bak"

echo ""
echo "✅ 全部完成！共替换 6 处 CDN 链接"
echo ""
echo "替换结果:"
echo "  fonts.googleapis.com  → fonts.font.im"
echo "  cdn.jsdelivr.net      → cdn.bootcdn.net"
echo "  cdnjs.cloudflare.com  → cdn.bootcdn.net"
echo ""
echo "下一步: git add . && git commit -m 'fix: 替换CDN为国内源' && git push"