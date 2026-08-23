#!/bin/bash
# Demo script: run the full dealflow pipeline end-to-end.
# Usage: ./examples/demo.sh

set -e  # exit on error

echo "🚀 dealflow demo"
echo "================"
echo ""

# Check for .env
if [ ! -f .env ]; then
    echo "❌ No .env file found. Copy .env.example and add your OpenRouter key."
    exit 1
fi

# Initialize DB
echo "1️⃣  Initializing database..."
uv run dealflow db init
echo ""

# Validate config
echo "2️⃣  Validating configuration..."
uv run dealflow config validate
echo ""

# Ingest first CIM
echo "3️⃣  Ingesting CIM #1 (Consolidated Utility Services)..."
uv run dealflow ingest-cim examples/cims/cus_cim.pdf --company-name "Consolidated Utility Services"
echo ""

# Ingest second CIM
echo "4️⃣  Ingesting CIM #2 (American Casino)..."
uv run dealflow ingest-cim examples/cims/american_casino_cim.pdf --company-name "American Casino"
echo ""

# Show results
echo "5️⃣  Extracted KPIs for Company 1:"
uv run dealflow show 1
echo ""

echo "6️⃣  Extracted KPIs for Company 2:"
uv run dealflow show 2
echo ""

# Export fixtures
echo "7️⃣  Exporting example data..."
uv run dealflow export --output-dir examples
echo ""

# Cost summary
echo "8️⃣  LLM cost summary:"
sqlite3 data/dealflow.sqlite "SELECT model, COUNT(*) as calls, ROUND(SUM(cost_usd), 4) as total_cost FROM llm_calls GROUP BY model;"
echo ""

echo "✅ Demo complete!"
echo ""
echo "Next steps:"
echo "  - Sync to Airtable: uv run dealflow sync-airtable"
echo "  - Add your own CIM: uv run dealflow ingest-cim <path> --company-name <name>"
echo "  - Edit config:     see config/*.yaml"
