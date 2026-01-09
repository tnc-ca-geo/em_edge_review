# 🐟 Fish Detector model training

This directory contains all necessary scripts and configuration files to **train and evaluate a fish detection model** using your own custom fish dataset. This step is a key part of adapting the AI-powered system to your fishery.

The baseline model provided in this repository (`baseline_fish_detector.pt`) was originally trained for a specific pilot fishery. However, each fishery has unique characteristics—such as vessel layout, camera angles, lighting conditions, and species composition—which means the model must be fine-tuned to perform well in your environment.

## 🔧 Setup

Before running the scripts, ensure you have:

- Installed all dependencies (see the root-level `README.md`)
- Modified the configuration files in `fish_detector_model/config/` to suit your dataset and hardware
- A YOLO-formatted dataset, with a corresponding `data.yaml` file

Your data.yaml should follow this format:

```yaml
path: /path/to/dataset
train: train/images
val: val/images
test: test/images

names:
  0: class_name_1
  1: class_name_2
  2: class_name_3
  ...
```


## 🏋️ Training the model

To fine-tune the provided baseline model (`baseline_fish_detector.pt`) on your custom dataset, run:

```bash
uv run fish_detector_model/train.py \
  --data /path/to/your/data.yaml
```

- This command uses settings from `train_args.yaml`.
- You can specify a different config file using `--config`:
  ```bash
  uv run fish_detector_model/train.py \
    --data /path/to/data.yaml \
    --conf path/to/your/custom_config.yaml
  ```
- To enable MLflow experiment tracking, add the `--mlflow` flag
  -> Make sure the `MLFLOW_TRACKING_URI` environment variable is set.


## ✅ Evaluating the Model

To evaluate the trained model on your test set:

```bash
uv run fish_detector_model/evaluate.py \
  --data /path/to/your/data.yaml \
  --model-path /path/to/your/model.pt
```

- This command uses settings from `eval_args.yaml`
- You can specify a different config file using `--config`:
  ```bash
  uv run fish_detector_model/train.py \
    --data /path/to/data.yaml \
    --conf path/to/your/custom_config.yaml
  ```


## 📁 Configuration Files

All configurations are located in `fish_detector_model/config/`:

`train_args.yaml` — Training hyperparameters, data augmentation, optimizer settings

`eval_args.yaml` — Confidence thresholds, NMS settings, test split, output options

🧠 These files reflect the configuration used in the pilot project. You can modify them freely to suit your dataset, hardware, or training strategy.
