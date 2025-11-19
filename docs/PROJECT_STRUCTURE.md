# FinSightAI Project Structure

## Directory Organization

```
FinSightAI/
├── api/                    # API application code
│   ├── __init__.py
│   ├── main.py             # FastAPI application
│   └── predictor.py        # Prediction service
│
├── kafka_pipeline/         # Kafka producer/consumer
│   ├── config.py           # Kafka configuration
│   ├── consumer.py         # Kafka consumer
│   ├── producer.py         # Kafka producer
│   └── schemas.py          # Pydantic schemas
│
├── models/                 # ML models and related files
│   ├── baseline_ma.py      # Moving Average model
│   ├── multi_stock_model_LSTM.keras
│   ├── random_forest_model.pkl
│   ├── scaler.pkl
│   └── *_training_metrics.pkl
│
├── scripts/                # Utility scripts
│   ├── compare_models.py
│   ├── feature_engineering.py
│   ├── probe.py            # API probe script
│   ├── train_all_models.py
│   └── get_github_secrets.ps1
│
├── tests/                  # Test files
│   ├── test_api.py
│   ├── test_connection.py
│   ├── test_e2e_simple.py
│   └── check_models.py
│
├── docs/                   # Documentation
│   ├── README.md
│   ├── IMPLEMENTATION_GUIDE.md
│   ├── REQUIREMENTS_CHECKLIST.md
│   ├── PROJECT_STATUS_ASSESSMENT.md
│   └── optimization-journey/
│
├── data/                   # Data files
│   ├── Merged_dataset.csv
│   ├── model_comparison.csv
│   └── validation_oct11_30.csv
│
├── logs/                   # Log files (gitignored)
│
├── memory-bank/            # Memory Bank system files
│   ├── activeContext.md
│   ├── projectbrief.md
│   ├── progress.md
│   └── creative/
│
├── .github/                # GitHub Actions workflows
│   └── workflows/
│       └── automated-probes.yml
│
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
├── README.md               # Main project README
└── .env                    # Environment variables (gitignored)
```

## File Categories

### Core Application
- `api/` - FastAPI application and prediction service
- `kafka_pipeline/` - Kafka producer and consumer implementations

### Models & Data
- `models/` - Trained ML models and scalers
- `data/` - CSV datasets and comparison tables

### Scripts & Tests
- `scripts/` - Utility and automation scripts
- `tests/` - Test files for API, Kafka, and models

### Documentation
- `docs/` - All project documentation and guides
- `README.md` - Main project documentation (root)

### Configuration
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (not in git)
- `.github/workflows/` - CI/CD workflows

### Logs
- `logs/` - Application logs (gitignored)

## Notes

- **Models**: Large model files (especially `random_forest_model.pkl` ~1.2GB) are stored in `models/`
- **Data**: Large CSV files are in `data/` directory
- **Tests**: All test files are organized in `tests/` directory
- **Documentation**: All markdown documentation is in `docs/` except main `README.md`
- **Logs**: Log files are stored in `logs/` and should be gitignored

## Clean Structure Benefits

1. **Easy Navigation**: Files organized by purpose
2. **Clear Separation**: Code, tests, docs, and data are separated
3. **Better Git**: Easier to manage what goes in git
4. **Professional**: Standard project structure
5. **Maintainable**: Easy to find and update files

