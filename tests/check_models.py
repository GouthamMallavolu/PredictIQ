import os
models = ['multi_stock_model_LSTM.keras', 'random_forest_model.pkl', 'scaler.pkl']
print('Model files:')
for m in models:
    status = "EXISTS" if os.path.exists(m) else "MISSING"
    print(f'  {m}: {status}')

