# StockRecoAI - Stock Recommendation System

**Submission Tomorrow** | Course Project | Team: team01

## 📁 Project Structure (CLEAN)

```
StockRecoAI/
├── kafka_pipeline/          # Kafka producer/consumer + data simulation
│   ├── config.py           # Kafka broker, topics, credentials
│   ├── schemas.py          # Pydantic validation schemas
│   ├── producer.py         # ⭐ DATA SIMULATION - Fetches EOD, streams hourly
│   └── consumer.py         # Consumes, validates, writes parquet snapshots
│
├── models/                  # All 3 models for comparison
│   └── baseline_ma.py      # Moving Average baseline
│
├── api/                     # FastAPI service
│   ├── main.py             # API endpoints
│   └── predictor.py        # Model inference
│
├── scripts/                 # Testing & utilities
│   ├── compare_models.py   # Generate model comparison table
│   ├── probe.py            # API probing for Kafka
│   └── quick_test.py       # Quick verification
│
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
│
├── multi_stock_model_LSTM.keras  # Your trained LSTM
├── scaler.pkl              # Feature scaler
│
├── SUBMISSION_README.md    # ⭐ START HERE - Complete guide
├── PROJECT_ADAPTATION_PLAN.md  # Rubric mapping details
│
└── Notebooks (reference):
    ├── Stock_News_prediction_1.ipynb  # Original training
    └── producer_py.ipynb               # Producer prototype
```

## 🚀 Quick Start

### Tonight (15 mins)
```bash
python scripts/quick_test.py
```

### Tomorrow Morning
Follow `SUBMISSION_README.md` step by step.

## ✅ What's Included

**Task 1 & 2**: Kafka pipeline with data simulation ✅  
**Task 3**: 3 models (MA, RF, LSTM) + comparison ✅  
**Task 4**: Docker API ✅  
**Task 5**: Probing script ✅  

## 📝 Key Files

- **SUBMISSION_README.md** - Your main guide for tomorrow
- **PROJECT_ADAPTATION_PLAN.md** - How we map to rubric requirements
- **kafka_pipeline/producer.py** - YOUR data simulation (critical!)
- **scripts/compare_models.py** - Generates comparison table for PDF
- [ ] Submit! 🎉

---
**Everything is clean and ready. Follow SUBMISSION_README.md tomorrow!**

