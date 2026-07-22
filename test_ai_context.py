import os, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, '.')
from dashboard_api import _build_ai_context
ctx = _build_ai_context()
print("=== AI CONTEXT TEST ===")
print("Total companies:", ctx.get("total_companies"))
print("Hot leads:", ctx.get("hot_leads"))
print("Warm leads:", ctx.get("warm_leads"))
print("SSL grades:", ctx.get("ssl_grades"))
print("Sentiment dist:", ctx.get("sentiment_distribution"))
print("Avg sentiment:", ctx.get("avg_sentiment"))
print("Responding pct:", ctx.get("responding_to_reviews_pct"))
print("Top hot leads:", len(ctx.get("top_hot_leads", [])))
print("At risk:", len(ctx.get("at_risk_companies", [])))
print("Sectors:", ctx.get("sectors_breakdown", {}))
if ctx.get("top_hot_leads"):
    print("First hot lead:", ctx["top_hot_leads"][0])
if ctx.get("at_risk_companies"):
    print("First at-risk:", ctx["at_risk_companies"][0])
print("=== ALL OK ===")
