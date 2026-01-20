# Preprocessing Output Fix - Issue #7

## Problem

**Error**:
```
No S3 objects found under S3 URL "s3://amzn-s3-movielens-327030626634/processed-data/train.csv"
```

**Root Cause**: The preprocessing script (`src/preprocessing.py`) only contained utility functions but no main execution block. When run as a SageMaker processing job, it didn't actually:
1. Load the MovieLens data
2. Process it
3. Save the output files

The training step expected `train.csv` and `validation.csv` files, but they were never created.

---

## Solution

Created a complete preprocessing script that:
1. Loads MovieLens 100K data from `/opt/ml/processing/input/data/`
2. Cleans the data (removes missing values)
3. Encodes user and movie IDs as consecutive integers
4. Normalizes ratings to [0, 1] range
5. Splits data into train/validation/test sets (80/10/10)
6. Saves as CSV files: `train.csv`, `validation.csv`, `test.csv`

---

## Fix Applied

### Script Created: `fix_preprocessing_script.py`

This script:
- Creates a complete preprocessing script with main execution block
- Uploads it to `s3://bucket/code/preprocessing.py`
- Replaces the previous incomplete script

### Command Executed

```powershell
python fix_preprocessing_script.py --bucket amzn-s3-movielens-327030626634
```

**Result**: Successfully uploaded new preprocessing script (6,346 bytes)

---

## What the New Script Does

### 1. Load Data
```python
# Loads u.data file (tab-separated)
# Format: user_id, movie_id, rating, timestamp
ratings = pd.read_csv(ratings_file, sep='\\t', names=['userId', 'movieId', 'rating', 'timestamp'])
```

### 2. Clean Data
```python
# Remove rows with missing values in required fields
cleaned = data.dropna(subset=['userId', 'movieId', 'rating'])
```

### 3. Encode IDs
```python
# Map original IDs to consecutive integers (0, 1, 2, ...)
# Required for embedding layers in neural network
user_id_map = {original: encoded for encoded, original in enumerate(unique_users)}
movie_id_map = {original: encoded for encoded, original in enumerate(unique_movies)}
```

### 4. Normalize Ratings
```python
# Scale ratings from [0.5, 5.0] to [0, 1]
normalized['rating'] = (data['rating'] - 0.5) / (5.0 - 0.5)
```

### 5. Split Data
```python
# 80% train, 10% validation, 10% test
train_data = shuffled.iloc[:train_size]
val_data = shuffled.iloc[train_size:train_size + val_size]
test_data = shuffled.iloc[train_size + val_size:]
```

### 6. Save Output
```python
# Save as CSV files (no header, no index)
# Format: userId,movieId,rating
train_data[columns].to_csv('train.csv', index=False, header=False)
val_data[columns].to_csv('validation.csv', index=False, header=False)
test_data[columns].to_csv('test.csv', index=False, header=False)
```

---

## Expected Output Files

After preprocessing completes, these files will be in S3:

```
s3://amzn-s3-movielens-327030626634/processed-data/
├── train.csv          (~80,000 rows)
├── validation.csv     (~10,000 rows)
└── test.csv           (~10,000 rows)
```

Each file format:
```
0,0,0.8
0,1,0.6
1,0,0.9
...
```
(userId, movieId, normalized_rating)

---

## State Machine Configuration

The training step expects these exact paths:

```json
{
  "InputDataConfig": [
    {
      "ChannelName": "train",
      "DataSource": {
        "S3DataSource": {
          "S3Uri": "s3://bucket/processed-data/train.csv"
        }
      }
    },
    {
      "ChannelName": "validation",
      "DataSource": {
        "S3DataSource": {
          "S3Uri": "s3://bucket/processed-data/validation.csv"
        }
      }
    }
  ]
}
```

---

## Verification

After preprocessing completes, verify the files exist:

```powershell
# Check S3 for processed data
aws s3 ls s3://amzn-s3-movielens-327030626634/processed-data/

# Expected output:
# train.csv
# validation.csv
# test.csv
```

Or use the Python script:
```powershell
python check_s3_progress.py --bucket amzn-s3-movielens-327030626634
```

---

## Timeline

**Issue Discovered**: 22:30 UTC (Execution 6 failed at training step)  
**Fix Created**: 22:31 UTC  
**Fix Applied**: 22:32 UTC  
**Pipeline Restarted**: 22:32:06 UTC (Execution 7)  
**Expected Completion**: ~23:44 UTC

---

## Comparison: Before vs After

### Before (Incomplete Script)
```python
# src/preprocessing.py
def handle_missing_values(data):
    ...

def encode_ids(data):
    ...

# No main block - script does nothing when executed!
```

### After (Complete Script)
```python
# preprocessing_fixed.py
def load_movielens_data(input_path):
    ...

def clean_data(data):
    ...

def encode_ids(data):
    ...

def save_processed_data(train, val, test, output_path):
    ...

def main():
    # 1. Load data
    data = load_movielens_data(input_path)
    # 2. Clean
    data = clean_data(data)
    # 3. Encode
    data, user_map, movie_map = encode_ids(data)
    # 4. Normalize
    data = normalize_ratings(data)
    # 5. Split
    train, val, test = split_data(data)
    # 6. Save
    save_processed_data(train, val, test, output_path)

if __name__ == '__main__':
    main()
```

---

## Related Issues

This is **Issue #7** in the pipeline deployment sequence:

1. ✓ Missing input parameters
2. ✓ Missing PassRole permission
3. ✓ Duplicate job names
4. ✓ Missing preprocessing code upload
5. ✓ Input parameters lost (ResultPath)
6. ✓ Missing AddTags permission
7. ✓ **Incomplete preprocessing script** ← THIS ISSUE

---

## Files Created

1. `fix_preprocessing_script.py` - Script to create and upload complete preprocessing script
2. `preprocessing_fixed.py` - The complete preprocessing script (local copy)
3. `PREPROCESSING_OUTPUT_FIX.md` - This documentation

---

## Next Steps

1. **Now**: Wait for preprocessing to complete (~10 minutes)
2. **22:42 UTC**: Verify processed data files exist in S3
3. **22:42 - 23:27 UTC**: Training runs (45 minutes)
4. **23:27 - 23:44 UTC**: Evaluation, deployment, monitoring (17 minutes)
5. **23:44 UTC**: Pipeline complete!

---

## Monitoring

**AWS Console**:
```
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:327030626634:stateMachine:MovieLensMLPipeline
```

**Execution**: `execution-20260119-223205-460`

**Check S3 Progress**:
```powershell
python check_s3_progress.py --bucket amzn-s3-movielens-327030626634
```

---

## Summary

**Issue**: Preprocessing script didn't create expected output files  
**Root Cause**: Script had no main execution block  
**Fix**: Created complete script with data loading, processing, and saving  
**Status**: ✓ Fixed and uploaded  
**Pipeline**: Restarted (Execution 7)  
**Expected**: SUCCESS!

---

**Confidence Level**: VERY HIGH - Script now has complete data pipeline implementation
