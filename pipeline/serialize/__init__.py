"""
Serialize Module

Model persistence and loading.
"""

import os
import joblib
from tensorflow.keras.models import load_model as keras_load_model, save_model as keras_save_model


def save_model(model, filename, model_type='keras'):
    """
    Save a model to disk.
    
    Args:
        model: Model object to save
        filename: Path to save file
        model_type: 'keras' for Keras models, 'joblib' for sklearn/other models
    """
    if model_type == 'keras':
        keras_save_model(model, filename)
    else:
        joblib.dump(model, filename)
    return filename


def load_model(filename, model_type='keras', compile=True):
    """
    Load a model from disk.
    
    Args:
        filename: Path to model file
        model_type: 'keras' for Keras models, 'joblib' for sklearn/other models
        compile: Whether to compile Keras models (faster loading if False)
    
    Returns:
        Loaded model object
    """
    if model_type == 'keras':
        return keras_load_model(filename, compile=compile)
    else:
        return joblib.load(filename)


__all__ = ['save_model', 'load_model']
