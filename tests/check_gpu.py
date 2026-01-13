import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import tensorflow as tf

print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))