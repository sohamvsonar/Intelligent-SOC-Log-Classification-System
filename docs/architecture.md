# Architecture

## System Overview

The Log Classification System follows a hybrid architecture that combines BERT-based classification with LLM-based classification for optimal performance and cost efficiency.

## High-Level Architecture

```
Input Log File → Log Classification System → Resource Usage → Security Alert → DevOps Output
                                         ↓
                                   Workflow Error
                                         ↓
                                   User Action
```

## Classification Pipeline

### 1. Initial Classification
- **Input**: Raw log messages
- **Process**: Regex classification for basic pattern matching
- **Output**: Valid/Invalid categorization

### 2. Hybrid Classification Approach

#### When Log Level Based Monitoring is Not Perfect:
- Programmers do not write perfect logs
- Logs involve heavy code and lots of other factors
- Just based on keywords (e.g., error, warning, etc.) but not built at functional/actionable level
- e.g., Security alert, Resource usage, etc.

#### Classification Categories:
1. **Security Alert**
   - Multiple login failures
   - 500 attempts on server (abnormal system behavior)
   - I/O, security breach

2. **Resource Usage**
   - Instance CPU usage: memory limit exceeded (20MB)
   - Physical memory: 8.394.6 MB, used: 512MB

3. **Workflow Error**
   - Escalation error failed for ticket
   - PID 3295, undefined escalation level
   - Task assignment for team 149 could not complete

## Technical Architecture

### Sample Log Processing Flow

```
Sample Log File (Excel) → BERT → [0.7, 0.8, 0.2] → DBSCAN → Cluster
                                Generate          To cluster
                                Embedding         this
                                                 embedding
```

### Component Details

1. **BERT (Bidirectional Encoder Representations from Transformers)**
   - Generates embeddings for log messages
   - Produces vector representations (e.g., [0.7, 0.8, 0.2])

2. **DBSCAN (Density-Based Spatial Clustering)**
   - Clusters similar log embeddings
   - Groups logs with similar patterns and meanings

3. **Output Categories**
   - Clustered logs are classified into predefined categories
   - Each cluster represents a specific type of log event

## Low-Level Architecture

### Log Message Processing

```
Log Message
    ↓
Regex Classification
    ↓
Valid Output ← → Unknown
    ↓              ↓
BERT Classification → LLM Classification
```

### Decision Tree Process

1. **Regex Classification**: Initial filtering of log messages
2. **Binary Decision**: 
   - If enough training samples exist → Use BERT Classification
   - If not enough training samples → Use LLM Classification

## Benefits of Hybrid Classification

1. **Optimized Cost**: Uses computationally efficient BERT when sufficient training data exists
2. **High Speed Performance**: BERT provides faster classification for known patterns
3. **Better Accuracy**: LLM handles edge cases and unknown patterns
4. **Scalability**: System can adapt to new log types without retraining